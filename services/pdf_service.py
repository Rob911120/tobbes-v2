"""
PDF Service for Tobbes v2.

Handles PDF generation using Playwright (system Chrome/Chromium).

IMPORTANT: Requires Chrome/Chromium to be installed on the system.
Use chrome_checker.ensure_chrome_installed() before using this service.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Callable, Dict
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    Browser = None
    Page = None

try:
    from pypdf import PdfWriter, PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    PdfWriter = None
    PdfReader = None

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

        Uses pypdf library for actual PDF concatenation with progress tracking.

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
        if not PYPDF_AVAILABLE:
            raise ReportGenerationError(
                "pypdf is not installed. Install with: pip install pypdf",
                details={"library": "pypdf"}
            )

        if not pdf_files:
            raise ReportGenerationError(
                "Inga PDF-filer att slå samman",
                details={"pdf_files": []}
            )

        # Validate all input files exist
        for pdf_file in pdf_files:
            if not pdf_file.exists():
                raise ReportGenerationError(
                    f"PDF-fil saknas: {pdf_file}",
                    details={"pdf_file": str(pdf_file)}
                )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            writer = PdfWriter()
            total_files = len(pdf_files)

            logger.info(f"Merging {total_files} PDF files...")

            for index, pdf_file in enumerate(pdf_files):
                try:
                    # Read PDF
                    reader = PdfReader(str(pdf_file))

                    # Append all pages
                    for page in reader.pages:
                        writer.add_page(page)

                    # Update progress
                    if progress_callback:
                        progress = int(((index + 1) / total_files) * 100)
                        progress_callback(progress)

                    logger.debug(f"Merged {pdf_file.name} ({len(reader.pages)} pages)")

                except Exception as e:
                    logger.warning(f"Failed to merge {pdf_file}: {e}")
                    # Continue with other files

            # Write merged PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            logger.info(f"Successfully merged {total_files} PDFs to: {output_path}")

            # Final progress update
            if progress_callback:
                progress_callback(100)

            return output_path

        except Exception as e:
            logger.exception(f"Failed to merge PDFs: {e}")
            raise ReportGenerationError(
                f"PDF-sammanslagning misslyckades: {e}",
                details={
                    "pdf_files": [str(f) for f in pdf_files],
                    "output_path": str(output_path),
                    "error": str(e)
                }
            )

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

    def create_separator_page(
        self,
        title: str,
        subtitle: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Create a separator page for PDF sections.

        Creates a simple HTML page with a title and optional subtitle,
        then converts it to PDF.

        Args:
            title: Main title for separator page
            subtitle: Optional subtitle
            output_path: Output path (auto-generated if not provided)

        Returns:
            Path to separator PDF

        Example:
            >>> service = PDFService()
            >>> separator = service.create_separator_page(
            ...     title="Materialintyg",
            ...     subtitle="Artikel ART-001"
            ... )
        """
        if output_path is None:
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "tobbes_separators"
            temp_dir.mkdir(exist_ok=True)
            output_path = temp_dir / f"separator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Create HTML for separator page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                }}
                .separator-content {{
                    text-align: center;
                    padding: 40px;
                }}
                h1 {{
                    font-size: 36px;
                    color: #333;
                    margin: 0 0 20px 0;
                    font-weight: bold;
                }}
                h2 {{
                    font-size: 24px;
                    color: #666;
                    margin: 0;
                    font-weight: normal;
                }}
            </style>
        </head>
        <body>
            <div class="separator-content">
                <h1>{title}</h1>
                {f'<h2>{subtitle}</h2>' if subtitle else ''}
            </div>
        </body>
        </html>
        """

        # Generate separator PDF
        return self.html_to_pdf(html_content, output_path)

    def merge_pdfs_with_separators(
        self,
        pdf_groups: Dict[str, List[Path]],
        output_path: Path,
        add_separators: bool = True,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Path:
        """
        Merge PDF files grouped by category with optional separator pages.

        This is useful for creating reports where certificates are grouped
        by type (e.g., "Materialintyg", "Svetslogg", etc.).

        Args:
            pdf_groups: Dict mapping group names to list of PDF paths
                       e.g., {"Materialintyg": [cert1.pdf, cert2.pdf]}
            output_path: Output merged PDF path
            add_separators: Add separator pages between groups
            progress_callback: Optional callback for progress (0-100)

        Returns:
            Path to merged PDF

        Raises:
            ReportGenerationError: If merging fails

        Example:
            >>> service = PDFService()
            >>> groups = {
            ...     "Materialintyg": [Path('cert1.pdf'), Path('cert2.pdf')],
            ...     "Svetslogg": [Path('cert3.pdf')]
            ... }
            >>> merged = service.merge_pdfs_with_separators(groups, Path('./report.pdf'))
        """
        if not pdf_groups:
            raise ReportGenerationError(
                "Inga PDF-grupper att slå samman",
                details={"pdf_groups": {}}
            )

        try:
            all_pdfs = []
            separator_pdfs = []

            # Calculate total for progress
            total_groups = len(pdf_groups)
            processed_groups = 0

            for group_name, pdf_files in pdf_groups.items():
                if not pdf_files:
                    continue

                # Create separator page if requested
                if add_separators:
                    separator_pdf = self.create_separator_page(
                        title=group_name,
                        subtitle=f"{len(pdf_files)} dokument"
                    )
                    all_pdfs.append(separator_pdf)
                    separator_pdfs.append(separator_pdf)

                # Add all PDFs in this group
                all_pdfs.extend(pdf_files)

                # Update progress
                processed_groups += 1
                if progress_callback:
                    progress = int((processed_groups / total_groups) * 90)  # Save 10% for final merge
                    progress_callback(progress)

            # Merge all PDFs
            result = self.merge_pdfs(
                pdf_files=all_pdfs,
                output_path=output_path,
                progress_callback=lambda p: progress_callback(90 + p // 10) if progress_callback else None
            )

            # Clean up separator PDFs
            for separator_pdf in separator_pdfs:
                try:
                    separator_pdf.unlink()
                except Exception:
                    pass  # Ignore cleanup errors

            logger.info(f"Merged {len(pdf_groups)} groups ({len(all_pdfs)} total PDFs) to: {output_path}")

            return result

        except Exception as e:
            logger.exception(f"Failed to merge PDFs with separators: {e}")
            raise ReportGenerationError(
                f"PDF-sammanslagning med avdelare misslyckades: {e}",
                details={
                    "pdf_groups": {k: [str(f) for f in v] for k, v in pdf_groups.items()},
                    "output_path": str(output_path),
                    "error": str(e)
                }
            )

    def get_pdf_page_count(self, pdf_path: Path) -> int:
        """
        Get number of pages in PDF.

        Uses pypdf library to accurately count pages.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages

        Raises:
            ReportGenerationError: If unable to read PDF

        Example:
            >>> service = PDFService()
            >>> pages = service.get_pdf_page_count(Path('./output.pdf'))
        """
        if not PYPDF_AVAILABLE:
            logger.warning("pypdf not available - returning 1")
            return 1

        if not pdf_path.exists():
            raise ReportGenerationError(
                f"PDF-fil saknas: {pdf_path}",
                details={"pdf_path": str(pdf_path)}
            )

        try:
            reader = PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            logger.debug(f"PDF {pdf_path.name} has {page_count} pages")
            return page_count

        except Exception as e:
            logger.exception(f"Failed to count PDF pages: {e}")
            raise ReportGenerationError(
                f"Kunde inte räkna sidor i PDF: {e}",
                details={"pdf_path": str(pdf_path), "error": str(e)}
            )


def build_table_of_contents(stamps: List[Dict[str, any]]) -> Dict[str, Dict[str, int]]:
    """
    Bygg innehållsförteckning från metadata-stämplar.

    Grupperar stamps per doc_type och beräknar sidspann.

    VIKTIGT: Lägger till +1 offset på alla sidnummer eftersom TOC kommer
    att infogas först i PDF:en, vilket skjuter alla sidor +1.

    Args:
        stamps: Lista med metadata stamps från extract_metadata_stamps()
                Format: [{'article_id': str, 'doc_type': str, 'pdf_page': int}, ...]

    Returns:
        Dict med TOC-data:
        {
            'Materialintyg': {'page_start': 5, 'page_end': 12},
            'Svetslogg': {'page_start': 13, 'page_end': 18},
            ...
        }

    Example:
        >>> from services.pdf_utils import extract_metadata_stamps
        >>> stamps = extract_metadata_stamps(Path('report.pdf'))
        >>> toc = build_table_of_contents(stamps)
        >>> print(toc)
        {'Rapport': {'page_start': 2, 'page_end': 4}, 'Materialintyg': {'page_start': 5, 'page_end': 12}}
    """
    if not stamps:
        logger.warning("Inga metadata-stämplar att bygga TOC från")
        return {}

    # Gruppera stamps per doc_type
    grouped = {}
    for stamp in stamps:
        doc_type = stamp['doc_type']
        pdf_page = stamp['pdf_page']

        if doc_type not in grouped:
            grouped[doc_type] = []
        grouped[doc_type].append(pdf_page)

    # Bygg TOC med sidspann (offset +1 för att kompensera TOC som sida 1)
    toc = {}
    for doc_type, pages in grouped.items():
        pages.sort()  # Sortera sidnummer
        toc[doc_type] = {
            'page_start': pages[0] + 1,  # +1 offset för TOC
            'page_end': pages[-1] + 1     # +1 offset för TOC
        }

    logger.info(f"Byggde TOC med {len(toc)} sektioner (offset +1): {list(toc.keys())}")
    return toc


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
