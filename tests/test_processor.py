from pathlib import Path

from gmail_moneywiz_export.mapping import AccountMappings
from gmail_moneywiz_export.models import GmailMessage
from gmail_moneywiz_export.parsers.promerica import PromericaPlugin
from gmail_moneywiz_export.processor import process_message

from tests.helpers import read_sample


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


def test_process_message_skips_when_matching_plugin_is_not_enabled() -> None:
    mappings = AccountMappings.from_file(Path("config/accounts.example.yaml"))
    message = GmailMessage(
        message_id="msg-bac",
        subject="BAC compra",
        sender="bank@example.com",
        label_ids=[],
        text=read_sample("bac/compra_crc_1234.txt"),
    )

    result = process_message(message, mappings, plugins=[PromericaPlugin()])

    assert result.status == "skipped"
    assert result.reason == "Unsupported email format"
