import re

from gmail_moneywiz_export.models import Transaction
from gmail_moneywiz_export.normalization import (
    normalize_amount,
    normalize_currency,
    normalize_merchant,
    normalized_lines,
    parse_promerica_date,
)
from gmail_moneywiz_export.parsers import ParseError

CARD_RE = re.compile(r"\*{4}-\*{4}-\*{4}-(\d{4})")


def parse_promerica(message_id: str, text: str) -> list[Transaction]:
    lines = normalized_lines(text)

    merchant = _require_value(lines, "Comercio")
    date_raw = _require_value(lines, "Fecha/hora")
    card_number = _require_value(lines, "Número de tarjeta")
    amount_raw = _require_value(lines, "Monto")
    auth = _find_value(lines, "Número de autorización")
    reference = _find_value(lines, "Número de referencia")

    card_match = CARD_RE.search(card_number)
    if not card_match:
        raise ParseError("Promerica — needs manual review or parsing template (card)")

    currency = normalize_currency(amount_raw)
    amount = normalize_amount(amount_raw)

    return [
        Transaction(
            bank="promerica",
            message_id=message_id,
            merchant=normalize_merchant(merchant),
            date=parse_promerica_date(date_raw),
            amount=amount,
            currency=currency,
            card_identifier=card_match.group(1),
            auth=auth,
            reference=reference,
        )
    ]


def _find_value(lines: list[str], label: str) -> str | None:
    for index, line in enumerate(lines):
        if line == label or line == f"{label}:":
            for next_line in lines[index + 1 :]:
                if next_line:
                    return next_line
            return None
        if line.startswith(f"{label} "):
            return line[len(label) :].strip()
        if line.startswith(f"{label}:"):
            return line[len(label) + 1 :].strip()
    return None


def _require_value(lines: list[str], label: str) -> str:
    value = _find_value(lines, label)
    if value is None:
        raise ParseError(f"Promerica — needs manual review or parsing template ({label})")
    return value
