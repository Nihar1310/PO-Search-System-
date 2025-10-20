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

    key_values: Dict[str, str] = {}
    tables: List[Dict[str, object]] = []

    for page in getattr(document, "pages", []) or []:
        for form_field in getattr(page, "form_fields", []) or []:
            name = _layout_to_text(document, form_field.field_name)
            value = _layout_to_text(document, form_field.field_value)
            if name and value:
                key_values.setdefault(name.lower(), value)

        for table in getattr(page, "tables", []) or []:
            header_rows = getattr(table, "header_rows", []) or []
            header = []
            if header_rows:
                first_header = header_rows[0]
                header = [_layout_to_text(document, cell.layout) for cell in first_header.cells]

            rows_data = []
            for row in getattr(table, "body_rows", []) or []:
                row_values = [_layout_to_text(document, cell.layout) for cell in row.cells]
                rows_data.append(row_values)

            if header or rows_data:
                tables.append({"header": header, "rows": rows_data})

    return {
        "text": text,
        "entities": entities,
        "mime_type": mime_type,
        "pages": len(getattr(document, "pages", []) or []),
        "key_values": key_values,
        "tables": tables,
    }


def _layout_to_text(document, layout) -> str:
    if not layout:
        return ""
    text_anchor = getattr(layout, "text_anchor", None)
    if not text_anchor:
        return ""
    segments = getattr(text_anchor, "text_segments", []) or []
    text = []
    for segment in segments:
        start_index = int(getattr(segment, "start_index", 0))
        end_index = int(getattr(segment, "end_index", 0))
        text.append(document.text[start_index:end_index])
    return "".join(text).strip()
