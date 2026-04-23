import re

from gmail_moneywiz_export.models import Transaction
from gmail_moneywiz_export.normalization import (
    normalize_amount,
    normalize_merchant,
    parse_scotia_date,
)
from gmail_moneywiz_export.parsers import ParseError, SkipMessage

SCOTIA_TRANSACTION_RE = re.compile(
    r"transacción realizada en\s+"
    r"(?P<merchant>.*?)\s*,\s*"
    r"el día\s+(?P<date>\d{2}/\d{2}/\d{4})\s+"
    r"a las\s+(?P<time>\d{2}:\d{2}\s*[AP]M)\s+"
    r"con su tarjeta de crédito(?:\s+(?:titular|adicional))?(?:\s+de DAVIbank)?\s+"
    r"(?P<card_type>VISA|MC)\s+terminada en\s+(?P<last4>\d{4})\s+"
    r"con número de autorización\s+(?P<auth>\d+)"
    r"(?:\s+y referencia\s+(?P<reference>\d+))?\s+"
    r"por\s+(?P<currency>CRC|USD)\s+(?P<amount>[\d,]+\.\d{2}),\s*"
    r"(?P<status>fue aprobada|fue rechazada|fue denegada)",
    re.IGNORECASE,
)
TRAILING_LOCATION_RE = re.compile(r"\s+(Costa Rica|Estados Unidos|USA)\s*$", re.IGNORECASE)


def parse_scotia(message_id: str, text: str) -> list[Transaction]:
    compact_text = " ".join(text.split())
    matches = list(SCOTIA_TRANSACTION_RE.finditer(compact_text))
    if not matches:
        if any(term in compact_text.lower() for term in ["rechazada", "denegada"]):
            raise SkipMessage("Scotiabank declined transaction")
        raise ParseError("Could not parse Scotiabank transaction")

    transactions: list[Transaction] = []
    for match in matches:
        status = match.group("status").lower()
        if status != "fue aprobada":
            raise SkipMessage(f"Scotiabank transaction not approved: {status}")

        merchant = TRAILING_LOCATION_RE.sub("", match.group("merchant")).strip(" ,")
        transactions.append(
            Transaction(
                bank="scotia",
                message_id=message_id,
                merchant=normalize_merchant(merchant),
                date=parse_scotia_date(match.group("date")),
                amount=normalize_amount(match.group("amount")),
                currency=match.group("currency").upper(),
                card_identifier=f"{match.group('card_type').upper()} {match.group('last4')}",
                auth=match.group("auth"),
                reference=match.group("reference"),
            )
        )

    return transactions
