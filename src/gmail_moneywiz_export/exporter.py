import csv
from pathlib import Path


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "account",
        "date",
        "expenses",
        "payee",
        "description",
        "category",
        "memo",
        "currency",
    ]
    output_rows = []
    for row in rows:
        output_row = {field: row.get(field, "") for field in fieldnames}
        output_row["expenses"] = row.get("amount", "")
        output_row["description"] = row.get("payee", "")
        output_rows.append(output_row)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
