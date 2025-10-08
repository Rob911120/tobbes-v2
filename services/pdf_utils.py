"""
PDF Utilities for Certificate Stamping.

Handles PDF metadata stamping for traceability.
Based on v1's pdf_utils.py implementation.
"""

import io
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PDFStampMarkers:
    """
    Konstanter för PDF-metadata markörer.

    Används för att ID-märka certifikat med:
    ##ART:{article}##TYP:{type}##SID:{page}/{total}##
    """
    ART_PREFIX: str = "##ART:"
    TYP_PREFIX: str = "##TYP:"
    SID_PREFIX: str = "##SID:"
    END_MARKER: str = "##"


def create_text_overlay(
    page_width: float,
    page_height: float,
    text_id: str
) -> PdfReader:
    """
    Skapa transparent overlay med horisontell text längst ner till vänster.

    Args:
        page_width: Sidans bredd i punkter
        page_height: Sidans höjd i punkter
        text_id: Text att lägga till (inkl. markörer)

    Returns:
        PdfReader med overlay-sida

    Raises:
        ImportError: Om pypdf eller reportlab inte är installerad
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError(
            "pypdf och reportlab krävs för PDF-märkning. "
            "Installera med: pip install pypdf reportlab"
        )

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Position: Längst ner till vänster, horisontell text
    x_pos = 10  # 10 punkter från vänster kant
    y_pos = 10  # 10 punkter från botten

    # Styling - mycket diskret (ljusgrå, liten font)
    can.setFont("Helvetica", 6)  # Mycket liten font
    can.setFillColorRGB(0.7, 0.7, 0.7)  # Ljusgrå

    # Rita text horisontellt
    can.drawString(x_pos, y_pos, text_id)

    can.save()

    # Konvertera till PyPDF-läsare
    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    return overlay_pdf


def stamp_pdf_with_metadata(
    pdf_path: Path,
    article_id: str,
    doc_type: str,
    markers: Optional[PDFStampMarkers] = None
) -> bool:
    """
    Stämpla en PDF-fil med metadata längst ner till vänster på alla sidor.

    Format: ##ART:{article_id}##TYP:{doc_type}##SID:{page}/{total}##

    Args:
        pdf_path: Sökväg till PDF att stämpla
        article_id: Artikel-ID (t.ex. artikelnummer)
        doc_type: Typ av dokument (t.ex. "Materialintyg", "Svetslogg")
        markers: PDFStampMarkers instance (använder default om None)

    Returns:
        True om lyckad stämpling, False annars

    Raises:
        ImportError: Om pypdf eller reportlab inte är installerad
        FileNotFoundError: Om PDF-fil inte finns
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError(
            "pypdf och reportlab krävs för PDF-märkning. "
            "Installera med: pip install pypdf reportlab"
        )

    if markers is None:
        markers = PDFStampMarkers()

    try:
        # Validera input
        if not pdf_path.exists():
            logger.error(f"PDF-fil finns inte: {pdf_path}")
            raise FileNotFoundError(f"PDF-fil finns inte: {pdf_path}")

        # Läs original PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        total_pages = len(reader.pages)

        logger.debug(f"Stämplar {total_pages} sidor i {pdf_path.name}")

        for page_num, page in enumerate(reader.pages, 1):
            # Format: ##ART:12345##TYP:Materialintyg##SID:1/5##
            text_id = (
                f"{markers.ART_PREFIX}{article_id}"
                f"{markers.TYP_PREFIX}{doc_type}"
                f"{markers.SID_PREFIX}{page_num}/{total_pages}{markers.END_MARKER}"
            )

            # Hämta sidans dimensioner
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # Skapa overlay med horisontell text
            overlay_pdf = create_text_overlay(
                page_width=page_width,
                page_height=page_height,
                text_id=text_id
            )

            # Slå ihop original-sida med overlay
            page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

            logger.debug(f"Stämplat sida {page_num}/{total_pages} med {article_id}")

        # Skriv över original med stämplad version
        with open(pdf_path, 'wb') as output:
            writer.write(output)

        logger.info(f"Alla {total_pages} sidor stämplade i {pdf_path.name}")
        return True

    except FileNotFoundError:
        raise
    except PermissionError:
        logger.error(f"Åtkomst nekad till PDF: {pdf_path}")
        return False
    except Exception as e:
        logger.error(f"Fel vid stämpling av PDF {pdf_path}: {e}", exc_info=True)
        return False


