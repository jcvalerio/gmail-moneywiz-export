# Gmail MoneyWiz Export

[![CI](https://github.com/jcvalerio/gmail-moneywiz-export/actions/workflows/ci.yml/badge.svg)](https://github.com/jcvalerio/gmail-moneywiz-export/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://github.com/jcvalerio/gmail-moneywiz-export/actions/workflows/ci.yml)

Local-only Gmail bank email exporter that:
- queries a narrow Gmail search
- parses supported bank transaction emails through plugins
- maps cards to MoneyWiz accounts
- exports one CSV file per run
- optionally adds `banks-processed` and archives handled emails

## Stack
- Python 3.12+
- `uv` for environment and dependency management
- Gmail API with a local OAuth token

## How it works

The app is split into a small core plus plugins.

Each enabled plugin owns four things:
- **query hints** used to build the Gmail search
- **message matching** to decide whether it can parse a message
- **parsing** from raw email text into normalized transactions
- **a stable plugin id** used as the account-mapping namespace

At runtime the flow is:
1. load config from `config/accounts.yaml`
2. discover built-in and installed third-party plugins
3. activate only the plugins listed in `plugins.enabled`
4. build a Gmail query from the enabled plugins' query hints
5. fetch matching emails
6. choose the best matching plugin for each message
7. parse transactions
8. map parsed card identifiers to local MoneyWiz accounts
9. write CSV and summary output
10. in `--apply` mode, label and archive only successfully exported messages

## Built-in plugins

Current built-ins:
- `bac`
- `scotia`
- `promerica`

List everything the app can see:

```bash
uv run gmail-moneywiz-export --list-plugins
```

A `*` means the plugin is enabled by your config.

## Setup

1. Create a Google OAuth desktop app and download the credentials JSON.
2. Save it as `secrets/credentials.json`.
3. Copy `config/accounts.example.yaml` to `config/accounts.yaml`.
4. Review `config/accounts.yaml` and adjust enabled plugins, Gmail query hints, and account names.
5. Install dependencies:

```bash
uv sync
```

## Config

Example config:

```yaml
plugins:
  enabled:
    - bac
    - scotia
    - promerica
  query_hints:
    bac:
      labels:
        - banks-bac
    scotia:
      labels:
        - banks-scotiabank
    promerica:
      labels:
        - banks-promerica

query:
  base: label:inbox

accounts:
  bac:
    "AMEX ***********1234":
      CRC: "AMEX"
      USD: "AMEX $"

  scotia:
    "VISA 4321":
      CRC: "Infinity"
      USD: "Infinity $"
```

Notes:
- `plugins.enabled` is the explicit allowlist
- discovered third-party plugins stay disabled until you add them to `plugins.enabled`
- `plugins.query_hints.<id>` overrides the plugin defaults used to build the Gmail query
- `accounts.<plugin-id>` is the mapping namespace for parsed transactions
- legacy account-only config files still load, but the plugin-aware shape above is the preferred format

## First run

Dry-run is the default:

```bash
uv run gmail-moneywiz-export
```

On first run, the browser-based Google OAuth flow will open and store the token in `secrets/token.json`.

If apply mode fails because the saved token was created with weaker scopes, delete `secrets/token.json` and run again. The tool now also forces re-auth if the token does not include `gmail.modify`.

## Apply mode

When you're ready to mutate Gmail:

```bash
uv run gmail-moneywiz-export --apply
```

Apply mode will only mutate emails that were fully parsed and exported successfully.
Mutation means:
- add the processed Gmail label
- archive the email by removing the `INBOX` label

## Options

```bash
uv run gmail-moneywiz-export --help
```

List available plugins:

```bash
uv run gmail-moneywiz-export --list-plugins
```

Inspect the Gmail labels the API sees:

```bash
uv run gmail-moneywiz-export --list-labels
```

If your Gmail search alias and actual Gmail label name differ, override them separately:

```bash
uv run gmail-moneywiz-export --apply \
  --processed-query-label "banks-processed" \
  --processed-label "Banks/Processed"
```

To include sender and a short preview for skipped emails:

```bash
uv run gmail-moneywiz-export --debug-skips
```

If you need to disable the built-in subject exclusions used to ignore obvious statement/update emails:

```bash
uv run gmail-moneywiz-export --no-default-subject-exclusions
```

## Extend with a third-party plugin

Third-party plugins are normal Python packages exposed through the `gmail_moneywiz_export.plugins` entry point group.

Minimal example:

```toml
[project.entry-points."gmail_moneywiz_export.plugins"]
my-local-bank = "gmail_moneywiz_plugin_my_bank:MyBankPlugin"
```

The entry point can resolve to:
- a plugin instance
- a no-argument plugin class
- a no-argument factory returning a plugin instance

A minimal plugin looks like this:

```python
from gmail_moneywiz_export.models import GmailMessage, Transaction
from gmail_moneywiz_export.plugins import QueryHints

class MyBankPlugin:
    id = "my-local-bank"
    display_name = "My Local Bank"
    priority = 100

    def query_hints(self) -> QueryHints:
        return QueryHints(
            senders=("alerts@examplebank.com",),
            subject_contains=("Purchase alert",),
        )

    def match_score(self, message: GmailMessage) -> int:
        if "Purchase alert" in message.subject:
            return 100
        return 0

    def parse(self, message: GmailMessage) -> list[Transaction]:
        ...
```

After installing the plugin package locally, enable it in `config/accounts.yaml`:

```yaml
plugins:
  enabled:
    - my-local-bank

accounts:
  my-local-bank:
    "1234":
      USD: "My Bank $"
```

The app will discover it, but it will not run until you explicitly enable it.

### Copyable example package

This repo includes a minimal external plugin template at:

- `examples/third_party_plugin/`

It shows:
- package layout
- entry point registration
- a working plugin class
- how to enable a local plugin in config

To install the example locally from this repo:

```bash
uv pip install -e ./examples/third_party_plugin --no-deps
```

Then verify discovery:

```bash
uv run gmail-moneywiz-export --list-plugins
```

## Contribute a built-in plugin

If you want to add support for a new bank in this repo:

1. add a plugin implementation under `src/gmail_moneywiz_export/parsers/`
2. register it in `src/gmail_moneywiz_export/plugins.py`
3. add anonymized sample fixtures under `samples/`
4. add tests covering matching and parsing
5. update `config/accounts.example.yaml` if the example config should show it
6. update docs if setup or config expectations changed

Contributor rules:
- do not commit raw emails, names, card identifiers, or real transaction data
- keep matching conservative; false negatives are better than false positives
- keep plugin ids stable once published because they are used in account mappings
- prefer the smallest parser that handles the current template well
- touch only code required for the new integration

See also:
- [docs/plugins.md](docs/plugins.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- `examples/third_party_plugin/`

## Output

Each run creates:
- `exports/transactions-<timestamp>.csv`
- `exports/transactions-<timestamp>.summary.json`

CSV format:

```csv
account,date,amount,merchant,currency
```

## Samples, linting, and tests

Parser and plugin tests read anonymized sample fixtures from `samples/`.
Only add sanitized samples there when a bank email template changes. Do not commit raw emails, names, card identifiers, or real transaction details.

Local checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

GitHub Actions runs the same lint, formatting, and test checks on pull requests and pushes to `main`.
Tests run on Python 3.12 and 3.13.
