class DiagnosisError(Exception):
    """Base exception for diagnosis failures."""


class InvalidDiagnosisResponse(DiagnosisError):
    """Raised when an AI component returns an unsupported response."""