def count_pdf_pages(pdf_path: Path) -> int:
    """
    Räkna antal sidor i en PDF-fil.

    Args:
        pdf_path: Sökväg till PDF-fil

    Returns:
        Antal sidor, 0 om fel uppstår

    Raises:
        ImportError: Om pypdf inte är installerad
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError("pypdf krävs. Installera med: pip install pypdf")

    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)
        logger.debug(f"PDF {pdf_path.name} har {page_count} sidor")
        return page_count
    except Exception as e:
        logger.warning(f"Kunde inte räkna sidor i {pdf_path}: {e}")
        return 0


def create_page_number_overlay(
    page_width: float,
    page_height: float,
    page_num: int,
    total_pages: int
) -> PdfReader:
    """
    Skapa overlay med sidnummer längst ner till höger.

    Args:
        page_width: Sidans bredd i punkter
        page_height: Sidans höjd i punkter
        page_num: Aktuellt sidnummer
        total_pages: Totalt antal sidor

    Returns:
        PdfReader med sidnummer-overlay

    Raises:
        ImportError: Om pypdf eller reportlab inte är installerad
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError(
            "pypdf och reportlab krävs för sidnumrering. "
            "Installera med: pip install pypdf reportlab"
        )

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Position: Längst ner till höger
    page_text = f"Page {page_num}/{total_pages}"

    # Beräkna textbredd för att positionera från höger
    text_width = can.stringWidth(page_text, "Helvetica", 6)
    x_pos = page_width - text_width - 10  # 10 punkter från höger kant
    y_pos = 10  # 10 punkter från botten

    # Styling - samma som metadata (ljusgrå, liten font)
    can.setFont("Helvetica", 6)
    can.setFillColorRGB(0.7, 0.7, 0.7)  # Ljusgrå

    # Rita text
    can.drawString(x_pos, y_pos, page_text)

    can.save()

    # Konvertera till PyPDF-läsare
    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    return overlay_pdf


