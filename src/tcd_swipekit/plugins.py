"""Plugin & extensibility registry for TCD-Swipekit sources, slide layouts, and exporters."""

from __future__ import annotations

import importlib.metadata
import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tcd_swipekit.models import DeckSpec, SlideItem, ThemeConfig
    from tcd_swipekit.sources.base import BaseSource

LayoutContextBuilder = Callable[
    ["SlideItem", int, int, "ThemeConfig", int, int],
    dict[str, Any],
]
ExporterCallable = Callable[[list[Path], Path, "DeckSpec"], Path]


@dataclass(frozen=True)
class SourceRegistration:
    """Metadata for a registered content source provider."""

    name: str
    cls: type[BaseSource]
    description: str = ""
    builtin: bool = False


@dataclass(frozen=True)
class LayoutRegistration:
    """Metadata for a registered slide layout and its Jinja2 template."""

    name: str
    template: str
    description: str = ""
    context_builder: LayoutContextBuilder | None = None
    builtin: bool = False


@dataclass(frozen=True)
class ExporterRegistration:
    """Metadata for a registered post-render bundle exporter (e.g., PDF, GIF)."""

    name: str
    filename: str
    fn: ExporterCallable
    description: str = ""
    builtin: bool = False


_SOURCES: dict[str, SourceRegistration] = {}
_LAYOUTS: dict[str, LayoutRegistration] = {}
_EXPORTERS: dict[str, ExporterRegistration] = {}
_DISCOVERED = False


def register_source(
    name: str,
    cls: type[BaseSource] | None = None,
    *,
    description: str = "",
    builtin: bool = False,
) -> Any:
    """Register a BaseSource subclass by name (usable as a decorator or direct call)."""
    key = name.strip().lower()

    def _decorator(target_cls: type[BaseSource]) -> type[BaseSource]:
        _SOURCES[key] = SourceRegistration(
            name=key,
            cls=target_cls,
            description=description or (target_cls.__doc__ or "").strip().splitlines()[0]
            if target_cls.__doc__
            else "",
            builtin=builtin,
        )
        return target_cls

    if cls is not None:
        return _decorator(cls)
    return _decorator


def get_source_class(name: str) -> type[BaseSource]:
    """Return a registered BaseSource class by name."""
    ensure_builtin_registrations()
    key = name.strip().lower()
    if key not in _SOURCES:
        available = ", ".join(sorted(_SOURCES))
        raise KeyError(f"Unknown content source '{name}'. Registered sources: {available}")
    return _SOURCES[key].cls


def list_sources() -> dict[str, SourceRegistration]:
    """Return all registered content sources."""
    ensure_builtin_registrations()
    return dict(sorted(_SOURCES.items()))


def register_layout(
    name: str,
    *,
    template: str | None = None,
    context_builder: LayoutContextBuilder | None = None,
    description: str = "",
    builtin: bool = False,
) -> Any:
    """Register a slide layout variant (usable as a decorator on a context_builder or direct call)."""
    key = name.strip().lower()
    resolved_template = template or f"slide_{key}.html.j2"

    def _decorator(fn: LayoutContextBuilder) -> LayoutContextBuilder:
        _LAYOUTS[key] = LayoutRegistration(
            name=key,
            template=resolved_template,
            description=description or (fn.__doc__ or "").strip(),
            context_builder=fn,
            builtin=builtin,
        )
        return fn

    if context_builder is not None:
        _decorator(context_builder)
        return _LAYOUTS[key]

    # Allow registering a template-only layout without a custom Python callback
    _LAYOUTS[key] = LayoutRegistration(
        name=key,
        template=resolved_template,
        description=description,
        context_builder=None,
        builtin=builtin,
    )
    return _decorator


def get_layout(name: str) -> LayoutRegistration | None:
    """Lookup a registered slide layout by name."""
    ensure_builtin_registrations()
    return _LAYOUTS.get(name.strip().lower())


def list_layouts() -> dict[str, LayoutRegistration]:
    """Return all registered slide layouts."""
    ensure_builtin_registrations()
    return dict(sorted(_LAYOUTS.items()))


