"""
File Service for Tobbes v2.

Handles all file operations - copying, moving, validating, etc.
"""

import shutil
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from domain.exceptions import ValidationError
from domain.validators import sanitize_filename
from config.constants import (
    ALLOWED_CERTIFICATE_EXTENSIONS,
    MAX_FILE_SIZE_MB,
)

logger = logging.getLogger(__name__)


class FileService:
    """
    Service for file operations.

    Handles:
    - File validation
    - Copying certificates to project folders
    - Safe file deletion
    - Directory management
    """

    def __init__(self, base_dir: Path):
        """
        Initialize file service.

        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(
        self,
        file_path: Path,
        allowed_extensions: Optional[List[str]] = None,
        max_size_mb: Optional[float] = None,
    ) -> bool:
        """
        Validate file exists and meets requirements.

        Args:
            file_path: Path to file to validate
            allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.jpg'])
            max_size_mb: Maximum file size in MB

        Returns:
            True if valid

        Raises:
            ValidationError: If file is invalid

        Example:
            >>> service = FileService(Path('./certs'))
            >>> service.validate_file(Path('cert.pdf'), ['.pdf'], 10)
        """
        if not file_path.exists():
            raise ValidationError(
                f"Filen finns inte: {file_path}",
                details={"file_path": str(file_path)}
            )

        if not file_path.is_file():
            raise ValidationError(
                f"Inte en fil: {file_path}",
                details={"file_path": str(file_path)}
            )

        # Check extension
        if allowed_extensions:
            if file_path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                raise ValidationError(
                    f"Ogiltig filtyp: {file_path.suffix}. Tillåtna: {', '.join(allowed_extensions)}",
                    details={"file_path": str(file_path), "allowed": allowed_extensions}
                )

        # Check size
        if max_size_mb:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                raise ValidationError(
                    f"Filen är för stor: {file_size_mb:.1f} MB (max {max_size_mb} MB)",
                    details={"file_path": str(file_path), "size_mb": file_size_mb}
                )

        return True

    def copy_certificate(
        self,
        source_path: Path,
        project_id: int,
        article_number: str,
        preserve_name: bool = True,
    ) -> Path:
        """
        Copy certificate file to project directory.

        Creates project directory structure:
        base_dir/project_{id}/article_{number}/filename.pdf

        Args:
            source_path: Source file path
            project_id: Project ID
            article_number: Article number
            preserve_name: Keep original filename (default: True)

        Returns:
            Path to copied file

        Raises:
            ValidationError: If file is invalid

        Example:
            >>> service = FileService(Path('./certificates'))
            >>> dest = service.copy_certificate(
            ...     Path('/tmp/cert.pdf'),
            ...     project_id=1,
            ...     article_number='ART-001'
            ... )
            >>> print(dest)  # certificates/project_1/article_ART-001/cert.pdf
        """
        # Validate source file
        self.validate_file(
            source_path,
            allowed_extensions=ALLOWED_CERTIFICATE_EXTENSIONS,
            max_size_mb=MAX_FILE_SIZE_MB,
        )

        # Create destination directory
        project_dir = self.base_dir / f"project_{project_id}"
        article_dir = project_dir / f"article_{sanitize_filename(article_number)}"
        article_dir.mkdir(parents=True, exist_ok=True)

        # Determine destination filename
        if preserve_name:
            dest_name = sanitize_filename(source_path.name)
        else:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_name = f"{sanitize_filename(article_number)}_{timestamp}{source_path.suffix}"

        dest_path = article_dir / dest_name

        # Handle duplicate filenames
        if dest_path.exists():
            counter = 1
            stem = dest_path.stem
            suffix = dest_path.suffix
            while dest_path.exists():
                dest_path = article_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        # Copy file
        shutil.copy2(source_path, dest_path)
        logger.info(f"Copied certificate: {source_path} -> {dest_path}")

        return dest_path

    def delete_file(self, file_path: Path, safe: bool = True) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete
            safe: If True, only delete files within base_dir (default: True)

        Returns:
            True if deleted successfully

        Raises:
            ValidationError: If safe=True and file is outside base_dir

        Example:
            >>> service = FileService(Path('./certificates'))
            >>> service.delete_file(Path('./certificates/project_1/cert.pdf'))
        """
        file_path = Path(file_path)

        # Safety check - only delete files within base_dir
        if safe:
            try:
                file_path.resolve().relative_to(self.base_dir.resolve())
            except ValueError:
                raise ValidationError(
                    f"Kan inte ta bort fil utanför arbetskatalogen: {file_path}",
                    details={"file_path": str(file_path), "base_dir": str(self.base_dir)}
                )

        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise ValidationError(
                f"Kunde inte ta bort fil: {e}",
                details={"file_path": str(file_path), "error": str(e)}
            )

    def cleanup_empty_directories(self, project_id: int) -> int:
        """
        Remove empty article directories for a project.

        Args:
            project_id: Project ID

        Returns:
            Number of directories removed

        Example:
            >>> service = FileService(Path('./certificates'))
            >>> removed = service.cleanup_empty_directories(project_id=1)
            >>> print(f"Removed {removed} empty directories")
        """
        project_dir = self.base_dir / f"project_{project_id}"

        if not project_dir.exists():
            return 0

        removed_count = 0

        # Remove empty article directories
        for article_dir in project_dir.iterdir():
            if article_dir.is_dir() and not list(article_dir.iterdir()):
                article_dir.rmdir()
                logger.info(f"Removed empty directory: {article_dir}")
                removed_count += 1

        # Remove empty project directory
        if not list(project_dir.iterdir()):
            project_dir.rmdir()
            logger.info(f"Removed empty project directory: {project_dir}")

        return removed_count

    def get_project_certificates(self, project_id: int) -> List[Path]:
        """
        Get all certificate files for a project.

        Args:
            project_id: Project ID

        Returns:
            List of certificate file paths

        Example:
            >>> service = FileService(Path('./certificates'))
            >>> certs = service.get_project_certificates(project_id=1)
            >>> for cert in certs:
            ...     print(cert.name)
        """
        project_dir = self.base_dir / f"project_{project_id}"

        if not project_dir.exists():
            return []

        certificate_files = []

        for article_dir in project_dir.iterdir():
            if article_dir.is_dir():
                for file_path in article_dir.iterdir():
                    if file_path.is_file():
                        certificate_files.append(file_path)

        return sorted(certificate_files)

    def get_article_certificates(
        self,
        project_id: int,
        article_number: str,
    ) -> List[Path]:
        """
        Get all certificate files for a specific article.

        Args:
            project_id: Project ID
            article_number: Article number

        Returns:
            List of certificate file paths

        Example:
            >>> service = FileService(Path('./certificates'))
            >>> certs = service.get_article_certificates(1, 'ART-001')
        """
        article_dir = (
            self.base_dir
            / f"project_{project_id}"
            / f"article_{sanitize_filename(article_number)}"
        )

        if not article_dir.exists():
            return []

        return sorted([f for f in article_dir.iterdir() if f.is_file()])
