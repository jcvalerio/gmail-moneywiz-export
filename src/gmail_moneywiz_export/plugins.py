from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Any, Protocol, runtime_checkable

from gmail_moneywiz_export.models import GmailMessage, Transaction

PLUGIN_ENTRY_POINT_GROUP = "gmail_moneywiz_export.plugins"


class PluginError(ValueError):
    pass


@dataclass(frozen=True)
class QueryHints:
    labels: tuple[str, ...] = ()
    senders: tuple[str, ...] = ()
    subject_contains: tuple[str, ...] = ()
    subject_excludes: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryHintsOverride:
    labels: tuple[str, ...] | None = None
    senders: tuple[str, ...] | None = None
    subject_contains: tuple[str, ...] | None = None
    subject_excludes: tuple[str, ...] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "QueryHintsOverride":
        data = data or {}
        return cls(
            labels=_tuple_or_none(data.get("labels")),
            senders=_tuple_or_none(data.get("senders")),
            subject_contains=_tuple_or_none(data.get("subject_contains")),
            subject_excludes=_tuple_or_none(data.get("subject_excludes")),
        )

    def apply(self, hints: QueryHints) -> QueryHints:
        return QueryHints(
            labels=self.labels if self.labels is not None else hints.labels,
            senders=self.senders if self.senders is not None else hints.senders,
            subject_contains=self.subject_contains
            if self.subject_contains is not None
            else hints.subject_contains,
            subject_excludes=self.subject_excludes
            if self.subject_excludes is not None
            else hints.subject_excludes,
        )


@runtime_checkable
class SourcePlugin(Protocol):
    id: str
    display_name: str
    priority: int

    def query_hints(self) -> QueryHints: ...

    def match_score(self, message: GmailMessage) -> int: ...

    def parse(self, message: GmailMessage) -> list[Transaction]: ...


@dataclass(frozen=True)
class PluginDefinition:
    plugin: SourcePlugin
    source: str


@dataclass(frozen=True)
class ResolvedPluginMatch:
    plugin: SourcePlugin
    score: int


def builtin_plugins() -> dict[str, PluginDefinition]:
    from gmail_moneywiz_export.parsers.bac import BacPlugin
    from gmail_moneywiz_export.parsers.promerica import PromericaPlugin
    from gmail_moneywiz_export.parsers.scotia import ScotiaPlugin

    return {
        "bac": PluginDefinition(plugin=BacPlugin(), source="built-in"),
        "promerica": PluginDefinition(plugin=PromericaPlugin(), source="built-in"),
        "scotia": PluginDefinition(plugin=ScotiaPlugin(), source="built-in"),
    }


def default_enabled_plugin_ids() -> tuple[str, ...]:
    return tuple(sorted(builtin_plugins().keys()))


def discover_plugins() -> dict[str, PluginDefinition]:
    plugins = dict(builtin_plugins())
    for plugin_entry_point in entry_points(group=PLUGIN_ENTRY_POINT_GROUP):
        plugin = _load_entry_point_plugin(plugin_entry_point)
        if plugin.id in plugins:
            existing = plugins[plugin.id]
            raise PluginError(
                f"Duplicate plugin id '{plugin.id}' from {plugin_entry_point.value}. Already provided by {existing.source}."
            )
        plugins[plugin.id] = PluginDefinition(
            plugin=plugin, source=f"entry point: {plugin_entry_point.value}"
        )
    return dict(sorted(plugins.items()))


def resolve_enabled_plugins(
    enabled_plugin_ids: list[str] | tuple[str, ...],
) -> list[SourcePlugin]:
    available_plugins = discover_plugins()
    missing_plugins = [
        plugin_id
        for plugin_id in enabled_plugin_ids
        if plugin_id not in available_plugins
    ]
    if missing_plugins:
        available = ", ".join(sorted(available_plugins)) or "none"
        missing = ", ".join(missing_plugins)
        raise PluginError(
            f"Unknown enabled plugin(s): {missing}. Available plugins: {available}"
        )
    return [available_plugins[plugin_id].plugin for plugin_id in enabled_plugin_ids]


def pick_plugin(
    message: GmailMessage, plugins: list[SourcePlugin]
) -> ResolvedPluginMatch | None:
    matches = [
        ResolvedPluginMatch(plugin=plugin, score=score)
        for plugin in plugins
        if (score := plugin.match_score(message)) > 0
    ]
    if not matches:
        return None

    matches.sort(
        key=lambda match: (match.score, match.plugin.priority, match.plugin.id),
        reverse=True,
    )
    if len(matches) > 1:
        first = matches[0]
        second = matches[1]
        if (
            first.score == second.score
            and first.plugin.priority == second.plugin.priority
        ):
            raise PluginError(
                f"Ambiguous plugin match: {first.plugin.id} and {second.plugin.id} both matched message {message.message_id}"
            )
    return matches[0]


def _load_entry_point_plugin(plugin_entry_point: EntryPoint) -> SourcePlugin:
    try:
        loaded = plugin_entry_point.load()
    except Exception as error:  # noqa: BLE001
        raise PluginError(
            f"Could not load plugin from {plugin_entry_point.value}: {error}"
        ) from error

    plugin = _coerce_plugin(loaded)
    _validate_plugin(plugin, source=plugin_entry_point.value)
    return plugin


def _coerce_plugin(loaded: Any) -> SourcePlugin:
    if _looks_like_plugin(loaded):
        return loaded
    if isinstance(loaded, type):
        instance = loaded()
        if _looks_like_plugin(instance):
            return instance
    if callable(loaded):
        instance = loaded()
        if _looks_like_plugin(instance):
            return instance
    raise PluginError(
        "Plugin entry point must resolve to a plugin instance, no-arg class, or no-arg factory"
    )


def _validate_plugin(plugin: SourcePlugin, source: str) -> None:
    if not plugin.id:
        raise PluginError(f"Plugin from {source} is missing an id")
    if not isinstance(plugin.priority, int):
        raise PluginError(
            f"Plugin '{plugin.id}' from {source} has a non-integer priority"
        )
    hints = plugin.query_hints()
    if not isinstance(hints, QueryHints):
        raise PluginError(
            f"Plugin '{plugin.id}' from {source} returned invalid query hints"
        )


def _looks_like_plugin(value: Any) -> bool:
    return all(
        hasattr(value, attribute)
        for attribute in [
            "id",
            "display_name",
            "priority",
            "query_hints",
            "match_score",
            "parse",
        ]
    )


def _tuple_or_none(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)
