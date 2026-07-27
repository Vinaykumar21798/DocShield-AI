from modules.detection.analyzer.detection_strategy import DetectionStrategy
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.gliner_detector import GLiNERDetector
from modules.detection.detectors.medspacy_detector import MedSpaCyDetector
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.detectors.regex_detector import RegexDetector

class DetectorFactory:
    """
    Creates detector instances based on the selected strategy.
    """

    @staticmethod
    def create(strategy: DetectionStrategy) -> list[BaseDetector]:
        detectors: list[BaseDetector] = []
        if strategy.use_regex:
            detectors.append(RegexDetector())

        if strategy.use_presidio:
            detectors.append(PresidioDetector())

        if strategy.use_gliner:
            detectors.append(GLiNERDetector())

        if strategy.use_medspacy:
            detectors.append(MedSpaCyDetector())

        return detectors