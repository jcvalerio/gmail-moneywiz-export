import pytest

from gmail_moneywiz_export.parsers import SkipMessage
from gmail_moneywiz_export.parsers.bac import parse_bac

from tests.helpers import read_sample


def test_parse_bac_purchase() -> None:
    transactions = parse_bac("msg-1", read_sample("bac/compra_crc_1234.txt"))
    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.bank == "bac"
    assert transaction.card_identifier == "AMEX ***********1234"
    assert transaction.currency == "CRC"
    assert transaction.amount == "45000.00"
    assert transaction.date == "03/26/2026"
    assert transaction.merchant == "COMERCIO DEMO"


def test_parse_bac_skips_zero_amount_authorization() -> None:
    with pytest.raises(SkipMessage, match="zero-amount authorization"):
        parse_bac("msg-2", read_sample("bac/verificacion_usd_cero.txt"))


def test_parse_bac_does_not_print_message_text(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parse_bac("msg-3", read_sample("bac/compra_crc_1234.txt"))

    assert capsys.readouterr().out == ""
