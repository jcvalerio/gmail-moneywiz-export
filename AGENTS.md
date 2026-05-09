# AGENTS.md

Scope: repository-wide instructions for AI coding agents.

## Project overview
- Python 3.12+ CLI named `gmail-moneywiz-export`.
- Exports parsed Gmail bank transaction emails to MoneyWiz CSV files.
- Core source lives in `src/gmail_moneywiz_export/`; tests in `tests/`.
- Built-in bank parsers live in `src/gmail_moneywiz_export/parsers/`.
- Third-party plugin template lives in `examples/third_party_plugin/`.

## Dev environment
- Use `uv` for dependency and environment management.
- Sync dependencies with `uv sync --group dev`.
- Run the CLI with `uv run gmail-moneywiz-export`.
- List discovered plugins with `uv run gmail-moneywiz-export --list-plugins`.

## Checks to run
- Lint: `uv run ruff check .`.
- Format check: `uv run ruff format --check .`.
- Tests: `uv run pytest`.
- Prefer focused `uv run pytest tests/path.py` while iterating.

## Code style
- Make minimal, surgical changes; avoid unrelated refactors.
- Match existing style and public import/export formats unless asked.
- Keep parsers small, explicit, and conservative.
- Prefer false negatives over false positives for email matching.
- For new built-ins, add registration, sanitized samples, and tests.
- Keep plugin IDs stable; config uses them as account namespaces.
- Do not auto-enable discovered third-party plugins.
- Update docs/config examples when behavior or setup changes.

## Privacy and safety
- Never commit raw emails, names, card IDs, OAuth tokens, or real transactions.
- Store secrets only under `secrets/`; do not track new secret files.
- Samples under `samples/` must be anonymized fixtures.
- Dry-run is default; be careful changing Gmail mutation behavior.

If unsure, ask before changing CSV schema, parsing scope, or Gmail mutations.
