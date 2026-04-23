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
