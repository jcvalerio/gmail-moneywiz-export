from __future__ import annotations

import re
from datetime import datetime

from gmail_moneywiz_export.models import GmailMessage, Transaction
from gmail_moneywiz_export.normalization import normalize_amount, normalize_merchant
from gmail_moneywiz_export.parsers import ParseError
from gmail_moneywiz_export.plugins import QueryHints

MERCHANT_RE = re.compile(r"^Merchant:\s*(.+)$", re.MULTILINE)
AMOUNT_RE = re.compile(r"^Amount:\s*(CRC|USD)\s+([\d,]+\.\d{2})$", re.MULTILINE)
DATE_RE = re.compile(r"^Date:\s*(\d{4}-\d{2}-\d{2})$", re.MULTILINE)
CARD_RE = re.compile(r"^Card:\s*(\d{4})$", re.MULTILINE)


class DemoBankPlugin:
    id = "demo-bank"
    display_name = "Demo Bank"
    priority = 100

    def query_hints(self) -> QueryHints:
        return QueryHints(
            senders=("alerts@demo-bank.example",),
            subject_contains=("Demo Bank purchase alert",),
        )

    def match_score(self, message: GmailMessage) -> int:
        text = message.text
        if (
            "Demo Bank purchase alert" in message.subject
            and "Merchant:" in text
            and "Amount:" in text
        ):
            return 100
        if "Merchant:" in text and "Amount:" in text and "Card:" in text:
            return 50
        return 0

    def parse(self, message: GmailMessage) -> list[Transaction]:
        merchant_match = MERCHANT_RE.search(message.text)
        amount_match = AMOUNT_RE.search(message.text)
        date_match = DATE_RE.search(message.text)
        card_match = CARD_RE.search(message.text)

        if not merchant_match:
            raise ParseError("Demo Bank: missing Merchant")
        if not amount_match:
            raise ParseError("Demo Bank: missing Amount")
        if not date_match:
            raise ParseError("Demo Bank: missing Date")
        if not card_match:
            raise ParseError("Demo Bank: missing Card")

        parsed_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").strftime(
            "%m/%d/%Y"
        )
        currency = amount_match.group(1)
        amount = normalize_amount(amount_match.group(2))

        return [
            Transaction(
                bank=self.id,
                message_id=message.message_id,
                merchant=normalize_merchant(merchant_match.group(1)),
                date=parsed_date,
                amount=amount,
                currency=currency,
                card_identifier=card_match.group(1),
            )
        ]
