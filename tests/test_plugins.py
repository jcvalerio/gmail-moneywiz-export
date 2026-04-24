import pytest

from gmail_moneywiz_export.config import AppConfig
from gmail_moneywiz_export.models import GmailMessage
from gmail_moneywiz_export.plugins import (
    PluginError,
    QueryHints,
    pick_plugin,
    resolve_enabled_plugins,
)


class DummyPlugin:
    def __init__(self, plugin_id: str, score: int, priority: int = 100):
        self.id = plugin_id
        self.display_name = plugin_id.upper()
        self.priority = priority
        self._score = score

    def query_hints(self) -> QueryHints:
        return QueryHints()

    def match_score(self, message: GmailMessage) -> int:
        return self._score

    def parse(self, message: GmailMessage) -> list:
        return []


def test_pick_plugin_returns_highest_score() -> None:
    message = GmailMessage(
        message_id="msg-1", subject="", sender="", label_ids=[], text="demo"
    )

    match = pick_plugin(message, [DummyPlugin("low", 10), DummyPlugin("high", 90)])

    assert match is not None
    assert match.plugin.id == "high"
    assert match.score == 90


def test_pick_plugin_raises_on_ambiguous_match() -> None:
    message = GmailMessage(
        message_id="msg-2", subject="", sender="", label_ids=[], text="demo"
    )

    with pytest.raises(PluginError):
        pick_plugin(message, [DummyPlugin("a", 90), DummyPlugin("b", 90)])


def test_resolve_enabled_plugins_preserves_requested_order() -> None:
    plugins = resolve_enabled_plugins(["scotia", "bac"])

    assert [plugin.id for plugin in plugins] == ["scotia", "bac"]


def test_app_config_supports_new_format() -> None:
    config = AppConfig.from_dict(
        {
            "plugins": {
                "enabled": ["bac"],
                "query_hints": {
                    "bac": {
                        "labels": ["custom-bac"],
                    }
                },
            },
            "query": {"base": "label:inbox category:primary"},
            "accounts": {
                "bac": {
                    "AMEX ***********1234": {
                        "CRC": "AMEX",
                    }
                }
            },
        }
    )

    assert config.enabled_plugins == ("bac",)
    assert config.query_base == "label:inbox category:primary"
    assert config.plugin_query_hints["bac"].labels == ("custom-bac",)
    assert config.accounts["bac"]["AMEX ***********1234"]["CRC"] == "AMEX"


def test_app_config_supports_legacy_account_mapping_shape() -> None:
    config = AppConfig.from_dict(
        {
            "bac": {
                "AMEX ***********1234": {
                    "CRC": "AMEX",
                }
            }
        }
    )

    assert "bac" in config.accounts
    assert set(config.enabled_plugins) == {"bac", "promerica", "scotia"}