def register_exporter(
    name: str,
    fn: ExporterCallable | None = None,
    *,
    filename: str | None = None,
    description: str = "",
    builtin: bool = False,
) -> Any:
    """Register a post-render slide exporter (usable as a decorator or direct call)."""
    key = name.strip().lower()
    default_filename = filename or f"carousel.{key}"

    def _decorator(target_fn: ExporterCallable) -> ExporterCallable:
        _EXPORTERS[key] = ExporterRegistration(
            name=key,
            filename=default_filename,
            fn=target_fn,
            description=description or (target_fn.__doc__ or "").strip().splitlines()[0]
            if target_fn.__doc__
            else "",
            builtin=builtin,
        )
        return target_fn

    if fn is not None:
        return _decorator(fn)
    return _decorator


def get_exporter(name: str) -> ExporterRegistration:
    """Lookup a registered exporter by name."""
    ensure_builtin_registrations()
    key = name.strip().lower()
    if key not in _EXPORTERS:
        available = ", ".join(sorted(_EXPORTERS))
        raise KeyError(f"Unknown exporter '{name}'. Registered exporters: {available}")
    return _EXPORTERS[key]


def list_exporters() -> dict[str, ExporterRegistration]:
    """Return all registered exporters."""
    ensure_builtin_registrations()
    return dict(sorted(_EXPORTERS.items()))


def load_plugin_file(path: Path | str) -> None:
    """Dynamically load a standalone Python plugin file that calls `register_*` helpers."""
    plugin_path = Path(path).expanduser().resolve()
    if not plugin_path.is_file():
        raise FileNotFoundError(f"Plugin file not found: {path}")
    module_name = f"tcd_swipekit_user_plugin_{plugin_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load Python plugin from {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def discover_external_plugins() -> None:
    """Discover installed Python entry-point plugins and user `~/.config/swipekit/plugins/*.py`."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True

    # 1. Python package entry points
    for group in ("tcd_swipekit.plugins", "tcd_swipekit.sources", "tcd_swipekit.layouts", "tcd_swipekit.exporters"):
        try:
            eps = importlib.metadata.entry_points(group=group)
        except Exception:
            eps = ()  # type: ignore[assignment]
        for ep in eps:
            try:
                loaded = ep.load()
                if group == "tcd_swipekit.sources" and isinstance(loaded, type):
                    register_source(ep.name, loaded)
                elif group == "tcd_swipekit.exporters" and callable(loaded):
                    register_exporter(ep.name, loaded)
                elif callable(loaded):
                    loaded()
            except Exception:
                continue

    # 2. User global plugins directory (~/.config/swipekit/plugins/*.py)
    global_plugin_dir = Path.home() / ".config" / "swipekit" / "plugins"
    if global_plugin_dir.is_dir():
        for py_file in sorted(global_plugin_dir.glob("*.py")):
            try:
                load_plugin_file(py_file)
            except Exception:
                continue


def ensure_builtin_registrations() -> None:
    """Ensure all built-in sources, layouts, and exporters are registered and plugins discovered."""
    if not _SOURCES:
        from tcd_swipekit.sources.github import GitHubSource
        from tcd_swipekit.sources.manual import ManualDeckSource
        from tcd_swipekit.sources.markdown import MarkdownSource
        from tcd_swipekit.sources.website import WebsiteSource

        register_source(
            "github",
            GitHubSource,
            description="GitHub Trending & topic search with smart README screenshot extraction",
            builtin=True,
        )
        register_source(
            "website",
            WebsiteSource,
            description="Auto-captured live desktop screenshots & OpenGraph metadata from sites.yml",
            builtin=True,
        )
        register_source(
            "markdown",
            MarkdownSource,
            description="Convert Markdown articles, tutorials, or docs into multi-layout slide decks",
            builtin=True,
        )
        register_source(
            "manual",
            ManualDeckSource,
            description="Hybrid YAML deck loader with automatic GitHub & website enrichment",
            builtin=True,
        )

    if not _LAYOUTS or not _EXPORTERS:
        from tcd_swipekit.renderer import register_builtin_layouts_and_exporters

        register_builtin_layouts_and_exporters()

    discover_external_plugins()
