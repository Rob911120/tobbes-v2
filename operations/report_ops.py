"""
Report Operations for Tobbes v2.

Generate PDF reports from project data.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, Union, Any
from datetime import datetime

from domain.models import Article, Certificate, Project
from domain.exceptions import ReportGenerationError
from services.pdf_service import PDFService
from ui.styles import REPORT_CSS, get_report_css_with_watermark

logger = logging.getLogger(__name__)


def generate_material_specification_html(
    project: Union[Project, Dict],
    articles: List[Dict],
    certificates: Optional[List[Union[Certificate, Dict]]] = None,
    include_watermark: bool = True,
) -> str:
    """
    Generate HTML material specification from project articles.

    Args:
        project: Project information (Project object or dict)
        articles: List of article dicts (from get_articles_for_project)
        certificates: Optional list of certificates (Certificate objects or dicts)
        include_watermark: Include FA-TEC watermark

    Returns:
        HTML string with material specification

    Example:
        >>> html = generate_material_specification_html(project, articles)
    """
    # Get CSS and body class
    if include_watermark:
        css, body_class = get_report_css_with_watermark()
    else:
        css = REPORT_CSS
        body_class = "report-page"

    # Build certificate lookup
    cert_lookup = _build_certificate_lookup(certificates or [])

    # Build HTML with proper v1 structure
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Materialspecifikation</title>",
        css,
        "</head>",
        f'<body class="{body_class}">',
        '<div class="container">',
        _build_project_header(project),
        _build_articles_table(articles, cert_lookup),
        _build_footer(),
        "</div>",
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


# ==================== Helper Functions ====================


def _build_certificate_lookup(certificates: List[Union[Certificate, Dict]]) -> Dict[str, List]:
    """
    Build lookup dict of certificates by article number.

    Args:
        certificates: List of certificates (Certificate objects or dicts)

    Returns:
        Dict mapping article_number -> list of certificates
    """
    lookup = {}
    for cert in certificates:
        # Handle both Certificate object and dict
        article_number = cert.article_number if hasattr(cert, 'article_number') else cert.get('article_number', '')

        if article_number not in lookup:
            lookup[article_number] = []
        lookup[article_number].append(cert)
    return lookup


def _build_project_header(project: Union[Project, Dict]) -> str:
    """Build HTML project header section using v1 class names."""
    # Handle both Project object and dict
    if isinstance(project, dict):
        project_name = project.get("project_name", "")
        order_number = project.get("order_number", "")
        customer = project.get("customer", "")
    else:
        project_name = project.project_name
        order_number = project.order_number
        customer = project.customer

    return f"""
    <header class="page-header">
        <h1 class="page-header__title">Material Specification</h1>
        <h2 class="page-header__subtitle">Project: {order_number or 'Not specified'}</h2>
    </header>
    <div class="info-block">
        <div class="info-block__project">
            <strong>Projekt:</strong> {project_name}<br>
            <strong>Kund:</strong> {customer}
        </div>
        <div class="info-block__meta">
            Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
    """


def _build_articles_table(
    articles: List[Dict],
    cert_lookup: Dict[str, List],
) -> str:
    """Build HTML articles table using v1 class names."""
    rows = []
    rows.append("<table class='base-table data-table'>")
    rows.append("<thead>")
    rows.append("<tr>")
    rows.append("<th class='col-level'>Nivå</th>")
    rows.append("<th class='col-article'>Artikel</th>")
    rows.append("<th class='col-description'>Benämning</th>")
    rows.append("<th class='col-quantity'>Antal</th>")
    rows.append("<th class='col-batch'>Batch</th>")
    rows.append("<th class='col-charge'>Charge</th>")
    rows.append("<th class='col-page'>Certifikat</th>")
    rows.append("</tr>")
    rows.append("</thead>")
    rows.append("<tbody>")

    for article in articles:
        article_num = article.get("article_number", "")
        desc = article.get("global_description", article.get("description", ""))
        qty = article.get("quantity", 0.0)
        level = article.get("level_number", article.get("level", ""))
        batch = article.get("batch_number", "")
        charge = article.get("charge_number", "")

        # Get certificates for this article
        certs = cert_lookup.get(article_num, [])
        # Handle both Certificate objects and dicts
        cert_types = []
        for c in certs:
            cert_type = c.certificate_type if hasattr(c, 'certificate_type') else c.get('certificate_type', '')
            cert_types.append(cert_type)
        cert_info = ", ".join(cert_types) if cert_types else ""

        rows.append("<tr>")
        rows.append(f"<td class='col-level'>{level}</td>")
        rows.append(f"<td class='col-article'>{article_num}</td>")
        rows.append(f"<td class='col-description'>{desc}</td>")
        rows.append(f"<td class='col-quantity'>{qty:.1f}</td>")
        rows.append(f"<td class='col-batch'>{batch}</td>")
        rows.append(f"<td class='col-charge'>{charge}</td>")
        rows.append(f"<td class='col-page'>{cert_info}</td>")
        rows.append("</tr>")

    rows.append("</tbody>")
    rows.append("</table>")

    return "\n".join(rows)


def _build_certificate_toc(certificates: List[Union[Certificate, Dict]]) -> str:
    """Build certificate table of contents."""
    if not certificates:
        return "<p>(Inga certifikat)</p>"

    rows = []
    rows.append("<ul>")

    # Group by article
    by_article = {}
    for cert in certificates:
        # Handle both Certificate object and dict
        article_number = cert.article_number if hasattr(cert, 'article_number') else cert.get('article_number', '')

        if article_number not in by_article:
            by_article[article_number] = []
        by_article[article_number].append(cert)

    for article_num, certs in sorted(by_article.items()):
        rows.append(f"<li><strong>{article_num}</strong>")
        rows.append("<ul>")
        for cert in certs:
            # Handle both Certificate object and dict
            cert_type = cert.certificate_type if hasattr(cert, 'certificate_type') else cert.get('certificate_type', '')
            orig_filename = cert.original_filename if hasattr(cert, 'original_filename') else cert.get('original_filename', '')
            rows.append(f"<li>{cert_type}: {orig_filename}</li>")
        rows.append("</ul>")
        rows.append("</li>")

    rows.append("</ul>")

    return "\n".join(rows)


def _build_footer() -> str:
    """Build HTML footer using v1 class names."""
    return f"""
    <footer class="page-footer">
        <p>Genererad av Tobbes v2 - Spårbarhetsguiden</p>
        <p>Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
    """


# ==================== Summary Functions ====================


def get_report_summary(
    articles: List[Dict],
    certificates: List[Dict[str, Any]],
) -> Dict[str, any]:
    """
    Get report generation summary statistics.

    Args:
        articles: List of article dicts
        certificates: List of certificate dicts

    Returns:
        Dict with summary statistics

    Example:
        >>> summary = get_report_summary(articles, certs)
        >>> print(f"Artiklar: {summary['article_count']}")
    """
    # Count articles with/without charges
    articles_with_charge = sum(
        1 for a in articles if a.get("charge_number")
    )
    articles_without_charge = len(articles) - articles_with_charge

    # Count articles with certificates
    articles_with_certs = len(set(c["article_number"] for c in certificates))

    return {
        "article_count": len(articles),
        "articles_with_charge": articles_with_charge,
        "articles_without_charge": articles_without_charge,
        "certificate_count": len(certificates),
        "articles_with_certificates": articles_with_certs,
        "unique_certificate_types": len(set(c["certificate_type"] for c in certificates)),
    }


def filter_articles_by_charge_status(
    articles: List[Dict],
    has_charge: bool,
) -> List[Dict]:
    """
    Filter articles by charge status.

    Args:
        articles: List of article dicts
        has_charge: True to get articles WITH charge, False for WITHOUT

    Returns:
        Filtered list of articles

    Example:
        >>> without_charge = filter_articles_by_charge_status(articles, has_charge=False)
    """
    return [
        a for a in articles
        if bool(a.get("charge_number")) == has_charge
    ]


# ==================== Table of Contents (TOC) Functions ====================


def create_toc_cover_html(
    project: Union[Project, Dict],
    toc_data: Dict[str, Dict[str, int]],
    article_count: int = 0,
) -> str:
    """
    Skapa kombinerad HTML för försättsblad + innehållsförteckning.

    Args:
        project: Project information (Project object or dict)
        toc_data: TOC data från build_table_of_contents()
                  Format: {'Section': {'page_start': X, 'page_end': Y}, ...}
        article_count: Antal artiklar i rapporten

    Returns:
        HTML string med cover + TOC

    Example:
        >>> toc_data = {'Rapport': {'page_start': 2, 'page_end': 4}}
        >>> html = create_toc_cover_html(project, toc_data, article_count=25)
    """
    # Handle both Project object and dict
    if isinstance(project, dict):
        project_name = project.get("project_name", "")
        order_number = project.get("order_number", "")
        customer = project.get("customer", "")
    else:
        project_name = project.project_name
        order_number = project.order_number
        customer = project.customer

    # Get CSS with watermark
    css, body_class = get_report_css_with_watermark()

    # Build TOC table rows
    toc_rows = []
    for section_name, section_info in toc_data.items():
        page_start = section_info['page_start']
        page_end = section_info['page_end']

        if page_start == page_end:
            page_text = str(page_start)
        else:
            page_text = f"{page_start}-{page_end}"

        toc_rows.append(f"""
            <tr>
                <td class="col-article">{section_name}</td>
                <td class="col-pages">{page_text}</td>
            </tr>
        """)

    toc_table = ''.join(toc_rows)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Traceability Report - {order_number}</title>
        {css}
    </head>
    <body class="{body_class}">
        <div class="container">
            <header class="page-header">
                <h1 class="page-header__title">Traceability Report</h1>
                <h2 class="page-header__subtitle">Complete documentation with attached certificates</h2>
            </header>

            <div class="info-block" style="flex-direction: column; align-items: flex-start; gap: var(--spacing-s); margin-bottom: var(--spacing-l);">
                <p><strong>Project:</strong> {project_name}</p>
                <p><strong>Order number:</strong> {order_number}</p>
                <p><strong>Customer:</strong> {customer}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
                <p><strong>Number of articles:</strong> {article_count}</p>
            </div>

            <h3 style="color: var(--color-primary); margin-bottom: var(--spacing-m); font-size: 1.2rem;">
                Table of Contents
            </h3>

            <table class="base-table data-table">
                <thead>
                    <tr>
                        <th class="col-article">Section</th>
                        <th class="col-pages">Pages</th>
                    </tr>
                </thead>
                <tbody>
                    {toc_table}
                </tbody>
            </table>

            <footer class="page-footer">
                <p>Report generated {datetime.now().strftime('%Y-%m-%d')} - Tobbes v2</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return html


def generate_report_with_toc(
    pdf_service: PDFService,
    project: Union[Project, Dict],
    articles: List[Dict],
    certificates: List[Union[Certificate, Dict]],
    output_path: Path,
    base_dir: Path,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Path:
    """
    Generera komplett rapport med Table of Contents.

    Pipeline:
    1. Generera materialspecifikation HTML → PDF
    2. Stämpla med metadata (doc_type="Rapport")
    3. Skapa section dividers för varje certifikattyp
    4. Stämpla dividers med metadata
    5. Stämpla alla certifikat med metadata
    6. Slå samman allt till temp PDF
    7. Extrahera metadata från temp PDF
    8. Bygg TOC från metadata
    9. Skapa TOC cover HTML → PDF
    10. Slå samman TOC + temp PDF
    11. Lägg till sidnummer på alla sidor

    Args:
        pdf_service: PDFService instance (injected)
        project: Project information
        articles: List of article dicts
        certificates: List of certificates
        output_path: Final output path
        base_dir: Base directory for certificates
        progress_callback: Optional progress callback (0-100)

    Returns:
        Path to final PDF with TOC

    Raises:
        ReportGenerationError: If generation fails

    Example:
        >>> service = create_pdf_service()
        >>> pdf = generate_report_with_toc(service, project, articles, certs, output, base)
    """
    from services.pdf_utils import (
        stamp_pdf_with_metadata,
        extract_metadata_stamps,
        add_page_numbers_to_pdf,
        PDFStampMarkers
    )
    from services.pdf_service import build_table_of_contents
    import shutil
    import tempfile

    logger.info("Generating complete report with TOC...")
    markers = PDFStampMarkers()

    try:
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="tobbes_toc_"))
        logger.debug(f"Using temp directory: {temp_dir}")

        if progress_callback:
            progress_callback(5)

        # 1. Generate main material specification
        logger.info("Step 1: Generating material specification...")
        main_html = generate_material_specification_html(
            project=project,
            articles=articles,
            certificates=certificates,
            include_watermark=True
        )

        main_pdf_path = temp_dir / "main_report.pdf"
        pdf_service.html_to_pdf(main_html, main_pdf_path)

        # Stamp main report
        stamp_pdf_with_metadata(main_pdf_path, "Rapport", "Rapport", markers)
        logger.info("Main report generated and stamped")

        if progress_callback:
            progress_callback(20)

        # 2. Group certificates by type
        logger.info("Step 2: Grouping certificates by type...")
        cert_groups = {}
        for cert in certificates:
            cert_type = cert.certificate_type if hasattr(cert, 'certificate_type') else cert.get('certificate_type', 'Other')
            if cert_type not in cert_groups:
                cert_groups[cert_type] = []
            cert_groups[cert_type].append(cert)

        if progress_callback:
            progress_callback(30)

        # 3. Create section dividers and stamp certificates
        logger.info("Step 3: Creating dividers and stamping certificates...")
        all_pdfs = [main_pdf_path]

        for cert_type, certs in cert_groups.items():
            # Create divider
            divider_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        font-family: 'Helvetica', Arial, sans-serif;
                        margin: 0;
                    }}
                    .divider-box {{
                        text-align: center;
                        padding: 60px;
                        border: 3px solid #007bff;
                        border-radius: 8px;
                    }}
                    h1 {{
                        color: #007bff;
                        font-size: 2.5rem;
                        margin: 0 0 20px 0;
                        text-transform: uppercase;
                        letter-spacing: 2px;
                    }}
                    p {{
                        color: #6c757d;
                        font-size: 1rem;
                        margin: 0;
                    }}
                </style>
            </head>
            <body>
                <div class="divider-box">
                    <h1>{cert_type}</h1>
                    <p>Attached certificates and documents</p>
                </div>
            </body>
            </html>
            """

            divider_path = temp_dir / f"divider_{cert_type.replace(' ', '_').lower()}.pdf"
            pdf_service.html_to_pdf(divider_html, divider_path)
            stamp_pdf_with_metadata(divider_path, cert_type, cert_type, markers)
            all_pdfs.append(divider_path)

            # Add and stamp certificates
            for cert in certs:
                # Get certificate path
                if hasattr(cert, 'get_full_path'):
                    cert_path = cert.get_full_path(base_dir)
                else:
                    stored_path = cert.get('stored_path', cert.get('file_path', ''))

                    # Handle both absolute and relative paths
                    if stored_path:
                        cert_path_obj = Path(stored_path)
                        if cert_path_obj.is_absolute():
                            cert_path = cert_path_obj  # Use absolute path directly
                        else:
                            cert_path = base_dir / stored_path  # Combine with base_dir
                    else:
                        cert_path = None

                if cert_path and cert_path.exists():
                    # Copy to temp and stamp
                    temp_cert = temp_dir / f"cert_{cert_path.name}"
                    shutil.copy2(cert_path, temp_cert)

                    article_num = cert.article_number if hasattr(cert, 'article_number') else cert.get('article_number', '')
                    stamp_pdf_with_metadata(temp_cert, article_num, cert_type, markers)
                    all_pdfs.append(temp_cert)
                else:
                    # Log warning for missing certificate
                    article_num = cert.article_number if hasattr(cert, 'article_number') else cert.get('article_number', '')
                    logger.warning(f"Certificate not found: {cert_path} (article: {article_num}, type: {cert_type})")

        if progress_callback:
            progress_callback(50)

        # 4. Merge all PDFs (without TOC)
        logger.info("Step 4: Merging all PDFs...")
        temp_merged_path = temp_dir / "merged_no_toc.pdf"
        pdf_service.merge_pdfs(all_pdfs, temp_merged_path)

        if progress_callback:
            progress_callback(60)

        # 5. Extract metadata stamps
        logger.info("Step 5: Extracting metadata stamps...")
        stamps = extract_metadata_stamps(temp_merged_path, markers)
        logger.info(f"Extracted {len(stamps)} metadata stamps")

        if progress_callback:
            progress_callback(70)

        # 6. Build TOC
        logger.info("Step 6: Building table of contents...")
        toc_data = build_table_of_contents(stamps)
        logger.info(f"TOC built with {len(toc_data)} sections")

        # 7. Create TOC cover page
        logger.info("Step 7: Creating TOC cover page...")
        toc_html = create_toc_cover_html(
            project=project,
            toc_data=toc_data,
            article_count=len(articles)
        )

        toc_pdf_path = temp_dir / "toc_cover.pdf"
        pdf_service.html_to_pdf(toc_html, toc_pdf_path)
        stamp_pdf_with_metadata(toc_pdf_path, "TOC", "Cover", markers)

        if progress_callback:
            progress_callback(80)

        # 8. Merge TOC + rest
        logger.info("Step 8: Merging TOC with rest of report...")
        temp_final_path = temp_dir / "final_no_page_nums.pdf"
        pdf_service.merge_pdfs([toc_pdf_path, temp_merged_path], temp_final_path)

        if progress_callback:
            progress_callback(90)

        # 9. Add page numbers
        logger.info("Step 9: Adding page numbers...")
        shutil.copy2(temp_final_path, output_path)
        add_page_numbers_to_pdf(output_path)

        if progress_callback:
            progress_callback(100)

        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Could not clean up temp directory: {e}")

        logger.info(f"Report with TOC generated successfully: {output_path}")
        return output_path

    except Exception as e:
        logger.exception("Failed to generate report with TOC")
        raise ReportGenerationError(
            f"Kunde inte generera rapport med TOC: {e}",
            details={"output_path": str(output_path), "error": str(e)}
        )
