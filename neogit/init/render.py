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
from typing import List, Optional

from dynaconf import LazySettings
from rich.console import Group, RenderableType
from rich.markup import escape
from rich.panel import Panel
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
    location = str(settings.object.key) if provider == "local" else settings.object.host
    return InitSummary(
        neo4j_url=settings.neo4j.url,
        provider=provider,
        location=location,
        container_name=settings.object.container_name,
    )


def render_init_summary(summary: InitSummary) -> RenderableType:
    """Return one Rich panel per backend (Neo4j, object storage).

    Each panel groups a backend's connection detail with its readiness line, so
    the output reads as two self-contained blocks. Panels size to their content
    and the title carries the provider/name.
    """
    neo4j_panel = Panel(
        Group(
            Text(summary.neo4j_url),
            Text.from_markup("[green]✓[/] Graph constraints ready"),
        ),
        title="Neo4j",
        title_align="left",
        expand=False,
    )
    store_body: List[Text] = []
    if summary.location:
        store_body.append(Text(summary.location))
    store_body.append(Text.from_markup(f"[green]✓[/] Container ready: {escape(summary.container_name)}"))
    store_panel = Panel(
        Group(*store_body),
        title=f"Object storage ([bold]{escape(summary.provider)}[/])",
        title_align="left",
        expand=False,
    )
    return Group(neo4j_panel, store_panel)
