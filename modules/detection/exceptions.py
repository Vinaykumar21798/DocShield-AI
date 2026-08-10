"""
Custom exceptions for the Detection module.
"""


class DetectionError(Exception):
    """
    Base exception for all detection-related errors.
    """

    def __init__(self, message: str = "Detection error occurred"):
        super().__init__(message)


class DetectorInitializationError(DetectionError):
    """
    Raised when a detector fails to initialize.
    """

    def __init__(self, detector_name: str):
        super().__init__(
            f"Failed to initialize detector: {detector_name}"
        )


class DetectionExecutionError(DetectionError):
    """
    Raised when a detector fails during execution.
    """

    def __init__(self, detector_name: str):
        super().__init__(
            f"Detection failed in detector: {detector_name}"
        )


class UnsupportedDocumentError(DetectionError):
    """
    Raised when the document type is unsupported.
    """

    def __init__(self, document_type: str):
        super().__init__(
            f"Unsupported document type: {document_type}"
        )


class EntityMappingError(DetectionError):
    """
    Raised when entity normalization fails.
    """

    def __init__(self, entity_type: str):
        super().__init__(
            f"Unable to map entity type: {entity_type}"
        )


class ValidationError(DetectionError):
    """
    Raised when entity validation fails.
    """

    def __init__(self, message: str = "Entity validation failed"):
        super().__init__(message)
