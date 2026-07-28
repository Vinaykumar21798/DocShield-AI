from modules.detection.models.detection_result import DetectionResult


class MaskManager:
    """
    Maintains a mask over the original document without
    modifying the original text.

    Every detector receives a masked view, while offsets
    always refer to the original document.
    """

    def __init__(self, text: str):

        self.original_text = text

        self.mask = [False] * len(text)

    def add_entities(
        self,
        entities: list[DetectionResult],
    ):

        for entity in entities:

            start = max(0, entity.start_char)
            end = min(len(self.mask), entity.end_char)

            for i in range(start, end):
                self.mask[i] = True

    def remaining_text(self) -> str:

        chars = []

        for i, ch in enumerate(self.original_text):

            if self.mask[i]:
                chars.append(" ")
            else:
                chars.append(ch)

        return "".join(chars)

    def has_remaining_text(self) -> bool:

        return self.remaining_text().strip() != ""