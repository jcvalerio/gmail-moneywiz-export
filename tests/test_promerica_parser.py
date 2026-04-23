from gmail_moneywiz_export.parsers.promerica import parse_promerica

from tests.helpers import read_sample


def test_parse_promerica_transaction() -> None:
    transactions = parse_promerica("msg-4", read_sample("promerica/usd_5678.txt"))
    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.bank == "promerica"
    assert transaction.card_identifier == "5678"
    assert transaction.currency == "USD"
    assert transaction.amount == "26.64"
    assert transaction.date == "12/05/2025"
    assert transaction.merchant == "COMERCIO DEMO ONLINE USA"
