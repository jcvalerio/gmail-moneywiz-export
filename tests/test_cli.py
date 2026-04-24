from gmail_moneywiz_export.cli import build_query, main
from gmail_moneywiz_export.parsers.bac import BacPlugin
from gmail_moneywiz_export.plugins import QueryHintsOverride


def test_build_query_adds_default_subject_exclusions() -> None:
    query = build_query("banks-processed")
    assert "-label:banks-processed" in query
    assert '-subject:"Estado de cuenta"' in query
    assert '-subject:"ACTUALIZACIÓN DE DATOS"' in query


def test_build_query_uses_only_enabled_plugins() -> None:
    query = build_query("banks-processed", plugins=[BacPlugin()])
    assert "label:banks-bac" in query
    assert "banks-scotiabank" not in query
    assert "banks-promerica" not in query


def test_build_query_applies_plugin_query_hint_overrides() -> None:
    query = build_query(
        "banks-processed",
        plugins=[BacPlugin()],
        query_hints_overrides={"bac": QueryHintsOverride(labels=("custom-bac",))},
    )
    assert "label:custom-bac" in query
    assert "banks-bac" not in query


def test_list_plugins_does_not_require_credentials(capsys, tmp_path) -> None:
    config_path = tmp_path / "accounts.yaml"
    config_path.write_text(
        "plugins:\n  enabled:\n    - bac\naccounts: {}\n", encoding="utf-8"
    )

    exit_code = main(["--list-plugins", "--accounts", str(config_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "* bac (built-in) - BAC" in captured.out
