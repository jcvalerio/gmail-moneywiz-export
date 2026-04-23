from pathlib import Path

from gmail_moneywiz_export.mapping import AccountMappings


def test_mapping_resolves_account() -> None:
    mappings = AccountMappings.from_file(Path("config/accounts.example.yaml"))
    assert mappings.resolve("scotia", "VISA 4321", "CRC") == "Infinity"
    assert mappings.resolve("promerica", "5678", "USD") == "Black $"