def add_page_numbers_to_pdf(pdf_path: Path, skip_first_page: bool = True) -> bool:
    """
    Lägg till sidnummer på alla sidor i en PDF.

    Lägger till "Page X/Y" längst ner till höger på varje sida.

    VIKTIGT: Skippar första sidan (TOC) om skip_first_page=True.

    Args:
        pdf_path: Sökväg till PDF att numrera (modifieras in-place)
        skip_first_page: Om True, skippa första sidan (TOC) - default True

    Returns:
        True om lyckad numrering, False annars

    Raises:
        ImportError: Om pypdf eller reportlab inte är installerad
        FileNotFoundError: Om PDF-fil inte finns
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError(
            "pypdf och reportlab krävs för sidnumrering. "
            "Installera med: pip install pypdf reportlab"
        )

    try:
        if not pdf_path.exists():
            logger.error(f"PDF-fil finns inte: {pdf_path}")
            raise FileNotFoundError(f"PDF-fil finns inte: {pdf_path}")

        # Läs original PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        total_pages = len(reader.pages)

        logger.debug(f"Lägger till sidnummer på {total_pages} sidor i {pdf_path.name} (skip_first={skip_first_page})")

        for page_num, page in enumerate(reader.pages, 1):
            # Skip first page (TOC) if requested
            if skip_first_page and page_num == 1:
                # Add page without page number
                writer.add_page(page)
                logger.debug(f"Skippade sidnummer på sida 1 (TOC)")
                continue

            # Hämta sidans dimensioner
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # Skapa sidnummer overlay
            page_number_overlay = create_page_number_overlay(
                page_width=page_width,
                page_height=page_height,
                page_num=page_num,
                total_pages=total_pages
            )

            # Slå ihop original-sida med overlay
            page.merge_page(page_number_overlay.pages[0])
            writer.add_page(page)

            logger.debug(f"Lagt till sidnummer på sida {page_num}/{total_pages}")

        # Skriv över original med numrerad version
        with open(pdf_path, 'wb') as output:
            writer.write(output)

        skipped_msg = " (TOC skippades)" if skip_first_page else ""
        logger.info(f"Sidnummer tillagda på {total_pages} sidor i {pdf_path.name}{skipped_msg}")
        return True

    except FileNotFoundError:
        raise
    except PermissionError:
        logger.error(f"Åtkomst nekad till PDF: {pdf_path}")
        return False
    except Exception as e:
        logger.error(f"Fel vid sidnumrering av PDF {pdf_path}: {e}", exc_info=True)
        return False


def extract_metadata_stamps(pdf_path: Path, markers: Optional[PDFStampMarkers] = None) -> list:
    """
    Extrahera metadata-stämplar från en PDF.

    Läser text från PDF och letar efter metadata-markörer i formatet:
    ##ART:{article}##TYP:{doc_type}##SID:{page}/{total}##

    Args:
        pdf_path: Sökväg till PDF att extrahera från
        markers: PDFStampMarkers instance (använder default om None)

    Returns:
        List med dicts: [{'article_id': str, 'doc_type': str, 'pdf_page': int}, ...]

    Raises:
        ImportError: Om pypdf inte är installerad
        FileNotFoundError: Om PDF-fil inte finns
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError("pypdf krävs. Installera med: pip install pypdf")

    if markers is None:
        markers = PDFStampMarkers()

    stamps = []

    try:
        if not pdf_path.exists():
            logger.error(f"PDF-fil finns inte: {pdf_path}")
            raise FileNotFoundError(f"PDF-fil finns inte: {pdf_path}")

        reader = PdfReader(str(pdf_path))
        total_pages = len(reader.pages)

        logger.debug(f"Extraherar metadata från {total_pages} sidor i {pdf_path.name}")

        for pdf_page, page in enumerate(reader.pages, 1):
            # Extrahera text från sidan
            text = page.extract_text()

            # Sök efter metadata-mönster: ##ART:...##TYP:...##SID:...##
            if markers.ART_PREFIX in text:
                try:
                    # Extrahera artikel-ID
                    art_start = text.find(markers.ART_PREFIX) + len(markers.ART_PREFIX)
                    art_end = text.find(markers.TYP_PREFIX, art_start)
                    article_id = text[art_start:art_end] if art_end > art_start else ""

                    # Extrahera doc_type
                    typ_start = text.find(markers.TYP_PREFIX) + len(markers.TYP_PREFIX)
                    typ_end = text.find(markers.SID_PREFIX, typ_start)
                    doc_type = text[typ_start:typ_end] if typ_end > typ_start else ""

                    # Spara metadata
                    if article_id and doc_type:
                        stamp = {
                            'article_id': article_id,
                            'doc_type': doc_type,
                            'pdf_page': pdf_page
                        }
                        stamps.append(stamp)
                        logger.debug(f"Sida {pdf_page}: {doc_type} - {article_id}")

                except Exception as e:
                    logger.warning(f"Kunde inte parsa metadata på sida {pdf_page}: {e}")

        logger.info(f"Extraherade {len(stamps)} metadata-stämplar från {pdf_path.name}")
        return stamps

    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Fel vid extraktion av metadata från {pdf_path}: {e}", exc_info=True)
        return []


def validate_pdf(pdf_path: Path) -> bool:
    """
    Validera att en fil är en giltig PDF.

    Args:
        pdf_path: Sökväg till fil

    Returns:
        True om giltig PDF, False annars

    Raises:
        ImportError: Om pypdf inte är installerad
    """
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError("pypdf krävs. Installera med: pip install pypdf")

    try:
        if not pdf_path.exists():
            logger.warning(f"Fil finns inte: {pdf_path}")
            return False

        if pdf_path.suffix.lower() != '.pdf':
            logger.warning(f"Fil är inte en PDF: {pdf_path}")
            return False

        # Försök öppna som PDF
        PdfReader(str(pdf_path))
        return True

    except Exception as e:
        logger.warning(f"Ogiltig PDF {pdf_path}: {e}")
        return False
