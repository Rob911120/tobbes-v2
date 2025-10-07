"""
Custom exceptions for Tobbes v2.

All exceptions inherit from TobbesBaseException for easier catching.
Each exception includes a message and optional details dict.
"""


class TobbesBaseException(Exception):
    """Base exception for all Tobbes-related errors."""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            details: Optional dict with additional context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """String representation with details if available."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class DatabaseError(TobbesBaseException):
    """Database operation failed."""
    pass


class ImportValidationError(TobbesBaseException):
    """Import file validation failed."""
    pass


class CertificateError(TobbesBaseException):
    """Certificate operation failed."""
    pass


class ReportGenerationError(TobbesBaseException):
    """Report generation failed."""
    pass


class ValidationError(TobbesBaseException):
    """Data validation failed."""
    pass


class NotFoundError(TobbesBaseException):
    """Requested resource not found."""
    pass
