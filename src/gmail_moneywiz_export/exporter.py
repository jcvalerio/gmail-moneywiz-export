import csv
from pathlib import Path


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["account", "date", "amount", "merchant", "currency"]
        )
        writer.writeheader()
        writer.writerows(rows)
