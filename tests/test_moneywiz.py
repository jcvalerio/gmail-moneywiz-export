from pathlib import Path

import pytest

from gmail_moneywiz_export.moneywiz import MoneyWizHistory, build_moneywiz_rows


def test_moneywiz_history_reads_sep_csv_and_infers_merchant_default(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "moneywiz.csv"
    history_path.write_text(
        "sep=,\n"
        "Description,Payee,Category,Memo\n"
        "WALMART TIBAS OCN00,Walmart,Food & Dining ► Groceries,\n"
        "WALMART TIBAS OCN00,Walmart,Food & Dining ► Groceries,\n"
        "WALMART TIBAS OCN00,Walmart,Shopping ► Household,\n",
        encoding="utf-8",
    )

    history = MoneyWizHistory.from_csv(history_path)

    default = history.default_for_merchant("WALMART TIBAS OCN00")
    assert default is not None
    assert default.payee == "Walmart"
    assert default.category == "Food & Dining ► Groceries"


def test_moneywiz_history_resolves_existing_values_with_normal_spaces(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "moneywiz.csv"
    history_path.write_text(
        "Description,Payee,Category,Memo\n"
        "2da Quincena,Servicios\u00a0de\u00a0Limpieza,Community ► Servicios de Limpieza,\n",
        encoding="utf-8",
    )

    history = MoneyWizHistory.from_csv(history_path)

    assert (
        history.resolve_payee("Servicios de Limpieza")
        == "Servicios\u00a0de\u00a0Limpieza"
    )


def test_build_moneywiz_rows_moves_merchant_to_memo_and_adds_mapping(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "moneywiz.csv"
    history_path.write_text(
        "Description,Payee,Category,Memo\n"
        "FERRETERIA EPA SA,Ferretería,Community ► Maintenance,\n",
        encoding="utf-8",
    )
    history = MoneyWizHistory.from_csv(history_path)

    rows = build_moneywiz_rows(
        [
            {
                "account": "AMEX Cashback",
                "date": "04/29/2026",
                "amount": "20990.00",
                "merchant": "FERRETERIA EPA SA",
                "currency": "CRC",
            }
        ],
        history,
    )

    assert rows == [
        {
            "account": "AMEX Cashback",
            "date": "04/29/2026",
            "amount": "20990.00",
            "payee": "Ferretería",
            "category": "Community ► Maintenance",
            "memo": "FERRETERIA EPA SA",
            "currency": "CRC",
        }
    ]


def test_moneywiz_history_suggests_payee_from_merchant_overlap(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "moneywiz.csv"
    history_path.write_text(
        "Description,Payee,Category,Memo\n"
        "Cloud hosting,Amazon Web Services,Community ► Subscriptions ► Software,\n"
        "Delivery,Uber Eats,Food & Dining ► Restaurants,\n",
        encoding="utf-8",
    )
    history = MoneyWizHistory.from_csv(history_path)

    aws_default = history.default_for_merchant(
        "Amazon web services aws.amazon.co Estados Unidos de América"
    )
    uber_default = history.default_for_merchant("DLC* UBER EATS SAN JOSE")

    assert aws_default is not None
    assert aws_default.payee == "Amazon Web Services"
    assert aws_default.category == "Community ► Subscriptions ► Software"
    assert uber_default is not None
    assert uber_default.payee == "Uber Eats"
    assert uber_default.category == "Food & Dining ► Restaurants"


def test_interactive_search_allows_numbered_payee_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "moneywiz.csv"
    history_path.write_text(
        "Description,Payee,Category,Memo\n"
        "Delivery,Uber Eats,Food & Dining ► Restaurants,\n",
        encoding="utf-8",
    )
    history = MoneyWizHistory.from_csv(history_path)
    responses = iter(["?uber", "1", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(responses))

    rows = build_moneywiz_rows(
        [
            {
                "account": "AMEX Cashback",
                "date": "05/03/2026",
                "amount": "2500.00",
                "merchant": "UNKNOWN MERCHANT",
                "currency": "CRC",
            }
        ],
        history,
        interactive=True,
    )

    assert rows[0]["payee"] == "Uber Eats"
    assert rows[0]["category"] == "Food & Dining ► Restaurants"
