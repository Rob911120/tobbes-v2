"""
Certificate Service for Tobbes v2.

Handles certificate processing:
- Generate unique IDs
- Copy files to project directory
- Stamp PDFs with metadata
- Save to database

Based on v1's certificate_manager.py implementation.
"""

import shutil
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from config.paths import get_project_certificates_path
from services.pdf_utils import stamp_pdf_with_metadata, count_pdf_pages, validate_pdf, PDFStampMarkers
from data.interface import DatabaseInterface
from domain.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Service for certificate processing.

    Handles:
    - Generating unique certificate IDs
    - Copying files to project directories
    - Stamping PDFs with metadata
    - Database persistence
    """

    def __init__(self):
        """Initialize certificate service."""
        self.markers = PDFStampMarkers()

    def generate_certificate_id(self, article_num: str, cert_type: str) -> str:
        """
        Generate unique certificate ID.

        Format: ART_{article}_{type}_{timestamp}

        Args:
            article_num: Article number
            cert_type: Certificate type (e.g., 'Materialintyg')

        Returns:
            Unique certificate ID

        Example:
            >>> service.generate_certificate_id("12345", "Materialintyg")
            'ART_12345_Materialintyg_20250107_143022'
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize characters invalid for filenames
        safe_article = re.sub(r'[<>:"/\\|?*]', '_', article_num)
        safe_type = re.sub(r'[<>:"/\\|?*]', '_', cert_type)

        # Format: ART_12345_Materialintyg_20250107_143022
        cert_id = f"ART_{safe_article}_{safe_type}_{timestamp}"

        logger.debug(f"Generated certificate ID: {cert_id}")
        return cert_id

    def copy_certificate(
        self,
        original_path: Path,
        order_number: str,
        cert_id: str
    ) -> Path:
        """
        Copy certificate to project certificates directory.

        Args:
            original_path: Original path to certificate file
            order_number: Project order number (e.g., "TO-12345")
            cert_id: Unique certificate ID

        Returns:
            Path to copied certificate

        Raises:
            FileNotFoundError: If original file doesn't exist
            PermissionError: If copy fails due to permissions
        """
        # Get project certificates directory (creates if doesn't exist)
        dest_dir = get_project_certificates_path(order_number)

        # New filename with .pdf extension
        new_filename = f"{cert_id}.pdf"
        dest_path = dest_dir / new_filename

        try:
            shutil.copy2(original_path, dest_path)
            logger.info(f"Copied certificate: {original_path.name} -> {new_filename}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to copy certificate: {e}")
            raise

    def process_certificate(
        self,
        original_path: Path,
        article_num: str,
        cert_type: str,
        project_id: int,
        db: DatabaseInterface
    ) -> Dict[str, Any]:
        """
        Complete certificate processing pipeline.

        Steps:
        1. Validate input
        2. Generate unique ID
        3. Copy to project directory
        4. Stamp PDF with metadata
        5. Count pages
        6. Save to database
        7. Return certificate data

        Args:
            original_path: Original path to certificate file
            article_num: Article number
            cert_type: Certificate type
            project_id: Project ID
            db: Database interface

        Returns:
            Dict with result:
                {
                    'success': bool,
                    'data': dict,  # Certificate data (if success)
                    'message': str
                }

        Example:
            >>> result = service.process_certificate(
            ...     Path('/tmp/cert.pdf'),
            ...     '12345',
            ...     'Materialintyg',
            ...     1,
            ...     db
            ... )
            >>> result['success']
            True
            >>> result['data']['certificate_id']
            'ART_12345_Materialintyg_20250107_143022'
        """
        try:
            # 0. Get project order number from database
            project = db.get_project(project_id)
            if not project:
                raise ValidationError(
                    f"Projekt med ID {project_id} finns inte",
                    details={'project_id': project_id}
                )
            order_number = project.get('order_number')
            if not order_number:
                raise ValidationError(
                    f"Projekt saknar ordernummer",
                    details={'project_id': project_id}
                )

            # 1. Validate input
            if not original_path.exists():
                raise FileNotFoundError(f"Certifikat finns inte: {original_path}")

            if not original_path.suffix.lower() == '.pdf':
                raise ValidationError(
                    f"Endast PDF-filer stöds, fick: {original_path.suffix}",
                    details={'file_type': original_path.suffix}
                )

            if not validate_pdf(original_path):
                raise ValidationError(
                    f"Ogiltig PDF-fil: {original_path.name}",
                    details={'file_path': str(original_path)}
                )

            # 2. Generate unique ID
            cert_id = self.generate_certificate_id(article_num, cert_type)

            # 3. Copy to project directory (using order_number)
            new_path = self.copy_certificate(original_path, order_number, cert_id)

            # 4. Stamp PDF with metadata
            stamp_success = stamp_pdf_with_metadata(
                pdf_path=new_path,
                article_id=article_num,
                doc_type=cert_type,
                markers=self.markers
            )

            if not stamp_success:
                logger.warning(f"Stamping failed for {cert_id} but file copied")

            # 5. Count pages
            page_count = count_pdf_pages(new_path)

            # 6. Prepare certificate data
            # stored_path is FULL absolute path (fixed to match v1 behavior - certificates now persist!)
            cert_dir = get_project_certificates_path(order_number)
            stored_path = str(cert_dir / f"{cert_id}.pdf")  # Full absolute path
            stored_name = f"{cert_id}.pdf"
            original_name = original_path.name

            # 7. Save to database
            logger.info(f"📦 SAVING CERTIFICATE TO DATABASE:")
            logger.info(f"   project_id={project_id}")
            logger.info(f"   article_number={article_num}")
            logger.info(f"   certificate_id={cert_id}")
            logger.info(f"   cert_type={cert_type}")
            logger.info(f"   stored_path={stored_path}")

            try:
                cert_db_id = db.save_certificate(
                    project_id=project_id,
                    article_number=article_num,
                    certificate_id=cert_id,
                    cert_type=cert_type,
                    stored_path=stored_path,
                    stored_name=stored_name,
                    original_name=original_name,
                    page_count=page_count,
                    original_path=str(original_path)  # Save original path for re-processing
                )

                logger.info(f"✅ Certificate saved to database! DB ID: {cert_db_id}")

                # VERIFICATION: Check that certificate was actually saved
                saved_certs = db.get_certificates_for_article(
                    project_id=project_id,
                    article_number=article_num
                )
                logger.info(f"🔍 VERIFICATION: Found {len(saved_certs)} certificates for {article_num} after save")

                # Check if our certificate is in the list
                our_cert_found = any(c.get('certificate_id') == cert_id for c in saved_certs)
                if our_cert_found:
                    logger.info(f"✅ VERIFIED: Certificate {cert_id} found in database immediately after save")
                else:
                    logger.error(f"❌ VERIFICATION FAILED: Certificate {cert_id} NOT found in database after save!")
                    logger.error(f"   Saved certificates: {[c.get('certificate_id') for c in saved_certs]}")

            except Exception as e:
                logger.exception(f"❌ FAILED to save certificate to database: {e}")
                raise

            # 8. Return certificate data
            cert_data = {
                'id': cert_db_id,  # Database ID
                'certificate_id': cert_id,  # Unique cert ID
                'article_number': article_num,
                'type': cert_type,
                'original_name': original_name,
                'stored_path': stored_path,
                'stored_name': stored_name,
                'timestamp': datetime.now().isoformat(),
                'pages': page_count
            }

            logger.info(f"Certificate processed successfully: {cert_id}")
            return {
                'success': True,
                'data': cert_data,
                'message': f"Certifikat tillagt: {cert_id}"
            }

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Fil saknas: {original_path.name}"
            }

        except ValidationError as e:
            logger.error(f"Validation error: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'message': f"Valideringsfel: {e.message}"
            }

        except Exception as e:
            logger.exception(f"Unexpected error processing certificate: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Oväntat fel: {str(e)}"
            }

    def change_certificate_type(
        self,
        certificate_id: int,
        new_cert_type: str,
        project_id: int,
        db: DatabaseInterface
    ) -> Dict[str, Any]:
        """
        Change certificate type without re-uploading.

        Fetches original file, re-processes with new type, deletes old.

        Args:
            certificate_id: Database ID of certificate to change
            new_cert_type: New certificate type
            project_id: Project ID
            db: Database interface

        Returns:
            Dict with result:
                {
                    'success': bool,
                    'data': dict,  # New certificate data (if success)
                    'message': str
                }

        Raises:
            ValidationError: If certificate has no original_path
        """
        try:
            # 1. Get certificate from database
            certificates = db.get_certificates_for_project(project_id)
            cert = next((c for c in certificates if c.get('id') == certificate_id), None)

            if not cert:
                raise ValidationError(
                    f"Certifikat med ID {certificate_id} finns inte",
                    details={'certificate_id': certificate_id}
                )

            # 2. Validate original_path exists
            original_path = cert.get('original_path')
            if not original_path:
                raise ValidationError(
                    "Detta certifikat saknar originalsökväg och kan inte ändras. "
                    "Bara certifikat uppladdat efter 2025-01-08 kan ändras.",
                    details={'certificate_id': certificate_id}
                )

            original_path = Path(original_path)
            if not original_path.exists():
                raise ValidationError(
                    f"Originalfilen finns inte längre: {original_path}",
                    details={'original_path': str(original_path)}
                )

            # 3. Delete old certificate file
            stored_path = Path(cert.get('stored_path'))
            if stored_path.exists():
                stored_path.unlink()
                logger.info(f"Deleted old certificate file: {stored_path}")

            # 4. Delete old certificate from database
            db.delete_certificate(certificate_id)
            logger.info(f"Deleted old certificate from database: {certificate_id}")

            # 5. Process with new type (re-use existing method)
            article_number = cert.get('article_number')
            result = self.process_certificate(
                original_path=original_path,
                article_num=article_number,
                cert_type=new_cert_type,
                project_id=project_id,
                db=db
            )

            if result['success']:
                logger.info(f"Certificate type changed from '{cert.get('certificate_type')}' to '{new_cert_type}'")

            return result

        except ValidationError as e:
            logger.error(f"Validation error: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'message': f"Valideringsfel: {e.message}"
            }

        except Exception as e:
            logger.exception(f"Unexpected error changing certificate type: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Oväntat fel: {str(e)}"
            }


def create_certificate_service() -> CertificateService:
    """
    Factory function for creating CertificateService instance.

    Returns:
        Configured CertificateService
    """
    return CertificateService()
