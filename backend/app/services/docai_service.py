from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, List, Optional

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/tiff",
    "image/gif",
    "image/jpeg",
    "image/png",
}


def _ensure_dependency():
    try:
        from google.cloud import documentai  # noqa: F401
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "google-cloud-documentai is required when USE_DOCAI=true. Install it via"
            " 'pip install google-cloud-documentai'"
        ) from exc


@lru_cache(maxsize=1)
def _get_client():
    _ensure_dependency()
    from google.cloud import documentai

    client_options = None
    if settings.DOCAI_API_ENDPOINT:
        client_options = {"api_endpoint": settings.DOCAI_API_ENDPOINT}

    return documentai.DocumentProcessorServiceClient(client_options=client_options)


def _processor_resource_name(client) -> str:
    if settings.DOCAI_PROCESSOR_VERSION:
        return client.processor_version_path(
            settings.DOCAI_PROJECT_ID,
            settings.DOCAI_LOCATION,
            settings.DOCAI_PROCESSOR_ID,
            settings.DOCAI_PROCESSOR_VERSION,
        )
    return client.processor_path(
        settings.DOCAI_PROJECT_ID,
        settings.DOCAI_LOCATION,
        settings.DOCAI_PROCESSOR_ID,
    )


def process_document(file_bytes: bytes, mime_type: str) -> Dict[str, object]:
    """Process a document with Google Document AI and return text + entity hints."""

    if not settings.DOCAI_PROJECT_ID or not settings.DOCAI_PROCESSOR_ID:
        raise RuntimeError("Document AI settings are missing. Configure DOCAI_* env vars.")

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(f"Unsupported mime type for Document AI: {mime_type}")

    from google.cloud import documentai

    client = _get_client()
    name = _processor_resource_name(client)

    raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)

    document = result.document
    text = document.text or ""

    entities: List[Dict[str, object]] = []
    for entity in getattr(document, "entities", []) or []:
        normalized_value: Optional[str] = None
        if getattr(entity, "normalized_value", None) and entity.normalized_value.text:
            normalized_value = entity.normalized_value.text
        entities.append(
            {
                "type": entity.type_,
                "mentionText": entity.mention_text,
                "confidence": entity.confidence,
                "normalizedValue": normalized_value,
            }
        )

    return {
        "text": text,
        "entities": entities,
        "mime_type": mime_type,
        "pages": len(getattr(document, "pages", []) or []),
    }

