from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rapidfuzz import fuzz


@dataclass(frozen=True)
class PayeeCategoryAssignment:
    payee: str
    category: str


class MoneyWizHistory:
    def __init__(
        self,
        merchant_mappings: dict[str, Counter[tuple[str, str]]],
        payee_categories: dict[str, Counter[str]],
        payees: dict[str, Counter[str]],
        categories: dict[str, Counter[str]],
    ):
        self._merchant_mappings = merchant_mappings
        self._payee_categories = payee_categories
        self._payees = payees
        self._categories = categories

    @classmethod
    def empty(cls) -> "MoneyWizHistory":
        return cls({}, {}, {}, {})

    @classmethod
    def from_csv(cls, path: Path) -> "MoneyWizHistory":
        merchant_mappings: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
        payee_categories: dict[str, Counter[str]] = defaultdict(Counter)
        payees: dict[str, Counter[str]] = defaultdict(Counter)
        categories: dict[str, Counter[str]] = defaultdict(Counter)

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            first_line = file.readline()
            if not first_line.startswith("sep="):
                file.seek(0)
            reader = csv.DictReader(file)
            for row in reader:
                payee = _clean_csv_value(row.get("Payee", ""))
                category = _clean_csv_value(row.get("Category", ""))
                if payee:
                    payees[_normalize_key(payee)][payee] += 1
                if category:
                    categories[_normalize_key(category)][category] += 1
                if payee and category:
                    payee_categories[_normalize_key(payee)][category] += 1
                    for merchant_field in ("Description", "Memo"):
                        merchant = _clean_csv_value(row.get(merchant_field, ""))
                        if merchant:
                            merchant_mappings[_normalize_key(merchant)][
                                (payee, category)
                            ] += 1

        return cls(
            dict(merchant_mappings),
            dict(payee_categories),
            dict(payees),
            dict(categories),
        )

    def default_for_merchant(self, merchant: str) -> PayeeCategoryAssignment | None:
        counter = self._merchant_mappings.get(_normalize_key(merchant))
        if counter:
            (payee, category), _count = counter.most_common(1)[0]
            return PayeeCategoryAssignment(payee=payee, category=category)

        payee = self.suggest_payee_for_merchant(merchant)
        if payee is None:
            return None
        return PayeeCategoryAssignment(
            payee=payee,
            category=self.default_category_for_payee(payee) or "",
        )

    def suggest_payee_for_merchant(self, merchant: str) -> str | None:
        matches = _search_values(
            merchant,
            self._payees.values(),
            limit=1,
            min_score=88,
            min_value_length=5,
        )
        return matches[0] if matches else None

    def default_category_for_payee(self, payee: str) -> str | None:
        categories = self.categories_for_payee(payee, limit=1)
        return categories[0] if categories else None

    def categories_for_payee(self, payee: str, limit: int = 10) -> list[str]:
        counter = self._payee_categories.get(_normalize_key(payee))
        if not counter:
            return []
        return [category for category, _count in counter.most_common(limit)]

    def resolve_payee(self, payee: str) -> str | None:
        counter = self._payees.get(_normalize_key(payee))
        if not counter:
            return None
        value, _count = counter.most_common(1)[0]
        return value

    def resolve_category(self, category: str) -> str | None:
        counter = self._categories.get(_normalize_key(category))
        if not counter:
            return None
        value, _count = counter.most_common(1)[0]
        return value

    def search_payees(self, query: str, limit: int = 10) -> list[str]:
        return _search_values(query, self._payees.values(), limit)

    def search_categories(self, query: str, limit: int = 10) -> list[str]:
        return _search_values(query, self._categories.values(), limit)


def build_moneywiz_rows(
    rows: Iterable[dict[str, str]],
    history: MoneyWizHistory | None = None,
    *,
    interactive: bool = False,
) -> list[dict[str, str]]:
    history = history or MoneyWizHistory.empty()
    assignments: dict[str, PayeeCategoryAssignment] = {}
    moneywiz_rows: list[dict[str, str]] = []

    for row in rows:
        merchant = row.get("merchant", "")
        key = _normalize_key(merchant)
        if key not in assignments:
            default = history.default_for_merchant(merchant)
            assignments[key] = (
                _prompt_assignment(merchant, history, default)
                if interactive
                else default or PayeeCategoryAssignment(payee="", category="")
            )
        assignment = assignments[key]
        moneywiz_rows.append(
            {
                "account": row.get("account", ""),
                "date": row.get("date", ""),
                "amount": row.get("amount", ""),
                "payee": assignment.payee,
                "category": assignment.category,
                "memo": merchant,
                "currency": row.get("currency", ""),
            }
        )

    return moneywiz_rows


