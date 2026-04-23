from pathlib import Path

import yaml


class MappingError(ValueError):
    pass


class AccountMappings:
    def __init__(self, mappings: dict[str, dict[str, dict[str, str]]]):
        self._mappings = mappings

    @classmethod
    def from_file(cls, path: Path) -> "AccountMappings":
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return cls(data)

    def resolve(self, bank: str, card_identifier: str, currency: str) -> str:
        bank_mapping = self._mappings.get(bank, {})
        identifier_mapping = bank_mapping.get(card_identifier)
        if identifier_mapping is None:
            raise MappingError(f"Unknown card identifier for {bank}: {card_identifier}")
        account = identifier_mapping.get(currency)
        if account is None:
            raise MappingError(
                f"Unknown currency mapping for {bank}: {card_identifier} / {currency}"
            )
        return account
