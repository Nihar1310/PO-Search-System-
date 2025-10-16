import re
from datetime import date
from typing import Optional

from dateutil import parser as date_parser

# Basic patterns to expand later
PO_NUMBER_REGEX = re.compile(r"(?:PO|P\.O\.|Purchase Order)[:\s#]*([A-Z0-9-]+)", re.IGNORECASE)
PAYMENT_TERMS_REGEX = re.compile(r"(NET\s*\d{1,3}|Payment\s*Terms\s*:\s*[^\n]+)", re.IGNORECASE)
CLIENT_REGEX = re.compile(r"(?:Client|Buyer|Vendor|Bill To|Sold To)[:\s]+([A-Za-z0-9 &.,\-]{2,})", re.IGNORECASE)
TOTAL_REGEX = re.compile(r"(?:Grand\s+Total|Total\s+Amount|Total\s+Due|Total)\D*(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
DATE_CANDIDATE_REGEX = re.compile(
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})"
)


def extract_po_number(text: str) -> Optional[str]:
    m = PO_NUMBER_REGEX.search(text or "")
    return m.group(1).strip() if m else None


def extract_payment_terms(text: str) -> Optional[str]:
    m = PAYMENT_TERMS_REGEX.search(text or "")
    return m.group(1).strip() if m else None


def extract_client_name(text: str) -> Optional[str]:
    m = CLIENT_REGEX.search(text or "")
    return m.group(1).strip() if m else None


def extract_total_value(text: str) -> Optional[float]:
    for match in TOTAL_REGEX.findall(text or ""):
        candidate = match.replace(",", "")
        try:
            return float(candidate)
        except ValueError:
            continue
    return None


def extract_date(text: str) -> Optional[date]:
    for match in DATE_CANDIDATE_REGEX.findall(text or ""):
        try:
            parsed = date_parser.parse(match, fuzzy=True).date()
            return parsed
        except (ValueError, OverflowError):
            continue
    return None

