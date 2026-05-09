import csv
from pathlib import Path

from gmail_moneywiz_export.exporter import write_csv


def test_write_csv_uses_expenses_and_payee_description(tmp_path: Path) -> None:
    csv_path = tmp_path / "moneywiz.csv"

    write_csv(
        csv_path,
        [
            {
                "account": "AMEX Cashback",
                "date": "04/29/2026",
                "amount": "20990.00",
                "payee": "Ferretería",
                "category": "Community ► Maintenance",
                "memo": "FERRETERIA EPA SA",
                "currency": "CRC",
            }
        ],
    )

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert reader.fieldnames == [
        "account",
        "date",
        "expenses",
        "payee",
        "description",
        "category",
        "memo",
        "currency",
    ]
    assert rows == [
        {
            "account": "AMEX Cashback",
            "date": "04/29/2026",
            "expenses": "20990.00",
            "payee": "Ferretería",
            "description": "Ferretería",
            "category": "Community ► Maintenance",
            "memo": "FERRETERIA EPA SA",
            "currency": "CRC",
        }
    ]
