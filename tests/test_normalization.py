from gmail_moneywiz_export.normalization import (
    normalize_amount,
    parse_bac_date,
    parse_promerica_date,
    parse_scotia_date,
)


def test_normalize_amount_removes_commas_and_keeps_two_decimals() -> None:
    assert normalize_amount("CRC 45,000.00") == "45000.00"


def test_parse_bac_date() -> None:
    assert parse_bac_date("Mar 26, 2026, 11:15") == "03/26/2026"


def test_parse_bac_date_with_spanish_month() -> None:
    assert parse_bac_date("Abr 29, 2026, 10:34") == "04/29/2026"


def test_parse_scotia_date() -> None:
    assert parse_scotia_date("21/04/2026") == "04/21/2026"


def test_parse_promerica_date() -> None:
    assert parse_promerica_date("05 dic 2025 / 23:08") == "12/05/2025"
