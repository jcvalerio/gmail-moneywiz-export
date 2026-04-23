from dataclasses import asdict, dataclass

from gmail_moneywiz_export.mapping import AccountMappings, MappingError
from gmail_moneywiz_export.models import GmailMessage, Transaction
from gmail_moneywiz_export.parsers import ParseError, SkipMessage
from gmail_moneywiz_export.parsers.bac import parse_bac
from gmail_moneywiz_export.parsers.promerica import parse_promerica
from gmail_moneywiz_export.parsers.scotia import parse_scotia


@dataclass
class MessageResult:
    message_id: str
    subject: str
    sender: str
    status: str
    reason: str | None = None
    rows: list[dict[str, str]] | None = None
    transactions: list[dict[str, str | None]] | None = None
    debug_preview: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def process_message(message: GmailMessage, mappings: AccountMappings, include_debug_preview: bool = False) -> MessageResult:
    parser = _detect_parser(message.text)
    if parser is None:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason="Unsupported email format",
            debug_preview=_build_debug_preview(message.text) if include_debug_preview else None,
        )

    try:
        transactions = parser(message.message_id, message.text)
    except SkipMessage as error:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason=str(error),
            debug_preview=_build_debug_preview(message.text) if include_debug_preview else None,
        )
    except (ParseError, MappingError) as error:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason=str(error),
            debug_preview=_build_debug_preview(message.text) if include_debug_preview else None,
        )

    rows: list[dict[str, str]] = []
    try:
        for transaction in transactions:
            account = mappings.resolve(
                bank=transaction.bank,
                card_identifier=transaction.card_identifier,
                currency=transaction.currency,
            )
            rows.append(transaction.to_csv_row(account))
    except MappingError as error:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason=str(error),
            debug_preview=_build_debug_preview(message.text) if include_debug_preview else None,
        )

    return MessageResult(
        message_id=message.message_id,
        subject=message.subject,
        sender=message.sender,
        status="ready",
        rows=rows,
        transactions=[transaction.to_dict() for transaction in transactions],
    )


def _detect_parser(text: str):
    if "DAVIbank le notifica" in text:
        return parse_scotia
    if "Comercio:" in text and "Monto:" in text and (
        "A continuación le detallamos la transacción realizada" in text or "Tipo de Transacción:" in text
    ):
        return parse_bac
    if "Número de tarjeta" in text and ("Fecha/hora" in text or "****-****-****-" in text):
        return parse_promerica
    return None


def _build_debug_preview(text: str, max_lines: int = 8) -> list[str]:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return [line for line in lines if line][:max_lines]
