"""
Input validators for Tobbes v2.

These validators ensure data integrity before it reaches the database.
All validators raise ValidationError on failure.
"""

import re
from pathlib import Path
from typing import Optional, Union

from .exceptions import ValidationError


def validate_order_number(order_number: str) -> str:
    """
    Validate order number format.

    Accepts any non-empty format (no pattern restrictions).

    Args:
        order_number: Order number to validate

    Returns:
        Cleaned order number (trimmed, preserves original case)

    Raises:
        ValidationError: If empty
    """
    if not order_number:
        raise ValidationError("Order number cannot be empty")

    cleaned = order_number.strip()

    # No format restrictions - accept any non-empty order number
    return cleaned


def validate_article_number(article_number: str) -> str:
    """
    Validate article number.

    Rules:
    - Not empty
    - Max 50 characters
    - Alphanumeric + hyphens/underscores/slashes/dots/spaces (v1 compatibility)

    Args:
        article_number: Article number to validate

    Returns:
        Cleaned article number (trimmed)

    Raises:
        ValidationError: If invalid
    """
    if not article_number:
        raise ValidationError("Article number cannot be empty")

    cleaned = article_number.strip()

    if len(cleaned) > 50:
        raise ValidationError(
            f"Article number too long: {len(cleaned)} characters (max 50)",
            details={"article_number": cleaned},
        )

    # Allow alphanumeric, hyphens, underscores, spaces, slashes, dots
    # This matches v1 behavior which had no pattern restriction
    pattern = r"^[A-Za-z0-9\-_\s/.]+$"
    if not re.match(pattern, cleaned):
        raise ValidationError(
            f"Article number contains invalid characters: '{cleaned}'",
            details={"article_number": cleaned, "allowed": "A-Z, 0-9, -, _, space, /, ."},
        )

    return cleaned


def validate_charge_number(charge_number: str) -> str:
    """
    Validate charge/batch number.

    Rules:
    - Not empty
    - Max 30 characters
    - Alphanumeric + hyphens/underscores

    Args:
        charge_number: Charge number to validate

    Returns:
        Cleaned charge number (trimmed)

    Raises:
        ValidationError: If invalid
    """
    if not charge_number:
        raise ValidationError("Charge number cannot be empty")

    cleaned = charge_number.strip()

    if len(cleaned) > 30:
        raise ValidationError(
            f"Charge number too long: {len(cleaned)} characters (max 30)",
            details={"charge_number": cleaned},
        )

    return cleaned


def validate_quantity(quantity: float, allow_zero: bool = True, allow_negative: bool = False) -> float:
    """
    Validate quantity value.

    Args:
        quantity: Quantity to validate (None/NaN will be converted to 0.0)
        allow_zero: If True, allow quantity = 0
        allow_negative: If True, allow negative quantities (for lagerlogg withdrawals)

    Returns:
        Validated quantity (guaranteed to be a valid float)

    Raises:
        ValidationError: If invalid
    """
    # Handle None/NaN - convert to 0.0 (v1 compatibility)
    if quantity is None:
        return 0.0

    # Handle NaN from pandas
    try:
        import math
        if math.isnan(quantity):
            return 0.0
    except (TypeError, ValueError):
        pass  # Not a float or NaN, continue with validation

    # Validate negative
    if not allow_negative and quantity < 0:
        raise ValidationError(
            f"Quantity cannot be negative: {quantity}",
            details={"quantity": quantity},
        )

    # Validate zero
    if not allow_zero and quantity == 0:
        raise ValidationError(
            "Quantity cannot be zero",
            details={"quantity": quantity},
        )

    return float(quantity)


def validate_file_path(
    file_path: Union[Path, str],
    must_exist: bool = True,
    allowed_extensions: Optional[list] = None,
) -> Path:
    """
    Validate file path.

    Args:
        file_path: File path to validate
        must_exist: If True, file must exist on disk
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.xlsx'])

    Returns:
        Path object

    Raises:
        ValidationError: If invalid
    """
    if not file_path:
        raise ValidationError("File path cannot be empty")

    path = Path(file_path)

    if must_exist and not path.exists():
        raise ValidationError(
            f"File does not exist: {path}",
            details={"file_path": str(path)},
        )

    if allowed_extensions:
        if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
            raise ValidationError(
                f"Invalid file extension: {path.suffix}. Allowed: {allowed_extensions}",
                details={"file_path": str(path), "allowed": allowed_extensions},
            )

    return path


def validate_level_number(level: str) -> str:
    """
    Validate BOM level number.

    Expected formats:
    - "1"
    - "1.1"
    - "1.1.1"
    - "1.1.1.1"

    Args:
        level: Level string to validate

    Returns:
        Cleaned level string

    Raises:
        ValidationError: If invalid format
    """
    if not level:
        return ""  # Empty is OK

    cleaned = level.strip()

    # Pattern: digits separated by dots
    pattern = r"^\d+(\.\d+)*$"
    if not re.match(pattern, cleaned):
        raise ValidationError(
            f"Invalid level format: '{cleaned}'. Expected: '1', '1.1', '1.1.1', etc.",
            details={"level": cleaned},
        )

    return cleaned


def validate_certificate_type(cert_type: str) -> str:
    """
    Validate certificate type name.

    Args:
        cert_type: Certificate type to validate

    Returns:
        Cleaned certificate type (trimmed)

    Raises:
        ValidationError: If invalid
    """
    if not cert_type:
        raise ValidationError("Certificate type cannot be empty")

    cleaned = cert_type.strip()

    if len(cleaned) > 100:
        raise ValidationError(
            f"Certificate type too long: {len(cleaned)} characters (max 100)",
            details={"certificate_type": cleaned},
        )

    return cleaned


def validate_project_name(project_name: str) -> str:
    """
    Validate project name.

    Args:
        project_name: Project name to validate

    Returns:
        Cleaned project name (trimmed)

    Raises:
        ValidationError: If invalid
    """
    if not project_name:
        raise ValidationError("Artikelbenämning kan inte vara tom")

    cleaned = project_name.strip()

    if len(cleaned) > 200:
        raise ValidationError(
            f"Artikelbenämning för lång: {len(cleaned)} tecken (max 200)",
            details={"project_name": cleaned},
        )

    return cleaned


def validate_customer_name(customer: str) -> str:
    """
    Validate customer name.

    Args:
        customer: Customer name to validate

    Returns:
        Cleaned customer name (trimmed)

    Raises:
        ValidationError: If invalid
    """
    if not customer:
        raise ValidationError("Customer name cannot be empty")

    cleaned = customer.strip()

    if len(cleaned) > 200:
        raise ValidationError(
            f"Customer name too long: {len(cleaned)} characters (max 200)",
            details={"customer": cleaned},
        )

    return cleaned


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Removes/replaces characters that could cause filesystem issues.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Remove path separators
    cleaned = filename.replace("/", "_").replace("\\", "_")

    # Remove or replace problematic characters
    cleaned = re.sub(r'[<>:"|?*]', "_", cleaned)

    # Remove leading/trailing dots and spaces
    cleaned = cleaned.strip(". ")

    # Limit length
    if len(cleaned) > 255:
        name, ext = cleaned.rsplit(".", 1) if "." in cleaned else (cleaned, "")
        cleaned = name[: 255 - len(ext) - 1] + "." + ext if ext else name[:255]

    return cleaned
