from pathlib import Path

from gmail_moneywiz_export.mapping import AccountMappings
from gmail_moneywiz_export.models import GmailMessage
from gmail_moneywiz_export.parsers.promerica import PromericaPlugin
from gmail_moneywiz_export.plugins import QueryHints
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


def test_process_message_skips_zero_amount_authorization() -> None:
    mappings = AccountMappings.from_file(Path("config/accounts.example.yaml"))
    message = GmailMessage(
        message_id="msg-zero",
        subject="BAC compra",
        sender="bank@example.com",
        label_ids=[],
        text=read_sample("bac/verificacion_usd_cero.txt"),
    )

    result = process_message(message, mappings)

    assert result.status == "skipped"
    assert result.reason == "BAC zero-amount authorization"
    assert result.plugin_id == "bac"


def test_process_message_reports_normalization_failures_as_skips() -> None:
    mappings = AccountMappings.from_file(Path("config/accounts.example.yaml"))
    text = read_sample("bac/compra_crc_1234.txt").replace(
        "CRC 45,000.00", "CRC no-es-un-monto"
    )
    message = GmailMessage(
        message_id="msg-bad-amount",
        subject="BAC compra",
        sender="bank@example.com",
        label_ids=[],
        text=text,
    )

    result = process_message(message, mappings)

    assert result.status == "skipped"
    assert result.reason is not None
    assert "Could not parse amount" in result.reason


def test_process_message_returns_error_instead_of_raising() -> None:
    class ExplodingPlugin:
        id = "exploding"
        display_name = "Exploding"
        priority = 500

        def query_hints(self) -> QueryHints:
            return QueryHints()

        def match_score(self, message: GmailMessage) -> int:
            return 100

        def parse(self, message: GmailMessage) -> list:
            raise RuntimeError("boom")

    mappings = AccountMappings.from_file(Path("config/accounts.example.yaml"))
    message = GmailMessage(
        message_id="msg-boom",
        subject="BAC compra",
        sender="bank@example.com",
        label_ids=[],
        text=read_sample("bac/compra_crc_1234.txt"),
    )

    result = process_message(message, mappings, plugins=[ExplodingPlugin()])

    assert result.status == "error"
    assert result.reason == "RuntimeError: boom"