def _prompt_assignment(
    merchant: str,
    history: MoneyWizHistory,
    default: PayeeCategoryAssignment | None,
) -> PayeeCategoryAssignment:
    print(f"\nMerchant: {merchant}")
    payee = _prompt_existing_value(
        label="Payee",
        default=default.payee if default else None,
        resolve=history.resolve_payee,
        search=history.search_payees,
    )
    category_default = (
        default.category
        if default and _normalize_key(default.payee) == _normalize_key(payee)
        else history.default_category_for_payee(payee)
    )
    category_options = history.categories_for_payee(payee)
    if len(category_options) > 1:
        print("Possible categories for this Payee:")
        for category in category_options:
            print(f"- {_display_value(category)}")
    category = _prompt_existing_value(
        label="Category",
        default=category_default,
        resolve=history.resolve_category,
        search=history.search_categories,
    )
    return PayeeCategoryAssignment(payee=payee, category=category)


def _prompt_existing_value(
    *,
    label: str,
    default: str | None,
    resolve,
    search,
) -> str:
    while True:
        prompt = f"{label} [{_display_value(default)}]: " if default else f"{label}: "
        response = input(prompt).strip()
        if not response and default:
            return default
        if response.startswith("?"):
            matches = search(response[1:].strip())
            selection = _prompt_match_selection(label, matches)
            if selection:
                return selection
            continue
        resolved = resolve(response)
        if resolved:
            return resolved
        print(f"Unknown {label}. Type an existing {label}, or use ?text to search.")


def _prompt_match_selection(label: str, matches: list[str]) -> str | None:
    if not matches:
        print(f"No existing {label.lower()} matches.")
        return None

    print(f"Existing {label.lower()} matches:")
    for index, match in enumerate(matches, start=1):
        print(f"{index}. {_display_value(match)}")

    while True:
        response = input(
            f"Select {label} number, or press Enter to keep typing: "
        ).strip()
        if not response:
            return None
        if response.isdigit() and 1 <= int(response) <= len(matches):
            return matches[int(response) - 1]
        print(f"Type a number from 1 to {len(matches)}, or press Enter.")


def _search_values(
    query: str,
    counters: Iterable[Counter[str]],
    limit: int,
    *,
    min_score: float = 70,
    min_value_length: int = 1,
) -> list[str]:
    normalized_query = _fuzzy_key(query)
    if not normalized_query:
        return []

    matches: list[tuple[float, float, int, str]] = []
    for counter in counters:
        value, count = counter.most_common(1)[0]
        normalized_value = _fuzzy_key(value)
        if len(normalized_value) < min_value_length:
            continue
        score = _fuzzy_score(normalized_query, normalized_value)
        if score >= min_score:
            coverage = _fuzzy_coverage(normalized_query, normalized_value)
            matches.append((score, coverage, count, value))
    matches.sort(
        key=lambda match: (-match[0], -match[1], -match[2], _display_value(match[3]))
    )
    return [value for _score, _coverage, _count, value in matches[:limit]]


def _clean_csv_value(value: str | None) -> str:
    return (value or "").strip()


def _normalize_key(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split()).casefold()


def _fuzzy_key(value: str) -> str:
    normalized = _normalize_key(value)
    normalized = re.sub(r"[^\w\s]+", " ", normalized)
    return " ".join(normalized.split())


def _fuzzy_score(query: str, value: str) -> float:
    if query in value or value in query:
        return 100
    return max(
        fuzz.WRatio(query, value),
        fuzz.token_set_ratio(query, value),
    )


def _fuzzy_coverage(query: str, value: str) -> float:
    shorter_length = min(len(query), len(value))
    longer_length = max(len(query), len(value))
    return shorter_length / longer_length if longer_length else 0


def _display_value(value: str | None) -> str:
    return (value or "").replace("\xa0", " ")
