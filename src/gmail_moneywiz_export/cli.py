from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from gmail_moneywiz_export.exporter import write_csv
from gmail_moneywiz_export.gmail_client import GmailClient
from gmail_moneywiz_export.mapping import AccountMappings
from gmail_moneywiz_export.processor import MessageResult, process_message

DEFAULT_PROCESSED_QUERY_LABEL = "banks-processed"
DEFAULT_PROCESSED_LABEL = "Banks/Processed"
DEFAULT_SUBJECT_EXCLUSIONS = [
    "Estado de cuenta",
    "ACTUALIZACIÓN DE DATOS",
]


def build_query(processed_query_label: str, subject_exclusions: list[str] | None = None) -> str:
    exclusion_terms = " ".join(
        f'-subject:"{subject}"' for subject in (subject_exclusions or DEFAULT_SUBJECT_EXCLUSIONS)
    )
    return " ".join(
        part
        for part in [
            "label:inbox",
            "(label:banks-scotiabank OR label:banks-bac OR label:banks-promerica)",
            f"-label:{processed_query_label}",
            exclusion_terms,
        ]
        if part
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export bank transaction emails from Gmail to MoneyWiz CSV")
    parser.add_argument("--apply", action="store_true", help="Add the processed label and archive handled emails")
    parser.add_argument("--limit", type=int, default=None, help="Limit how many matching emails to process")
    parser.add_argument("--output", type=Path, default=None, help="Optional output CSV path")
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
        help="Path to the account mapping YAML",
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
        "--debug-skips",
        action="store_true",
        help="Include sender and a short text preview for skipped emails in the summary output",
    )
    parser.add_argument(
        "--no-default-subject-exclusions",
        action="store_true",
        help="Do not exclude known non-transaction email subjects from the Gmail query",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.credentials.exists():
        raise SystemExit(f"Missing credentials file: {args.credentials}")
    if not args.accounts.exists():
        raise SystemExit(f"Missing account mapping file: {args.accounts}")

    subject_exclusions = [] if args.no_default_subject_exclusions else DEFAULT_SUBJECT_EXCLUSIONS
    query = build_query(args.processed_query_label, subject_exclusions)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    csv_path = args.output or (args.exports_dir / f"transactions-{timestamp}.csv")
    summary_path = csv_path.with_suffix(".summary.json")

    mappings = AccountMappings.from_file(args.accounts)
    gmail = GmailClient(args.credentials, args.token)

    if args.list_labels:
        for name in sorted(gmail.list_labels()):
            print(name)
        return 0

    message_ids = gmail.list_message_ids(query, args.limit)

    results: list[MessageResult] = []
    csv_rows: list[dict[str, str]] = []
    ready_message_ids: list[str] = []

    for message_id in message_ids:
        message = gmail.get_message(message_id)
        result = process_message(message, mappings, include_debug_preview=args.debug_skips)
        results.append(result)
        if result.status != "ready":
            continue
        csv_rows.extend(result.rows or [])
        ready_message_ids.append(message_id)

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

    skipped_reasons = Counter(result.reason for result in results if result.status == "skipped")
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "query": query,
        "fetched_emails": len(message_ids),
        "ready_emails": len(ready_message_ids),
        "csv_rows_written": len(csv_rows),
        "csv_path": str(csv_path) if csv_written else None,
        "summary_path": str(summary_path),
        "gmail_mutations_applied": mutated,
        "skipped": sum(1 for result in results if result.status == "skipped"),
        "skipped_reasons": {reason or "Unknown": count for reason, count in skipped_reasons.items()},
        "mutation_errors": mutation_errors,
        "messages": [result.to_dict() for result in results],
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Mode: {summary['mode']}")
    print(f"Fetched emails: {summary['fetched_emails']}")
    print(f"Ready emails: {summary['ready_emails']}")
    print(f"CSV rows written: {summary['csv_rows_written']}")
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
        skipped_messages = [message for message in summary["messages"] if message["status"] == "skipped"]
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
