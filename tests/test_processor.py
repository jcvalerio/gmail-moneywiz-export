from pathlib import Path

from gmail_moneywiz_export.mapping import AccountMappings
from gmail_moneywiz_export.models import GmailMessage
from gmail_moneywiz_export.processor import process_message


def test_process_message_includes_debug_preview_for_skips() -> None:
    mappings = AccountMappings.from_file(Path("config/accounts.example.yaml"))
    message = GmailMessage(
        message_id="msg-skip",
        subject="Estado de cuenta",
        sender="bank@example.com",
        label_ids=[],
        text="Primera línea\n\nSegunda línea\nTercera línea",
    )

    result = process_message(message, mappings, include_debug_preview=True)

    assert result.status == "skipped"
    assert result.sender == "bank@example.com"
    assert result.debug_preview == ["Primera línea", "Segunda línea", "Tercera línea"]
