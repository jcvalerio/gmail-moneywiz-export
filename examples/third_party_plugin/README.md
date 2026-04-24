# Example third-party plugin

This is a minimal external plugin package for `gmail-moneywiz-export`.

It demonstrates:
- package layout
- entry point registration
- a simple plugin class
- local enablement through `config/accounts.yaml`

## Install locally from this repo

From the repo root:

```bash
uv pip install -e ./examples/third_party_plugin --no-deps
```

`--no-deps` is convenient here because the main project is already your active environment.
If you copy this package into its own repo, declare `gmail-moneywiz-export` as a normal dependency and install it normally.

## Verify discovery

```bash
uv run gmail-moneywiz-export --list-plugins
```

You should see `demo-bank` in the list.

## Enable it

Add it to `config/accounts.yaml`:

```yaml
plugins:
  enabled:
    - demo-bank
  query_hints:
    demo-bank:
      senders:
        - alerts@demo-bank.example

accounts:
  demo-bank:
    "1234":
      USD: "Demo Bank $"
      CRC: "Demo Bank ₡"
```

## Example email shape

```text
Subject: Demo Bank purchase alert
From: alerts@demo-bank.example

Merchant: DEMO STORE
Amount: USD 12.34
Date: 2026-04-23
Card: 1234
```

## Entry point

The package is exposed through:

```toml
[project.entry-points."gmail_moneywiz_export.plugins"]
demo-bank = "gmail_moneywiz_plugin_demo_bank:DemoBankPlugin"
```

That lets the main app discover it without changing this repository.
