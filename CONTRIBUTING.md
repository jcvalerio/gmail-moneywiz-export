# Contributing

Thanks for contributing.

This project is intentionally small and conservative. The goal is to make it easy to add support for new bank email formats without forcing everyone into one personal Gmail workflow.

## Principles

Please keep changes aligned with these rules:

- make the smallest change that solves the problem
- prefer conservative matching over aggressive matching
- false negatives are better than false positives
- do not refactor unrelated code in the same PR
- keep plugin ids stable once published
- never commit secrets or real financial data

## Development setup

Install dependencies:

```bash
uv sync
```

Run the local checks used by CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Useful commands:

```bash
uv run gmail-moneywiz-export --help
uv run gmail-moneywiz-export --list-plugins
```

## Project model

The app has a small core plus plugins.

A plugin owns:
- query hints for Gmail search building
- message matching
- parsing into normalized transactions
- a stable plugin id used for account mappings

There are two contribution paths:

1. **built-in plugin**: add support directly in this repo
2. **third-party plugin**: create a separate Python package exposed through entry points

See also:
- `README.md`
- `docs/plugins.md`
- `examples/third_party_plugin/`

## Contributing a built-in plugin

Use this path when the integration is broadly useful and you want it maintained in this repository.

### Checklist

1. Add the parser/plugin implementation under `src/gmail_moneywiz_export/parsers/`
2. Register it in `src/gmail_moneywiz_export/plugins.py`
3. Add anonymized samples under `samples/`
4. Add tests under `tests/`
5. Update `config/accounts.example.yaml` if needed
6. Update docs if config or behavior changed

### Plugin requirements

A built-in plugin should define:

- `id`
- `display_name`
- `priority`
- `query_hints()`
- `match_score(message)`
- `parse(message)`

Guidance:

- use a short, stable `id` such as `bac`, `scotia`, `promerica`
- `id` becomes the namespace under `accounts.<plugin-id>` in user config
- keep `match_score()` conservative and deterministic
- if two formats are similar, prefer stronger matching conditions rather than broad ones
- if the email format is known but should not be exported, raise `SkipMessage`
- if the format should parse but required fields are missing, raise `ParseError`

### Matching guidance

Good matching usually combines a few highly specific signals:

- sender
- stable subject text
- stable body labels
- known card or transaction markers

Avoid matching on:

- generic words like `Compra`, `Monto`, `Tarjeta`
- content that is likely shared across multiple institutions
- assumptions based only on language or currency

## Contributing fixtures

Tests should use sanitized fixtures only.

Allowed:
- anonymized sample emails under `samples/`
- fake merchants
- fake last4/card identifiers
- fake references/auth codes
- edited dates and amounts when needed

Not allowed:
- real names
- real email addresses unless they are public sender addresses from institutions
- full card numbers
- real account numbers
- real transaction data
- raw exported inbox content
- OAuth credentials or tokens

If you are unsure whether a fixture is safe to commit, do not commit it.

## Testing expectations

For a new built-in plugin, include tests for:

- successful parse of at least one representative sample
- skip behavior when applicable
- parser failures for malformed or incomplete variants when useful
- plugin matching behavior when the format could overlap with another plugin

At minimum, before opening a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## External plugins

If an integration is niche, private, or experimental, prefer an external plugin package.

External plugins are regular Python packages that expose an entry point in:

- `gmail_moneywiz_export.plugins`

Example:

```toml
[project.entry-points."gmail_moneywiz_export.plugins"]
my-local-bank = "gmail_moneywiz_plugin_my_bank:MyBankPlugin"
```

This repo includes a copyable example at:

- `examples/third_party_plugin/`

That is the recommended starting point for custom/local integrations.

## Pull request scope

Please keep PRs focused.

Good PR examples:
- add one new bank plugin with samples and tests
- fix one parser bug with a regression test
- improve one documentation path for plugin authors

Avoid mixing:
- parser additions
- refactors
- style changes
- unrelated cleanup

in the same PR.

## Review expectations

A good PR usually includes:

- a short explanation of the email format/problem
- sanitized fixtures
- tests proving the behavior
- a clear statement if the parser is intentionally conservative
- notes about known unsupported variants, if any

## Security and privacy

This tool handles inbox messages and financial notifications.
Treat all contributions with that in mind.

Do not commit:
- `secrets/`
- OAuth tokens
- private inbox exports
- personally identifying data
- real transaction details

## Questions

If you want to add support but are unsure whether it belongs as a built-in or third-party plugin, open an issue or PR draft and describe:

- the institution/source
- whether it is broadly useful or personal/private
- whether the format is stable
- whether you can provide sanitized fixtures
