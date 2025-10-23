from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import Dict, List, Optional

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUPPORTED_MIME_TYPES = {
    "image/tiff",
    "image/gif", 
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
}

def _ensure_dependency():
    try:
        from google.cloud import vision  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-vision is required when USE_VISION=true. Install it via"
            " 'pip install google-cloud-vision'"
        ) from exc

@lru_cache(maxsize=1)
def _get_client():
    _ensure_dependency()
    from google.cloud import vision
    
    return vision.ImageAnnotatorClient()

def process_document(file_bytes: bytes, mime_type: str) -> Dict[str, object]:
    """Process a document with Google Cloud Vision API and return text."""
    
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(f"Unsupported mime type for Vision API: {mime_type}")
    
    from google.cloud import vision
    
    client = _get_client()
    
    # Create image object
    image = vision.Image(content=file_bytes)
    
    # Perform text detection
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    if not texts:
        return {
            "text": "",
            "mime_type": mime_type,
            "pages": 1,
            "confidence": 0.0,
            "word_count": 0,
        }
    
    # Get full text (first annotation contains all text)
    full_text = texts[0].description if texts else ""
    
    # Calculate confidence from individual detections
    confidences = []
    word_count = 0
    
    for text in texts[1:]:  # Skip first (full text)
        if hasattr(text, 'confidence') and text.confidence:
            confidences.append(text.confidence)
        word_count += len(text.description.split())
    
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    return {
        "text": full_text,
        "mime_type": mime_type,
        "pages": 1,  # Vision API processes single images
        "confidence": avg_confidence,
        "word_count": word_count,
        "detections": len(texts) - 1,  # Number of individual text blocks
    }

def process_pdf_pages(file_bytes: bytes) -> Dict[str, object]:
    """Process PDF by converting to images and using Vision API."""
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image
        
        # Convert PDF to images
        images = convert_from_bytes(
            file_bytes,
            dpi=300,
            first_page=1,
            last_page=10,  # Limit for performance
            fmt='png',
            thread_count=2
        )
        
        if not images:
            return {
                "text": "",
                "mime_type": "application/pdf",
                "pages": 0,
                "confidence": 0.0,
                "word_count": 0,
            }
        
        client = _get_client()
        all_texts = []
        total_confidence = 0.0
        total_words = 0
        total_detections = 0
        
        for i, image in enumerate(images):
            try:
                # Convert PIL image to bytes
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
                
                # Process with Vision API
                from google.cloud import vision
                image_obj = vision.Image(content=img_bytes)
                response = client.text_detection(image=image_obj)
                texts = response.text_annotations
                
                if texts:
                    page_text = texts[0].description
                    all_texts.append(page_text)
                    
                    # Calculate metrics
                    page_confidences = []
                    for text in texts[1:]:
                        if hasattr(text, 'confidence') and text.confidence:
                            page_confidences.append(text.confidence)
                    
                    if page_confidences:
                        total_confidence += sum(page_confidences) / len(page_confidences)
                    
                    total_words += len(page_text.split())
                    total_detections += len(texts) - 1
                    
                    logger.debug(f"Vision API extracted {len(page_text)} chars from page {i+1}")
                
            except Exception as exc:
                logger.warning(f"Vision API failed on page {i+1}: {exc}")
                continue
        
        if all_texts:
            full_text = "\n".join(all_texts)
            avg_confidence = total_confidence / len(images) if images else 0.0
            
            return {
                "text": full_text,
                "mime_type": "application/pdf",
                "pages": len(images),
                "confidence": avg_confidence,
                "word_count": total_words,
                "detections": total_detections,
            }
        else:
            return {
                "text": "",
                "mime_type": "application/pdf", 
                "pages": len(images),
                "confidence": 0.0,
                "word_count": 0,
            }
            
    except Exception as exc:
        logger.error(f"PDF processing with Vision API failed: {exc}")
        return {
            "text": "",
            "mime_type": "application/pdf",
            "pages": 0,
            "confidence": 0.0,
            "word_count": 0,
        }
