from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from modules.detection.models.detection_result import DetectionResult

logger = logging.getLogger(__name__)

# Common section headers in medical, legal, financial, and corporate records
SECTION_HEADER_PATTERN = re.compile(
    r"(?im)^(?:[A-Z0-9\s/_\-]{3,40}:|[#*]{1,3}\s+[A-Z][A-Za-z0-9\s/_\-]{2,40}|"
    r"(?:CHIEF COMPLAINT|HISTORY OF PRESENT ILLNESS|PAST MEDICAL HISTORY|MEDICATIONS|ALLERGIES|"
    r"PHYSICAL EXAMINATION|LABORATORY DATA|IMPRESSION|PLAN|DIAGNOSIS|DISCHARGE SUMMARY|"
    r"PAYMENT DETAILS|ACCOUNT SUMMARY|TERMS AND CONDITIONS|EMPLOYMENT DETAILS|PATIENT INFORMATION|"
    r"BENEFICIARY DETAILS|BILLING INFORMATION)\b)"
)


@dataclass(frozen=True)
class DocumentChunk:
    """
    Represents a logically coherent chunk of text with its global
    character offsets in the original document.
    """

    chunk_id: int
    text: str
    start_char: int
    end_char: int
    section_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.text)


class SemanticChunker:
    """
    Semantic chunker designed for PII/PHI document intelligence.

    Splits text along logical semantic boundaries (section headers, paragraphs,
    and sentences) while preserving global character coordinates, maintaining
    boundary overlap, and selecting candidate-relevant chunks for LLM processing.
    """

    DEFAULT_TARGET_CHUNK_CHARS = 1500
    DEFAULT_MAX_CHUNK_CHARS = 2200
    DEFAULT_MIN_CHUNK_CHARS = 300
    DEFAULT_OVERLAP_CHARS = 100

    def __init__(
        self,
        target_chunk_chars: int = DEFAULT_TARGET_CHUNK_CHARS,
        max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS,
        overlap_chars: int = DEFAULT_OVERLAP_CHARS,
    ):
        self.target_chunk_chars = target_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars
        self.overlap_chars = overlap_chars

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes extracted raw text (from OCR/Native PDF extraction):
        - Standardizes line breaks (\\r\\n, \\r -> \\n).
        - Removes non-printable control characters, null bytes, and zero-width spaces.
        - Normalizes Unicode quotation marks, dashes, and non-breaking spaces.
        - Strips trailing spaces per line and collapses excessive vertical blank lines.
        """
        if not text:
            return ""

        # 1. Unify line breaks
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Remove zero-width spaces, BOM, and null bytes
        for ch in ("\ufeff", "\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\x00"):
            normalized = normalized.replace(ch, "")

        # 3. Normalize Unicode quotes, dashes, and non-breaking spaces
        trans_table = str.maketrans({
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2014": "-",
            "\u2013": "-",
            "\u00a0": " ",
        })
        normalized = normalized.translate(trans_table)

        # 4. Clean trailing whitespace on each line
        lines = [line.rstrip() for line in normalized.split("\n")]
        normalized = "\n".join(lines)

        # 5. Collapse excessive blank lines (more than 2 consecutive newlines)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        return normalized.strip()

    def chunk_document(self, text: str) -> list[DocumentChunk]:
        """
        Partitions the document text into semantic chunks with exact global offsets.
        """
        if not text or not text.strip():
            return []

        # Ensure normalized text
        text = self.normalize_text(text)

        # If document is small enough, return as a single chunk
        if len(text) <= self.max_chunk_chars:
            return [
                DocumentChunk(
                    chunk_id=0,
                    text=text,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        # 1. Identify primary split points (double newlines, section headers, sentences)
        paragraphs = self._split_into_semantic_segments(text)
        if not paragraphs:
            return [
                DocumentChunk(
                    chunk_id=0,
                    text=text,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        # 2. Group segments into target-sized chunks with overlap
        chunks: list[DocumentChunk] = []
        current_segments: list[tuple[int, int]] = []
        current_len = 0
        chunk_id = 0

        for seg_start, seg_end in paragraphs:
            seg_len = seg_end - seg_start
            if current_segments and (current_len + seg_len > self.max_chunk_chars):
                # Finalize current chunk
                chunk_start = current_segments[0][0]
                chunk_end = current_segments[-1][1]
                chunk_text = text[chunk_start:chunk_end]

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        start_char=chunk_start,
                        end_char=chunk_end,
                    )
                )
                chunk_id += 1

                # Retain overlap segments
                overlap_accum = 0
                new_segments = []
                for s_start, s_end in reversed(current_segments):
                    new_segments.insert(0, (s_start, s_end))
                    overlap_accum += (s_end - s_start)
                    if overlap_accum >= self.overlap_chars:
                        break

                current_segments = new_segments
                current_len = overlap_accum

            current_segments.append((seg_start, seg_end))
            current_len += seg_len

        if current_segments:
            chunk_start = current_segments[0][0]
            chunk_end = current_segments[-1][1]
            chunk_text = text[chunk_start:chunk_end]
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    start_char=chunk_start,
                    end_char=chunk_end,
                )
            )

        return chunks

    def select_relevant_chunks(
        self,
        chunks: list[DocumentChunk],
        candidates: Sequence[dict[str, Any]],
        low_confidence_entities: Sequence[DetectionResult] | None = None,
        resolved_entities: Sequence[DetectionResult] | None = None,
        max_chunks: int = 10,
    ) -> list[DocumentChunk]:
        """
        Selects chunks that require LLM processing:
        - Locks high-confidence entity spans, but ensures surrounding chunk text is still sent to LLM.
        - Chunks with residual candidates, low-confidence entities, or unmasked narrative text are prioritized.
        - A chunk is only skipped if 100% of its content is covered by a locked span with zero surrounding text.
        """
        if not chunks:
            return []

        resolved = resolved_entities or []
        high_conf_spans = [
            (e.start_char, e.end_char)
            for e in resolved
            if e.confidence_score >= 0.80
        ]

        scored_chunks: list[tuple[int, int, DocumentChunk]] = []

        for chunk in chunks:
            chunk_len = len(chunk.text.strip())
            if chunk_len == 0:
                continue

            # Calculate overlap with high-confidence locked spans
            locked_char_count = 0
            for start, end in high_conf_spans:
                overlap = max(0, min(chunk.end_char, end) - max(chunk.start_char, start))
                locked_char_count += overlap

            unresolved_chars = max(0, chunk_len - locked_char_count)

            # Skip ONLY if 100% covered by locked spans with zero surrounding text
            if unresolved_chars == 0 and locked_char_count > 0:
                continue

            # Count candidate intersections
            candidate_hits = sum(
                1
                for c in candidates
                if max(chunk.start_char, c.get("start", 0)) < min(chunk.end_char, c.get("end", 0))
            )

            # Count low confidence entity intersections
            low_conf = low_confidence_entities or []
            low_conf_hits = sum(
                1
                for e in low_conf
                if max(chunk.start_char, e.start_char) < min(chunk.end_char, e.end_char)
            )

            # Score prioritizing candidate signals while ensuring all chunks with unresolved text are eligible
            total_score = (candidate_hits * 3) + (low_conf_hits * 4) + (unresolved_chars // 50) + 1
            scored_chunks.append((total_score, -chunk.chunk_id, chunk))

        if not scored_chunks:
            return chunks[:max_chunks]

        # Sort by highest score first, then by earliest chunk order
        scored_chunks.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [item[2] for item in scored_chunks[:max_chunks]]
        # Return in sequential document order
        selected.sort(key=lambda chunk: chunk.start_char)
        return selected

    @staticmethod
    def remap_detection_to_global(
        detection: DetectionResult,
        chunk: DocumentChunk,
    ) -> DetectionResult:
        """
        Remaps a DetectionResult with chunk-local character coordinates
        back to global document character coordinates.
        """
        detection.start_char += chunk.start_char
        detection.end_char += chunk.start_char
        return detection

    def _split_into_semantic_segments(self, text: str) -> list[tuple[int, int]]:
        """
        Identifies boundaries by double newlines, section headings, and sentences.
        Returns a list of (start_idx, end_idx) character spans.
        """
        segments: list[tuple[int, int]] = []
        pos = 0
        text_len = len(text)

        # Match paragraph breaks (\n\n+) or section headers
        boundary_pattern = re.compile(
            r"(?:\r?\n\s*\r?\n|(?<=\n)(?=[A-Z0-9\s/_\-]{3,40}:)|(?<=[.!?])\s+(?=[A-Z]))"
        )

        for match in boundary_pattern.finditer(text):
            split_idx = match.start()
            if split_idx > pos:
                seg_text = text[pos:split_idx].strip()
                if seg_text:
                    raw_start = pos + (len(text[pos:split_idx]) - len(text[pos:split_idx].lstrip()))
                    raw_end = pos + len(text[pos:split_idx].rstrip())
                    if raw_start < raw_end:
                        segments.append((raw_start, raw_end))
            pos = match.end()

        if pos < text_len:
            seg_text = text[pos:text_len].strip()
            if seg_text:
                raw_start = pos + (len(text[pos:text_len]) - len(text[pos:text_len].lstrip()))
                raw_end = pos + len(text[pos:text_len].rstrip())
                if raw_start < raw_end:
                    segments.append((raw_start, raw_end))

        return segments
