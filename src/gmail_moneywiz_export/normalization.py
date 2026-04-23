from datetime import datetime
from decimal import Decimal, InvalidOperation
import html
import re

ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\ufeff]")
WHITESPACE_RE = re.compile(r"\s+")
AMOUNT_RE = re.compile(r"([\d,]+\.\d{2})")
CURRENCY_RE = re.compile(r"\b(CRC|USD)\b", re.IGNORECASE)
SPANISH_MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


class NormalizationError(ValueError):
    pass


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = ZERO_WIDTH_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def normalized_lines(text: str) -> list[str]:
    return [collapse_spaces(line) for line in clean_text(text).splitlines() if collapse_spaces(line)]


def collapse_spaces(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_merchant(value: str) -> str:
    return collapse_spaces(value)


def normalize_currency(value: str) -> str:
    match = CURRENCY_RE.search(value)
    if not match:
        raise NormalizationError(f"Unsupported currency in: {value}")
    return match.group(1).upper()


def normalize_amount(value: str) -> str:
    match = AMOUNT_RE.search(value)
    if not match:
        raise NormalizationError(f"Could not parse amount from: {value}")
    normalized = match.group(1).replace(",", "")
    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation as error:
        raise NormalizationError(f"Invalid amount: {value}") from error
    return f"{decimal_value:.2f}"


def parse_bac_date(value: str) -> str:
    value = collapse_spaces(value)
    formats = [
        "%b %d, %Y, %H:%M",
        "%b %d, %Y, %I:%M",
        "%b %d, %Y, %I:%M %p",
    ]
    return _parse_with_formats(value, formats)


def parse_scotia_date(value: str) -> str:
    try:
        parsed = datetime.strptime(collapse_spaces(value), "%d/%m/%Y")
    except ValueError as error:
        raise NormalizationError(f"Invalid Scotia date: {value}") from error
    return parsed.strftime("%m/%d/%Y")


def parse_promerica_date(value: str) -> str:
    match = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", collapse_spaces(value), re.IGNORECASE)
    if not match:
        raise NormalizationError(f"Invalid Promerica date: {value}")
    day = int(match.group(1))
    month = SPANISH_MONTHS.get(match.group(2).lower())
    year = int(match.group(3))
    if month is None:
        raise NormalizationError(f"Unsupported Promerica month: {value}")
    return datetime(year, month, day).strftime("%m/%d/%Y")


def _parse_with_formats(value: str, formats: list[str]) -> str:
    for date_format in formats:
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.strftime("%m/%d/%Y")
        except ValueError:
            continue
    raise NormalizationError(f"Invalid date: {value}")
