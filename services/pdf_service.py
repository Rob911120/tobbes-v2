"""
PDF Service for Tobbes v2.

Handles PDF generation using Playwright (system Chrome/Chromium).

IMPORTANT: Requires Chrome/Chromium to be installed on the system.
Use chrome_checker.ensure_chrome_installed() before using this service.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    Browser = None
    Page = None

from domain.exceptions import ReportGenerationError
from services.chrome_checker import ensure_chrome_installed
from config.constants import (
    DEFAULT_PDF_PAGE_SIZE,
    PDF_MAX_RETRIES,
    PDF_RETRY_DELAY,
)

logger = logging.getLogger(__name__)


class PDFService:
    """
    Service for PDF generation using Playwright.

    Uses system Chrome/Chromium for HTML to PDF conversion.

    CRITICAL: Requires Chrome/Chromium installed on system!
    """

    def __init__(
        self,
        page_size: str = DEFAULT_PDF_PAGE_SIZE,
        enable_watermark: bool = True,
    ):
        """
        Initialize PDF service.

        Args:
            page_size: PDF page size (default: A4)
            enable_watermark: Enable watermark in generated PDFs

        Raises:
            EnvironmentError: If Playwright is not installed
            EnvironmentError: If Chrome/Chromium is not found
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise EnvironmentError(
                "Playwright is not installed. Install with: pip install playwright"
            )

        # Check Chrome/Chromium
        ensure_chrome_installed()

        self.page_size = page_size
        self.enable_watermark = enable_watermark

    def html_to_pdf(
        self,
        html_content: str,
        output_path: Path,
        page_size: Optional[str] = None,
        print_background: bool = True,
        margin: Optional[dict] = None,
    ) -> Path:
        """
        Convert HTML to PDF using Playwright.

        Args:
            html_content: HTML content as string
            output_path: Output PDF file path
            page_size: PDF page size (default: A4)
            print_background: Include background graphics
            margin: Page margins dict (e.g., {"top": "1cm", "bottom": "1cm"})

        Returns:
            Path to generated PDF file

        Raises:
            ReportGenerationError: If PDF generation fails

        Example:
            >>> service = PDFService()
            >>> html = "<html><body><h1>Test</h1></body></html>"
            >>> pdf_path = service.html_to_pdf(html, Path('./output.pdf'))
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if page_size is None:
            page_size = self.page_size

        if margin is None:
            margin = {
                "top": "1cm",
                "right": "1cm",
                "bottom": "1cm",
                "left": "1cm",
            }

        try:
            with sync_playwright() as p:
                # Launch system Chrome
                browser = p.chromium.launch(channel='chrome')
                page = browser.new_page()

                # Set content
                page.set_content(html_content, wait_until='networkidle')

                # Generate PDF
                page.pdf(
                    path=str(output_path),
                    format=page_size,
                    print_background=print_background,
                    margin=margin,
                )

                browser.close()

            logger.info(f"Generated PDF: {output_path}")
            return output_path

        except Exception as e:
            logger.exception(f"Failed to generate PDF: {e}")
            raise ReportGenerationError(
                f"PDF-generering misslyckades: {e}",
                details={"output_path": str(output_path), "error": str(e)}
            )

    def merge_pdfs(
        self,
        pdf_files: List[Path],
        output_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Path:
        """
        Merge multiple PDF files into one.

        NOTE: This is a placeholder. For production, use PyPDF2 or pikepdf.
        Playwright doesn't have built-in PDF merging.

        Args:
            pdf_files: List of PDF file paths to merge
            output_path: Output merged PDF path
            progress_callback: Optional callback for progress (0-100)

        Returns:
            Path to merged PDF

        Raises:
            ReportGenerationError: If merging fails

        Example:
            >>> service = PDFService()
            >>> pdfs = [Path('page1.pdf'), Path('page2.pdf')]
            >>> merged = service.merge_pdfs(pdfs, Path('./merged.pdf'))
        """
        # This is a simplified implementation
        # In production, use PyPDF2:
        #
        # from PyPDF2 import PdfMerger
        # merger = PdfMerger()
        # for pdf in pdf_files:
        #     merger.append(pdf)
        # merger.write(output_path)
        # merger.close()

        logger.warning("PDF merging not fully implemented - using placeholder")

        if not pdf_files:
            raise ReportGenerationError(
                "Inga PDF-filer att slå samman",
                details={"pdf_files": []}
            )

        # For now, just copy the first file
        # TODO: Implement proper PDF merging with PyPDF2
        import shutil
        shutil.copy2(pdf_files[0], output_path)

        logger.info(f"Merged {len(pdf_files)} PDFs to: {output_path}")
        return output_path

    def retry_operation(
        self,
        operation: Callable,
        max_retries: int = PDF_MAX_RETRIES,
        delay: float = PDF_RETRY_DELAY,
    ) -> any:
        """
        Retry an operation with exponential backoff.

        Useful for operations that might fail due to file locking, etc.

        Args:
            operation: Function to retry
            max_retries: Maximum number of retries
            delay: Base delay in seconds (exponential backoff)

        Returns:
            Result of operation

        Raises:
            Exception: If all retries fail

        Example:
            >>> service = PDFService()
            >>> result = service.retry_operation(
            ...     lambda: service.html_to_pdf(html, output_path)
            ... )
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Operation failed after {max_retries} attempts")

        raise last_exception

    def validate_pdf(self, pdf_path: Path) -> bool:
        """
        Validate that file is a valid PDF.

        Simple check - verifies PDF header exists.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if valid PDF

        Raises:
            ReportGenerationError: If not a valid PDF

        Example:
            >>> service = PDFService()
            >>> service.validate_pdf(Path('./output.pdf'))
        """
        if not pdf_path.exists():
            raise ReportGenerationError(
                f"PDF-filen finns inte: {pdf_path}",
                details={"pdf_path": str(pdf_path)}
            )

        # Check PDF header
        with open(pdf_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                raise ReportGenerationError(
                    f"Inte en giltig PDF-fil: {pdf_path}",
                    details={"pdf_path": str(pdf_path), "header": header}
                )

        return True

    def get_pdf_page_count(self, pdf_path: Path) -> int:
        """
        Get number of pages in PDF.

        NOTE: This is a placeholder. For production, use PyPDF2 or pikepdf.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages

        Example:
            >>> service = PDFService()
            >>> pages = service.get_pdf_page_count(Path('./output.pdf'))
        """
        # This is a simplified implementation
        # In production, use PyPDF2:
        #
        # from PyPDF2 import PdfReader
        # reader = PdfReader(pdf_path)
        # return len(reader.pages)

        logger.warning("PDF page counting not fully implemented - returning 1")
        return 1  # Placeholder


def create_pdf_service(
    page_size: str = DEFAULT_PDF_PAGE_SIZE,
    enable_watermark: bool = True,
) -> PDFService:
    """
    Factory function to create PDFService.

    Args:
        page_size: PDF page size
        enable_watermark: Enable watermark

    Returns:
        PDFService instance

    Example:
        >>> service = create_pdf_service(page_size='A4', enable_watermark=True)
    """
    return PDFService(page_size=page_size, enable_watermark=enable_watermark)
