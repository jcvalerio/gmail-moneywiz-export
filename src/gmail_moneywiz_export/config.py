from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from gmail_moneywiz_export.plugins import QueryHintsOverride, default_enabled_plugin_ids

_RESERVED_TOP_LEVEL_KEYS = {"accounts", "plugins", "query"}


@dataclass(frozen=True)
class AppConfig:
    accounts: dict[str, dict[str, dict[str, str]]]
    enabled_plugins: tuple[str, ...]
    query_base: str
    plugin_query_hints: dict[str, QueryHintsOverride]

    @classmethod
    def default(cls) -> "AppConfig":
        return cls(
            accounts={},
            enabled_plugins=default_enabled_plugin_ids(),
            query_base="label:inbox",
            plugin_query_hints={},
        )

    @classmethod
    def from_file(cls, path: Path) -> "AppConfig":
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        plugins_data = data.get("plugins") or {}
        query_data = data.get("query") or {}
        enabled_plugins = tuple(
            plugins_data.get("enabled") or default_enabled_plugin_ids()
        )
        plugin_query_hints = {
            plugin_id: QueryHintsOverride.from_dict(override)
            for plugin_id, override in (plugins_data.get("query_hints") or {}).items()
        }
        return cls(
            accounts=_extract_accounts(data),
            enabled_plugins=enabled_plugins,
            query_base=str(query_data.get("base") or "label:inbox"),
            plugin_query_hints=plugin_query_hints,
        )


def _extract_accounts(data: dict[str, Any]) -> dict[str, dict[str, dict[str, str]]]:
    if "accounts" in data:
        accounts = data.get("accounts") or {}
        return {bank: identifiers or {} for bank, identifiers in accounts.items()}

    return {
        bank: identifiers or {}
        for bank, identifiers in data.items()
        if bank not in _RESERVED_TOP_LEVEL_KEYS
    }
