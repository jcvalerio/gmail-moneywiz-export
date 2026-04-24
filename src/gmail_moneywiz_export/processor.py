from dataclasses import asdict, dataclass

from gmail_moneywiz_export.mapping import AccountMappings, MappingError
from gmail_moneywiz_export.models import GmailMessage
from gmail_moneywiz_export.parsers import ParseError, SkipMessage
from gmail_moneywiz_export.plugins import (
    PluginError,
    SourcePlugin,
    builtin_plugins,
    pick_plugin,
)


@dataclass
class MessageResult:
    message_id: str
    subject: str
    sender: str
    status: str
    reason: str | None = None
    plugin_id: str | None = None
    rows: list[dict[str, str]] | None = None
    transactions: list[dict[str, str | None]] | None = None
    debug_preview: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def process_message(
    message: GmailMessage,
    mappings: AccountMappings,
    plugins: list[SourcePlugin] | None = None,
    include_debug_preview: bool = False,
) -> MessageResult:
    plugins = plugins or [
        definition.plugin for definition in builtin_plugins().values()
    ]

    try:
        match = pick_plugin(message, plugins)
    except PluginError as error:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason=str(error),
            debug_preview=_build_debug_preview(message.text)
            if include_debug_preview
            else None,
        )

    if match is None:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason="Unsupported email format",
            debug_preview=_build_debug_preview(message.text)
            if include_debug_preview
            else None,
        )

    try:
        transactions = match.plugin.parse(message)
    except SkipMessage as error:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason=str(error),
            plugin_id=match.plugin.id,
            debug_preview=_build_debug_preview(message.text)
            if include_debug_preview
            else None,
        )
    except (ParseError, MappingError) as error:
        return MessageResult(
            message_id=message.message_id,
            subject=message.subject,
            sender=message.sender,
            status="skipped",
            reason=str(error),
            plugin_id=match.plugin.id,
            debug_preview=_build_debug_preview(message.text)
            if include_debug_preview
            else None,
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
            plugin_id=match.plugin.id,
            debug_preview=_build_debug_preview(message.text)
            if include_debug_preview
            else None,
        )

    return MessageResult(
        message_id=message.message_id,
        subject=message.subject,
        sender=message.sender,
        status="ready",
        plugin_id=match.plugin.id,
        rows=rows,
        transactions=[transaction.to_dict() for transaction in transactions],
    )


def _build_debug_preview(text: str, max_lines: int = 8) -> list[str]:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return [line for line in lines if line][:max_lines]
