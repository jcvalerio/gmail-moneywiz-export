from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Transaction:
    bank: str
    message_id: str
    merchant: str
    date: str
    amount: str
    currency: str
    card_identifier: str
    auth: str | None = None
    reference: str | None = None

    def to_csv_row(self, account: str) -> dict[str, str]:
        return {
            "account": account,
            "date": self.date,
            "amount": self.amount,
            "merchant": self.merchant,
            "currency": self.currency,
        }

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class GmailMessage:
    message_id: str
    subject: str
    sender: str
    label_ids: list[str]
    text: str
