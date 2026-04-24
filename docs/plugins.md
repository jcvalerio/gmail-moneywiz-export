# Plugins

This project uses a small plugin interface for bank/source integrations.

A plugin owns four things:

1. query hints for finding candidate Gmail messages
2. message matching
3. parsing a message into normalized transactions
4. a stable plugin id used for account mappings

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

## Config

Example:

```yaml
plugins:
  enabled:
    - bac
    - scotia
    - my-local-bank
  query_hints:
    bac:
      labels:
        - banks-bac
    my-local-bank:
      senders:
        - alerts@examplebank.com

query:
  base: label:inbox

accounts:
  bac:
    "AMEX ***********1234":
      CRC: "AMEX"
      USD: "AMEX $"
```

Notes:

- only plugins listed in `plugins.enabled` are active
- discovered third-party plugins are **not** auto-enabled
- `plugins.query_hints.<id>` overrides the plugin defaults for Gmail query building
- `accounts.<plugin-id>` is the namespace used for account mapping

## Third-party plugins

Third-party plugins are regular Python packages exposed through entry points.
A copyable example lives in `examples/third_party_plugin/`.

`pyproject.toml` in the plugin package:

```toml
[project.entry-points."gmail_moneywiz_export.plugins"]
my-local-bank = "gmail_moneywiz_plugin_my_bank:MyBankPlugin"
```

The entry point can resolve to:

- a plugin instance
- a no-argument plugin class
- a no-argument factory returning a plugin instance

To try the example from this repo:

```bash
uv pip install -e ./examples/third_party_plugin --no-deps
uv run gmail-moneywiz-export --list-plugins
```

## Plugin contract

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
            subject_contains=("Compra aprobada",),
        )

    def match_score(self, message: GmailMessage) -> int:
        if "Compra aprobada" in message.text:
            return 100
        return 0

    def parse(self, message: GmailMessage) -> list[Transaction]:
        ...
```

## Contributor checklist for parser/plugin PRs

- add a plugin with a stable `id`
- add anonymized fixture samples under `samples/`
- add parser/plugin tests
- do not commit raw emails, names, card identifiers, or real transaction data
- keep detection conservative; false negatives are better than false positives
- prefer the smallest parser that handles the current email template well
