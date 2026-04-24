import re

from gmail_moneywiz_export.models import GmailMessage, Transaction
from gmail_moneywiz_export.plugins import QueryHints
from gmail_moneywiz_export.normalization import (
    normalize_amount,
    normalize_currency,
    normalize_merchant,
    normalized_lines,
    parse_bac_date,
)
from gmail_moneywiz_export.parsers import ParseError, SkipMessage

CARD_NUMBER_RE = re.compile(r"^\*{4,}\d{4}$")
CARD_TYPE_RE = re.compile(r"^(AMEX|VISA|MASTERCARD|MC)$", re.IGNORECASE)


class BacPlugin:
    id = "bac"
    display_name = "BAC"
    priority = 100

    def query_hints(self) -> QueryHints:
        return QueryHints(labels=("banks-bac",))

    def match_score(self, message: GmailMessage) -> int:
        text = message.text
        if (
            "Comercio:" in text
            and "Monto:" in text
            and (
                "A continuación le detallamos la transacción realizada" in text
                or "Tipo de Transacción:" in text
            )
        ):
            return 100
        return 0

    def parse(self, message: GmailMessage) -> list[Transaction]:
        return parse_bac(message.message_id, message.text)


def parse_bac(message_id: str, text: str) -> list[Transaction]:
    lines = normalized_lines(text)

    transaction_type = _find_value(lines, "Tipo de Transacción:")
    if transaction_type and transaction_type.upper() != "COMPRA":
        raise SkipMessage(f"BAC non-purchase transaction: {transaction_type}")

    merchant = _require_value(lines, "Comercio:")
    date_raw = _require_value(lines, "Fecha:")
    amount_raw = _require_value(lines, "Monto:")
    card_identifier = _find_card_identifier(lines)
    auth = _find_value(lines, "Autorización:") or _find_value(
        lines, "Número de Autorización:"
    )
    reference = _find_value(lines, "Referencia:") or _find_value(
        lines, "Número de Referencia:"
    )

    currency = normalize_currency(amount_raw)
    amount = normalize_amount(amount_raw)

    return [
        Transaction(
            bank="bac",
            message_id=message_id,
            merchant=normalize_merchant(merchant),
            date=parse_bac_date(date_raw),
            amount=amount,
            currency=currency,
            card_identifier=card_identifier,
            auth=auth,
            reference=reference,
        )
    ]


def _find_card_identifier(lines: list[str]) -> str:
    for index, line in enumerate(lines):
        if not CARD_NUMBER_RE.match(line):
            continue
        previous = _previous_non_empty(lines, index)
        if previous and CARD_TYPE_RE.match(previous):
            return f"{previous.upper()} {line}"
    raise ParseError("Could not find BAC card identifier")


def _previous_non_empty(lines: list[str], start_index: int) -> str | None:
    for index in range(start_index - 1, -1, -1):
        if lines[index]:
            return lines[index]
    return None


def _find_value(lines: list[str], label: str) -> str | None:
    for index, line in enumerate(lines):
        if line == label:
            for next_line in lines[index + 1 :]:
                if next_line:
                    return next_line
            return None
        if line.startswith(label):
            value = line[len(label) :].strip()
            return value or None
    return None


def _require_value(lines: list[str], label: str) -> str:
    value = _find_value(lines, label)
    if value is None:
        raise ParseError(f"Missing BAC field: {label}")
    return value
