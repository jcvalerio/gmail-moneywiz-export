from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from gmail_moneywiz_export.config import AppConfig
from gmail_moneywiz_export.exporter import write_csv
from gmail_moneywiz_export.gmail_client import GmailClient
from gmail_moneywiz_export.mapping import AccountMappings
from gmail_moneywiz_export.moneywiz import MoneyWizHistory, build_moneywiz_rows
from gmail_moneywiz_export.plugins import (
    QueryHintsOverride,
    SourcePlugin,
    builtin_plugins,
    discover_plugins,
    resolve_enabled_plugins,
)
from gmail_moneywiz_export.processor import MessageResult, process_message

DEFAULT_PROCESSED_QUERY_LABEL = "banks-processed"
DEFAULT_PROCESSED_LABEL = "Banks/Processed"
DEFAULT_SUBJECT_EXCLUSIONS = [
    "Estado de cuenta",
    "ACTUALIZACIÓN DE DATOS",
]


def build_query(
    processed_query_label: str,
    plugins: list[SourcePlugin] | None = None,
    *,
    base_query: str = "label:inbox",
    subject_exclusions: list[str] | None = None,
    query_hints_overrides: dict[str, QueryHintsOverride] | None = None,
) -> str:
    plugins = plugins or [
        definition.plugin for definition in builtin_plugins().values()
    ]
    query_hints_overrides = query_hints_overrides or {}

    positive_terms: list[str] = []
    plugin_subject_exclusions: list[str] = []
    for plugin in plugins:
        hints = query_hints_overrides.get(plugin.id, QueryHintsOverride()).apply(
            plugin.query_hints()
        )
        positive_terms.extend(_label_term(label) for label in hints.labels)
        positive_terms.extend(f'from:"{sender}"' for sender in hints.senders)
        positive_terms.extend(
            f'subject:"{subject}"' for subject in hints.subject_contains
        )
        plugin_subject_exclusions.extend(hints.subject_excludes)

    all_subject_exclusions = list(
        DEFAULT_SUBJECT_EXCLUSIONS if subject_exclusions is None else subject_exclusions
    )
    all_subject_exclusions.extend(plugin_subject_exclusions)
    parts = [base_query]
    unique_positive_terms = _dedupe(positive_terms)
    if unique_positive_terms:
        parts.append(_or_group(unique_positive_terms))
    parts.append(f"-{_label_term(processed_query_label)}")
    parts.extend(f'-subject:"{subject}"' for subject in _dedupe(all_subject_exclusions))
    return " ".join(part for part in parts if part)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export bank transaction emails from Gmail to MoneyWiz CSV"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Add the processed label and archive handled emails",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit how many matching emails to process",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Optional output CSV path"
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("secrets/credentials.json"),
        help="Path to Google OAuth client credentials",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=Path("secrets/token.json"),
        help="Path to the local OAuth token",
    )
    parser.add_argument(
        "--accounts",
        type=Path,
        default=Path("config/accounts.yaml"),
        help="Path to the YAML config with enabled plugins and account mappings",
    )
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=Path("exports"),
        help="Directory for generated CSV and summary files",
    )
    parser.add_argument(
        "--processed-label",
        default=DEFAULT_PROCESSED_LABEL,
        help="Exact Gmail label name to add after successful export",
    )
    parser.add_argument(
        "--processed-query-label",
        default=DEFAULT_PROCESSED_QUERY_LABEL,
        help="Gmail search label alias used in the query exclusion",
    )
    parser.add_argument(
        "--list-labels",
        action="store_true",
        help="List Gmail labels and exit",
    )
    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List available built-in and installed plugins and exit",
    )
    parser.add_argument(
        "--debug-skips",
        action="store_true",
        help="Include sender and a short text preview for skipped emails in the summary output",
    )
    parser.add_argument(
        "--no-default-subject-exclusions",
        action="store_true",
        help="Do not exclude known non-transaction email subjects from the Gmail query",
    )
    parser.add_argument(
        "--moneywiz-history",
        type=Path,
        default=None,
        help="MoneyWiz all-accounts CSV export used to infer Payee and Category defaults",
    )
    parser.add_argument(
        "--no-interactive-mapping",
        action="store_true",
        help="Use inferred MoneyWiz defaults without prompting for Payee/Category overrides",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_plugins:
        config = (
            AppConfig.from_file(args.accounts)
            if args.accounts.exists()
            else AppConfig.default()
        )
        enabled_plugins = set(config.enabled_plugins)
        for plugin_id, definition in discover_plugins().items():
            enabled_marker = "*" if plugin_id in enabled_plugins else " "
            print(
                f"{enabled_marker} {plugin_id} ({definition.source}) - {definition.plugin.display_name}"
            )
        return 0

    if not args.credentials.exists():
        raise SystemExit(f"Missing credentials file: {args.credentials}")
    if not args.accounts.exists():
        raise SystemExit(f"Missing config file: {args.accounts}")

    config = AppConfig.from_file(args.accounts)
    enabled_plugins = resolve_enabled_plugins(list(config.enabled_plugins))

    subject_exclusions = (
        [] if args.no_default_subject_exclusions else DEFAULT_SUBJECT_EXCLUSIONS
    )
    query = build_query(
        args.processed_query_label,
        enabled_plugins,
        base_query=config.query_base,
        subject_exclusions=subject_exclusions,
        query_hints_overrides=config.plugin_query_hints,
    )
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    csv_path = args.output or (args.exports_dir / f"transactions-{timestamp}.csv")
    summary_path = csv_path.with_suffix(".summary.json")

    mappings = AccountMappings.from_dict(config.accounts)
    gmail = GmailClient(args.credentials, args.token)

    if args.list_labels:
        for name in sorted(gmail.list_labels()):
            print(name)
        return 0

    message_ids = gmail.list_message_ids(query, args.limit)

    results: list[MessageResult] = []
    raw_csv_rows: list[dict[str, str]] = []
    ready_message_ids: list[str] = []

    for message_id in message_ids:
        message = gmail.get_message(message_id)
        result = process_message(
            message,
            mappings,
            plugins=enabled_plugins,
            include_debug_preview=args.debug_skips,
        )
        results.append(result)
        if result.status != "ready":
            continue
        raw_csv_rows.extend(result.rows or [])
        ready_message_ids.append(message_id)

    moneywiz_history = MoneyWizHistory.empty()
    moneywiz_history_path = (
        args.moneywiz_history.expanduser() if args.moneywiz_history else None
    )
    if moneywiz_history_path:
        if not moneywiz_history_path.exists():
            raise SystemExit(f"Missing MoneyWiz history CSV: {moneywiz_history_path}")
        moneywiz_history = MoneyWizHistory.from_csv(moneywiz_history_path)

    interactive_mapping = bool(
        moneywiz_history_path and not args.no_interactive_mapping and sys.stdin.isatty()
    )
    csv_rows = build_moneywiz_rows(
        raw_csv_rows,
        moneywiz_history,
        interactive=interactive_mapping,
    )
    missing_payee_category_rows = sum(
        1 for row in csv_rows if not row["payee"] or not row["category"]
    )

    csv_written = False
    if csv_rows:
        write_csv(csv_path, csv_rows)
        csv_written = True

    mutated = 0
    mutation_errors: list[dict[str, str]] = []
    if args.apply and csv_written:
        for message_id in ready_message_ids:
            try:
                gmail.mark_processed_and_archive(message_id, args.processed_label)
                mutated += 1
            except Exception as error:  # noqa: BLE001
                mutation_errors.append({"message_id": message_id, "error": str(error)})
    elif args.apply and not csv_written and ready_message_ids:
        mutation_errors.append(
            {
                "message_id": "run",
                "error": "Messages were ready but CSV was not written. No Gmail mutations applied.",
            }
        )

    skipped_reasons = Counter(
        result.reason for result in results if result.status == "skipped"
    )
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "enabled_plugins": [plugin.id for plugin in enabled_plugins],
        "query": query,
        "fetched_emails": len(message_ids),
        "ready_emails": len(ready_message_ids),
        "csv_rows_written": len(csv_rows),
        "csv_path": str(csv_path) if csv_written else None,
        "summary_path": str(summary_path),
        "moneywiz_history_path": str(moneywiz_history_path)
        if moneywiz_history_path
        else None,
        "interactive_mapping": interactive_mapping,
        "missing_payee_category_rows": missing_payee_category_rows,
        "gmail_mutations_applied": mutated,
        "skipped": sum(1 for result in results if result.status == "skipped"),
        "skipped_reasons": {
            reason or "Unknown": count for reason, count in skipped_reasons.items()
        },
        "mutation_errors": mutation_errors,
        "messages": [result.to_dict() for result in results],
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Mode: {summary['mode']}")
    print(f"Enabled plugins: {', '.join(summary['enabled_plugins']) or 'none'}")
    print(f"Fetched emails: {summary['fetched_emails']}")
    print(f"Ready emails: {summary['ready_emails']}")
    print(f"CSV rows written: {summary['csv_rows_written']}")
    print(f"Missing Payee/Category rows: {summary['missing_payee_category_rows']}")
    print(f"Gmail mutations applied: {summary['gmail_mutations_applied']}")
    print(f"Skipped: {summary['skipped']}")
    if csv_written:
        print(f"CSV: {csv_path}")
    print(f"Summary: {summary_path}")

    if summary["skipped_reasons"]:
        print("Skipped reasons:")
        for reason, count in summary["skipped_reasons"].items():
            print(f"- {count} x {reason}")

    if args.debug_skips:
        skipped_messages = [
            message for message in summary["messages"] if message["status"] == "skipped"
        ]
        if skipped_messages:
            print("Skipped message previews:")
            for message in skipped_messages:
                print(f"- {message['message_id']}: {message['subject']}")
                print(f"  sender: {message['sender']}")
                for line in message.get("debug_preview") or []:
                    print(f"  > {line}")

    if summary["mutation_errors"]:
        print("Mutation errors:")
        for error in summary["mutation_errors"]:
            print(f"- {error['message_id']}: {error['error']}")

    if not args.apply:
        print("Dry-run only. Re-run with --apply to label and archive ready emails.")
        return 0

    return 1 if summary["mutation_errors"] else 0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


def _label_term(label: str) -> str:
    if any(character.isspace() for character in label) or "/" in label:
        return f'label:"{label}"'
    return f"label:{label}"


def _or_group(terms: list[str]) -> str:
    if len(terms) == 1:
        return terms[0]
    return f"({' OR '.join(terms)})"
