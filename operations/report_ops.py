"""
Report Operations for Tobbes v2.

Generate PDF reports from project data.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, Union
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
    # Get CSS
    css = get_report_css_with_watermark() if include_watermark else REPORT_CSS
    body_class = 'class="watermarked"' if include_watermark else ""

    # Build certificate lookup
    cert_lookup = _build_certificate_lookup(certificates or [])

    # Build HTML
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Materialspecifikation</title>",
        css,
        "</head>",
        f"<body {body_class}>",
        _build_project_header(project),
        _build_articles_table(articles, cert_lookup),
        _build_footer(),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def generate_pdf_report(
    pdf_service: PDFService,
    html_content: str,
    output_path: Path,
    page_size: str = "A4",
) -> Path:
    """
    Generate PDF report from HTML content.

    Args:
        pdf_service: PDFService instance (injected)
        html_content: HTML content as string
        output_path: Output PDF file path
        page_size: PDF page size (default: A4)

    Returns:
        Path to generated PDF file

    Raises:
        ReportGenerationError: If PDF generation fails

    Example:
        >>> service = create_pdf_service()
        >>> pdf_path = generate_pdf_report(service, html, Path('./report.pdf'))
    """
    logger.info(f"Generating PDF report: {output_path}")

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate PDF
        result_path = pdf_service.html_to_pdf(
            html_content=html_content,
            output_path=output_path,
            page_size=page_size,
        )

        logger.info(f"PDF report generated: {result_path}")
        return result_path

    except Exception as e:
        logger.exception("Failed to generate PDF report")
        raise ReportGenerationError(
            f"Kunde inte generera PDF-rapport: {e}",
            details={"output_path": str(output_path), "error": str(e)}
        )


def merge_certificates_into_report(
    pdf_service: PDFService,
    main_report_path: Path,
    certificates: List[Certificate],
    output_path: Path,
    base_dir: Path,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Path:
    """
    Merge main report with certificate PDFs.

    NOTE: Uses placeholder merge (just copies main report).
    For production, implement proper merging with PyPDF2.

    Args:
        pdf_service: PDFService instance (injected)
        main_report_path: Path to main report PDF
        certificates: List of certificates to merge
        output_path: Output merged PDF path
        base_dir: Base directory for certificate files
        progress_callback: Optional progress callback (0-100)

    Returns:
        Path to merged PDF

    Raises:
        ReportGenerationError: If merging fails

    Example:
        >>> merged = merge_certificates_into_report(
        ...     service, main_pdf, certs, output_path, base_dir
        ... )
    """
    logger.info(f"Merging {len(certificates)} certificates into report")

    try:
        # Build list of PDF files to merge
        pdf_files = [main_report_path]

        for cert in certificates:
            cert_path = cert.get_full_path(base_dir)
            if cert_path.exists():
                pdf_files.append(cert_path)
            else:
                logger.warning(f"Certificate file not found: {cert_path}")

        if progress_callback:
            progress_callback(20)

        # Merge PDFs (placeholder implementation)
        merged_path = pdf_service.merge_pdfs(
            pdf_files=pdf_files,
            output_path=output_path,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(100)

        logger.info(f"Merged report generated: {merged_path}")
        return merged_path

    except Exception as e:
        logger.exception("Failed to merge certificates into report")
        raise ReportGenerationError(
            f"Kunde inte slå samman certifikat: {e}",
            details={
                "main_report": str(main_report_path),
                "certificate_count": len(certificates),
                "error": str(e)
            }
        )


def create_table_of_contents(
    project: Union[Project, Dict],
    articles: List[Dict],
    certificates: List[Union[Certificate, Dict]],
) -> str:
    """
    Generate HTML table of contents for report.

    Args:
        project: Project information (Project object or dict)
        articles: List of article dicts
        certificates: List of certificates (Certificate objects or dicts)

    Returns:
        HTML string with table of contents

    Example:
        >>> toc_html = create_table_of_contents(project, articles, certs)
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

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Innehållsförteckning</title>",
        REPORT_CSS,
        "</head>",
        "<body>",
        "<h1>Innehållsförteckning</h1>",
        f"<div class='project-info'>",
        f"<p><strong>Projekt:</strong> {project_name}</p>",
        f"<p><strong>Ordernummer:</strong> {order_number}</p>",
        f"<p><strong>Kund:</strong> {customer}</p>",
        f"</div>",
        "<h2>Materialspecifikation</h2>",
        f"<p>Artiklar: {len(articles)}</p>",
        "<h2>Certifikat</h2>",
        _build_certificate_toc(certificates),
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
    """Build HTML project header section."""
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
    <h1>Materialspecifikation</h1>
    <div class='project-info'>
        <p><strong>Projekt:</strong> {project_name}</p>
        <p><strong>Ordernummer:</strong> {order_number}</p>
        <p><strong>Kund:</strong> {customer}</p>
        <p><strong>Genererad:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    """


def _build_articles_table(
    articles: List[Dict],
    cert_lookup: Dict[str, List],
) -> str:
    """Build HTML articles table."""
    rows = []
    rows.append("<h2>Artiklar</h2>")
    rows.append("<table>")
    rows.append("<thead>")
    rows.append("<tr>")
    rows.append("<th>Artikelnummer</th>")
    rows.append("<th>Benämning</th>")
    rows.append("<th>Antal</th>")
    rows.append("<th>Nivå</th>")
    rows.append("<th>Charge</th>")
    rows.append("<th>Certifikat</th>")
    rows.append("</tr>")
    rows.append("</thead>")
    rows.append("<tbody>")

    for article in articles:
        article_num = article.get("article_number", "")
        desc = article.get("global_description", article.get("description", ""))
        qty = article.get("quantity", 0.0)
        level = article.get("level", "")
        charge = article.get("charge_number", "(Ingen)")

        # Get certificates for this article
        certs = cert_lookup.get(article_num, [])
        # Handle both Certificate objects and dicts
        cert_types = []
        for c in certs:
            cert_type = c.certificate_type if hasattr(c, 'certificate_type') else c.get('certificate_type', '')
            cert_types.append(cert_type)
        cert_info = ", ".join(cert_types) if cert_types else "(Inga)"

        rows.append("<tr class='article-row'>")
        rows.append(f"<td>{article_num}</td>")
        rows.append(f"<td>{desc}</td>")
        rows.append(f"<td>{qty:.1f}</td>")
        rows.append(f"<td>{level}</td>")
        rows.append(f"<td>{charge}</td>")
        rows.append(f"<td class='certificate-list'>{cert_info}</td>")
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
    """Build HTML footer."""
    return f"""
    <div style='margin-top: 50px; padding-top: 20px; border-top: 1px solid #cccccc; color: #666666; font-size: 9pt;'>
        <p>Genererad av Tobbes v2 - Spårbarhetsguiden</p>
        <p>Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """


# ==================== Summary Functions ====================


def get_report_summary(
    articles: List[Dict],
    certificates: List[Certificate],
) -> Dict[str, any]:
    """
    Get report generation summary statistics.

    Args:
        articles: List of article dicts
        certificates: List of certificates

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
    articles_with_certs = len(set(c.article_number for c in certificates))

    return {
        "article_count": len(articles),
        "articles_with_charge": articles_with_charge,
        "articles_without_charge": articles_without_charge,
        "certificate_count": len(certificates),
        "articles_with_certificates": articles_with_certs,
        "unique_certificate_types": len(set(c.certificate_type for c in certificates)),
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
