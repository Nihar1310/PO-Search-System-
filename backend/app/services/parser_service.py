from __future__ import annotations

import io
import logging
import mimetypes
import os
from typing import Any, Dict, Optional, Tuple, List

from ..utils import extractors

logger = logging.getLogger(__name__)

# Feature flags
USE_DOCAI = os.getenv("USE_DOCAI", "false").lower() == "true"
USE_VISION = os.getenv("USE_VISION", "false").lower() == "true"

if USE_DOCAI:
    from . import docai_service

if USE_VISION:
    from . import vision_service


def parse_document(file_bytes: bytes, filename: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
    # Validate input
    if not _validate_file_input(file_bytes, filename):
        logger.warning(f"Invalid file input: {filename}")
        return _create_empty_result(filename)
    
    text = ''
    extraction_method = 'unknown'
    docai_payload: Optional[Dict[str, Any]] = None
    vision_payload: Optional[Dict[str, Any]] = None

    # Try Vision API first if enabled
    if USE_VISION:
        text, vision_payload = _extract_text_with_vision(file_bytes, filename, mime_type)
        if text:
            extraction_method = 'vision'

    # Fallback to Document AI if Vision fails
    if not text and USE_DOCAI:
        text, docai_payload = _extract_text_with_docai(file_bytes, filename, mime_type)
        if text:
            extraction_method = 'docai'

    # Final fallback to Tesseract OCR
    if not text:
        text, extraction_method = _extract_text_with_fallback(file_bytes, filename, mime_type)
    
    # Validate extracted text
    if not _validate_extracted_text(text, filename):
        logger.warning(f"Text extraction failed for: {filename}")
        return _create_empty_result(
            filename,
            extraction_method=extraction_method,
            docai_payload=docai_payload,
            vision_payload=vision_payload,
        )

    # Extract PO data
    po_number = extractors.extract_po_number(text)
    date_value = extractors.extract_date(text)
    client_name = extractors.extract_client_name(text)
    total_value = extractors.extract_total_value(text)
    payment_terms = extractors.extract_payment_terms(text)

    # Validate PO signals
    po_signals = _validate_po_signals(text, po_number, date_value, client_name)

    structured_from_docai = _structured_from_docai(docai_payload) if docai_payload else {}

    result = {
        "po_number": po_number,
        "date": date_value.isoformat() if date_value else None,
        "client": client_name,
        "items": structured_from_docai.get("items", []),
        "total_value": structured_from_docai.get("total_value", total_value),
        "terms": structured_from_docai.get("terms", payment_terms),
        "raw_text": _clean_excerpt(text),
        "source_filename": filename,
        "extraction_method": extraction_method,
        "po_signals": po_signals,
        "text_length": len(text),
    }

    if docai_payload:
        result["docai"] = {
            "entities": docai_payload.get("entities", []),
            "pages": docai_payload.get("pages"),
            "key_values": docai_payload.get("key_values", {}),
        }

    if vision_payload:
        result["vision"] = {
            "confidence": vision_payload.get("confidence", 0.0),
            "pages": vision_payload.get("pages", 1),
            "word_count": vision_payload.get("word_count", 0),
            "detections": vision_payload.get("detections", 0),
        }

    if structured_from_docai.get("client"):
        result["client"] = structured_from_docai["client"]
    if structured_from_docai.get("po_number"):
        result["po_number"] = structured_from_docai["po_number"]
    if structured_from_docai.get("terms") and not result.get("terms"):
        result["terms"] = structured_from_docai["terms"]

    return result


def _detect_mime_type(filename: str, declared: Optional[str]) -> str:
    if declared:
        return declared
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    return "application/pdf"


def _extract_text_with_docai(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    resolved_mime = _detect_mime_type(filename, mime_type)
    if resolved_mime not in docai_service.SUPPORTED_MIME_TYPES:
        logger.debug("Document AI unsupported mime type %s, falling back", resolved_mime)
        return "", None

    try:
        payload = docai_service.process_document(file_bytes, resolved_mime)
        text = payload.get("text", "")
        if text:
            logger.info("Extracted %s characters via Document AI", len(text))
        return text, payload
    except Exception as exc:  # pragma: no cover - external service
        logger.error("Document AI extraction failed: %s", exc)
        return "", None


def _extract_text_with_vision(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Extract text using Google Cloud Vision API."""
    try:
        detected_mime = _detect_mime_type(filename, mime_type)
        
        if detected_mime == "application/pdf":
            result = vision_service.process_pdf_pages(file_bytes)
        else:
            result = vision_service.process_document(file_bytes, detected_mime)
        
        text = result.get("text", "")
        if text:
            logger.info(f"Vision API extracted {len(text)} characters from {filename}")
            return text, result
        else:
            logger.warning(f"Vision API returned no text for {filename}")
            return "", None
            
    except Exception as exc:
        logger.error(f"Vision API extraction failed for {filename}: {exc}")
        return "", None


def _extract_text_with_fallback(file_bytes: bytes, filename: str, mime_type: Optional[str]) -> Tuple[str, str]:
    """
    Extract text with fallback logic: native extraction → OCR fallback
    Returns (text, extraction_method)
    """
    lower_name = filename.lower()
    
    # Try native text extraction first
    if mime_type and "pdf" in mime_type:
        text = _extract_text_from_pdf(file_bytes)
        if text and _is_text_quality_good(text):
            return text, "pdf_native"
    if lower_name.endswith(".pdf"):
        text = _extract_text_from_pdf(file_bytes)
        if text and _is_text_quality_good(text):
            return text, "pdf_native"
    if lower_name.endswith(".docx") or (mime_type and "word" in mime_type):
        text = _extract_text_from_docx(file_bytes)
        if text and _is_text_quality_good(text):
            return text, "docx_native"
    
    # Fallback to OCR for images or scanned PDFs
    logger.info(f"Native text extraction failed for {filename}, falling back to OCR")
    text = _extract_text_with_ocr(file_bytes)
    return text or "", "ocr_tesseract"


def _extract_text(file_bytes: bytes, filename: str, mime_type: Optional[str]) -> str:
    """Legacy function for backward compatibility"""
    text, _ = _extract_text_with_fallback(file_bytes, filename, mime_type)
    return text


def _extract_text_from_pdf(file_bytes: bytes) -> Optional[str]:
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if text:
            return text
    except Exception as exc:  # pragma: no cover - depends on optional libs
        logger.debug("pdfplumber extraction failed: %s", exc)

    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if text:
            return text
    except Exception as exc:  # pragma: no cover
        logger.debug("PyPDF2 extraction failed: %s", exc)

    return None


def _extract_text_from_docx(file_bytes: bytes) -> Optional[str]:
    try:
        import docx  # type: ignore

        document = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in document.paragraphs]
        text = "\n".join(paragraphs).strip()
        return text or None
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.debug("DOCX extraction failed: %s", exc)
        return None


def _extract_text_with_ocr(file_bytes: bytes) -> Optional[str]:
    """
    Extract text using OCR with enhanced PDF→image rasterization
    """
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        
        # Configure pytesseract to use the correct tesseract path
        import os
        tesseract_path = os.getenv('TESSERACT_CMD', '/opt/homebrew/bin/tesseract')
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Check if it's an image file first
        try:
            image = Image.open(io.BytesIO(file_bytes))
            # If we can open it as an image, process it directly
            text = pytesseract.image_to_string(image)
            if text.strip():
                logger.info(f"Direct OCR extracted {len(text)} characters from image")
                return text.strip()
        except Exception as exc:
            logger.debug(f"Not an image file or direct OCR failed: {exc}")

        # Configure pdf2image to use the correct poppler path
        poppler_path = os.getenv('POPPLER_PATH', '/opt/homebrew/bin')
        if os.path.exists(poppler_path):
            os.environ['PATH'] = poppler_path + ':' + os.environ.get('PATH', '')

        # Convert PDF to images with enhanced settings
        images = convert_from_bytes(
            file_bytes,
            dpi=300,  # Higher DPI for better OCR
            first_page=1,
            last_page=10,  # Limit to first 10 pages for performance
            fmt='png',
            thread_count=2
        )
        
        if not images:
            logger.warning("No images generated from PDF")
            return None

        text_chunks = []
        for i, image in enumerate(images):
            try:
                # Preprocess image for better OCR
                processed_image = _preprocess_image_for_ocr(image)
                
                # Extract text with Tesseract
                text = pytesseract.image_to_string(
                    processed_image,
                    config='--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:;()[]{}@#$%^&*+-=<>/\\|"\'`~_ \n\t'
                )
                
                if text.strip():
                    text_chunks.append(text.strip())
                    logger.debug(f"OCR extracted {len(text)} chars from page {i+1}")
                
            except Exception as exc:
                logger.warning(f"OCR failed on page {i+1}: {exc}")
                continue

        if text_chunks:
            final_text = "\n".join(text_chunks).strip()
            logger.info(f"OCR extracted {len(final_text)} total characters from {len(images)} pages")
            return final_text
        else:
            logger.warning("No text extracted from any page")
            return None
            
    except Exception as exc:  # pragma: no cover - heavy dependency
        logger.error(f"OCR extraction failed: {exc}")
        return None


def _preprocess_image_for_ocr(image) -> object:
    """
    Preprocess image to improve OCR accuracy
    """
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply denoising
        img_array = cv2.fastNlMeansDenoising(img_array)
        
        # Apply adaptive thresholding
        img_array = cv2.adaptiveThreshold(
            img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Convert back to PIL
        from PIL import Image
        return Image.fromarray(img_array)
        
    except ImportError:
        # If OpenCV not available, return original image
        logger.debug("OpenCV not available, skipping image preprocessing")
        return image
    except Exception as exc:
        logger.warning(f"Image preprocessing failed: {exc}")
        return image


def _validate_file_input(file_bytes: bytes, filename: str) -> bool:
    """
    Validate file input: check bytes, filename, and basic file properties
    """
    if not file_bytes:
        logger.warning("Empty file bytes")
        return False
    
    if len(file_bytes) < 100:  # Minimum file size
        logger.warning(f"File too small: {len(file_bytes)} bytes")
        return False
    
    if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
        logger.warning(f"File too large: {len(file_bytes)} bytes")
        return False
    
    if not filename or len(filename.strip()) == 0:
        logger.warning("Empty filename")
        return False
    
    # Check for valid file extensions
    valid_extensions = {'.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    file_ext = '.' + filename.lower().split('.')[-1] if '.' in filename else ''
    if file_ext not in valid_extensions:
        logger.warning(f"Unsupported file extension: {file_ext}")
        return False
    
    return True


def _validate_extracted_text(text: str, filename: str) -> bool:
    """
    Validate extracted text quality
    """
    if not text or not text.strip():
        logger.warning(f"No text extracted from {filename}")
        return False
    
    # Check minimum text length
    if len(text.strip()) < 10:
        logger.warning(f"Text too short: {len(text)} chars")
        return False
    
    # Check for reasonable character distribution
    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text)
    
    if total_chars > 0 and alpha_chars / total_chars < 0.1:
        logger.warning(f"Too few alphabetic characters: {alpha_chars}/{total_chars}")
        return False
    
    return True


def _is_text_quality_good(text: str) -> bool:
    """
    Check if extracted text quality is good enough to skip OCR
    """
    if not text or len(text.strip()) < 50:
        return False
    
    # Check for common OCR artifacts
    ocr_artifacts = ['�', '□', '■', '▢', '▣', '▤', '▥', '▦', '▧', '▨', '▩']
    artifact_count = sum(text.count(artifact) for artifact in ocr_artifacts)
    
    if artifact_count > len(text) * 0.05:  # More than 5% artifacts
        return False
    
    # Check for reasonable word spacing
    words = text.split()
    if len(words) < 5:
        return False
    
    # Check for reasonable line structure
    lines = text.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    if len(non_empty_lines) < 2:
        return False
    
    return True


def _validate_po_signals(text: str, po_number: Optional[str], date_value: Optional[Any], client_name: Optional[str]) -> Dict[str, Any]:
    """
    Validate PO-specific signals in the extracted text
    """
    signals = {
        "has_po_number": po_number is not None,
        "has_date": date_value is not None,
        "has_client": client_name is not None,
        "text_length": len(text),
        "po_keywords_found": [],
        "confidence_score": 0.0
    }
    
    # Check for PO-related keywords
    po_keywords = [
        'purchase order', 'po number', 'po#', 'p.o.', 'order number',
        'invoice', 'bill to', 'ship to', 'vendor', 'supplier',
        'quantity', 'unit price', 'total', 'subtotal', 'tax',
        'payment terms', 'delivery date', 'due date'
    ]
    
    text_lower = text.lower()
    found_keywords = [kw for kw in po_keywords if kw in text_lower]
    signals["po_keywords_found"] = found_keywords
    
    # Calculate confidence score
    score = 0.0
    if signals["has_po_number"]:
        score += 0.4
    if signals["has_date"]:
        score += 0.2
    if signals["has_client"]:
        score += 0.2
    if len(found_keywords) >= 3:
        score += 0.2
    elif len(found_keywords) >= 1:
        score += 0.1
    
    signals["confidence_score"] = min(score, 1.0)
    
    return signals


def _create_empty_result(
    filename: str,
    extraction_method: str = "none",
    docai_payload: Optional[Dict[str, Any]] = None,
    vision_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create empty result structure for failed parsing
    """
    result = {
        "po_number": None,
        "date": None,
        "client": None,
        "items": [],
        "total_value": None,
        "terms": None,
        "raw_text": "",
        "source_filename": filename,
        "extraction_method": extraction_method,
        "po_signals": {
            "has_po_number": False,
            "has_date": False,
            "has_client": False,
            "text_length": 0,
            "po_keywords_found": [],
            "confidence_score": 0.0
        },
        "text_length": 0,
    }

    if docai_payload:
        result["docai"] = {
            "entities": docai_payload.get("entities", []),
            "pages": docai_payload.get("pages"),
        }

    if vision_payload:
        result["vision"] = {
            "confidence": vision_payload.get("confidence", 0.0),
            "pages": vision_payload.get("pages", 1),
            "word_count": vision_payload.get("word_count", 0),
            "detections": vision_payload.get("detections", 0),
        }

    return result


def _structured_from_docai(docai_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not docai_payload:
        return {}

    key_values = docai_payload.get("key_values") or {}
    items = _items_from_tables(docai_payload.get("tables") or [])

    def find_value(*candidates: str) -> Optional[str]:
        for candidate in candidates:
            for key, value in key_values.items():
                if candidate in key:
                    return value.strip()
        return None

    client = find_value(
        "bill to",
        "buyer",
        "client",
        "consignee",
        "customer",
        "buyer name",
    )
    po_number = find_value("po no", "po number", "purchase order", "order number")
    payment_terms = find_value("payment terms", "terms")
    total_value = None

    total_raw = find_value("total", "grand total", "total amount", "total value")
    if total_raw:
        try:
            total_value = float(total_raw.replace(",", "").split()[0])
        except ValueError:
            total_value = None

    return {
        "client": client,
        "po_number": po_number,
        "terms": payment_terms,
        "total_value": total_value,
        "items": items,
    }


def _items_from_tables(tables: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not tables:
        return []

    normalized_rows: List[Dict[str, Any]] = []
    for table in tables:
        header = [h.lower() for h in table.get("header", []) or []]
        if not header:
            continue

        column_map = {}
        for idx, name in enumerate(header):
            if 'description' in name or 'item' in name:
                column_map['description'] = idx
            elif 'qty' in name or 'quantity' in name:
                column_map['quantity'] = idx
            elif 'unit price' in name or 'rate' in name:
                column_map['unit_price'] = idx
            elif 'amount' in name or 'total' in name:
                column_map['total'] = idx

        if 'description' not in column_map:
            continue

        for row in table.get("rows", []) or []:
            item = {}
            desc_idx = column_map['description']
            if desc_idx < len(row):
                item['description'] = row[desc_idx].strip()

            qty_idx = column_map.get('quantity')
            if qty_idx is not None and qty_idx < len(row):
                try:
                    item['quantity'] = float(row[qty_idx].replace(',', ''))
                except (ValueError, AttributeError):
                    item['quantity'] = row[qty_idx]

            unit_idx = column_map.get('unit_price')
            if unit_idx is not None and unit_idx < len(row):
                try:
                    item['unit_price'] = float(row[unit_idx].replace(',', ''))
                except (ValueError, AttributeError):
                    item['unit_price'] = row[unit_idx]

            total_idx = column_map.get('total')
            if total_idx is not None and total_idx < len(row):
                try:
                    item['total'] = float(row[total_idx].replace(',', ''))
                except (ValueError, AttributeError):
                    item['total'] = row[total_idx]

            if item.get('description'):
                normalized_rows.append(item)

    return normalized_rows


def _clean_excerpt(text: str, limit: int = 1200) -> str:
    if not text:
        return ""
    collapsed = " ".join(text.split())
    return collapsed[:limit]
