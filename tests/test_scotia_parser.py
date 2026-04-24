from gmail_moneywiz_export.parsers import SkipMessage
from gmail_moneywiz_export.parsers.scotia import parse_scotia

from tests.helpers import read_sample


def test_parse_scotia_approved_transaction() -> None:
    transactions = parse_scotia(
        "msg-2", read_sample("scotia/approved_crc_visa_4321.txt")
    )
    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.bank == "scotia"
    assert transaction.card_identifier == "VISA 4321"
    assert transaction.currency == "CRC"
    assert transaction.amount == "36700.00"
    assert transaction.date == "04/21/2026"


def test_parse_scotia_declined_transaction() -> None:
    try:
        parse_scotia("msg-3", read_sample("scotia/declined_crc_visa_4321.txt"))
    except SkipMessage as error:
        assert "not approved" in str(error)
    else:
        raise AssertionError("Expected SkipMessage")
