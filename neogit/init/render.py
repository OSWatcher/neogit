# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""Human-friendly summary of `neogit init` for the CLI.

`init` is otherwise silent. After creating the graph constraints and the object
container, the service returns an :class:`InitSummary` describing the backends it
used; the CLI renders it with Rich. Returning a renderable (not a string) lets
the CLI own the ``rich.console.Console`` so color shows on a TTY and is stripped
when piped. Only non-secret connection details are included.
"""

from dataclasses import dataclass
from typing import Optional

from dynaconf import LazySettings
from rich.console import Group, RenderableType
from rich.markup import escape
from rich.text import Text


@dataclass
class InitSummary:
    """Non-secret description of the backends `neogit init` connected to."""

    neo4j_url: str
    provider: str
    location: Optional[str]
    container_name: str


def build_init_summary(settings: LazySettings) -> InitSummary:
    """Read the active settings into an InitSummary (no secrets included)."""
    provider = settings.object.provider
    location = settings.object.key if provider == "local" else settings.object.host
    return InitSummary(
        neo4j_url=settings.neo4j.url,
        provider=provider,
        location=location,
        container_name=settings.object.container_name,
    )


def render_init_summary(summary: InitSummary) -> RenderableType:
    """Return a Rich renderable summarizing the initialized backends."""
    store = f"[bold]Object store[/] {escape(summary.provider)}"
    if summary.location:
        store += f"  ([dim]{escape(str(summary.location))}[/])"
    return Group(
        Text.from_markup(f"[bold]Neo4j[/]        {escape(summary.neo4j_url)}"),
        Text.from_markup(store),
        Text(""),
        Text.from_markup("[green]✓[/] Graph constraints ready"),
        Text.from_markup(f"[green]✓[/] Object container ready: {escape(summary.container_name)}"),
    )
