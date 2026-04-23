# Gmail MoneyWiz Export

Local-only Gmail bank email exporter that:
- queries a narrow Gmail search
- conservatively excludes known non-transaction subjects from the Gmail query
- parses supported bank transaction emails
- maps cards to MoneyWiz accounts
- exports one CSV file per run
- optionally adds `banks-processed` and archives handled emails

## Stack
- Python 3.12+
- `uv` for environment and dependency management
- Gmail API with a local OAuth token

## Setup

1. Create a Google OAuth desktop app and download the credentials JSON.
2. Save it as `secrets/credentials.json`.
3. Copy `config/accounts.example.yaml` to `config/accounts.yaml`.
4. Review `config/accounts.yaml` and adjust it with your local account names.
5. Install dependencies:

```bash
uv sync
```

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

To inspect the Gmail labels the API sees:

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

## Output

Each run creates:
- `exports/transactions-<timestamp>.csv`
- `exports/transactions-<timestamp>.summary.json`

CSV format:

```csv
account,date,amount,merchant,currency
```

## Samples and tests

Parser tests read anonymized sample fixtures from `samples/`.
Only add sanitized samples there when a bank email template changes. Do not commit raw emails, names, card identifiers, or real transaction details.

```bash
uv run pytest
```
