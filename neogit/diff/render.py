# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""Human-friendly rendering of a single FSDiffObject for the CLI.

Output is git ``--name-status`` style: a status letter, two spaces, then the
path. The returned string is Rich markup, so a ``rich.console.Console`` shows
color on a TTY and prints plain text when the output is piped or redirected.
The path is escaped so bracket characters in filenames are not parsed as
Rich markup tags.
"""

from neogit.model import DiffStatus, FSDiffObject

# Map each diff status to its git-style letter and Rich color.
_STATUS_STYLE: dict[DiffStatus, tuple[str, str]] = {
    DiffStatus.NEW: ("A", "green"),
    DiffStatus.MOD: ("M", "yellow"),
    DiffStatus.DEL: ("D", "red"),
    DiffStatus.TYP: ("T", "cyan"),
}


def _escape_path(path: str) -> str:
    """Escape all ``[`` characters in a path so they are not parsed as Rich markup tags."""
    return path.replace("[", "\\[")


def render_diff_line(obj: FSDiffObject) -> str:
    """Return Rich markup for one file diff, e.g. ``"[green]A[/]  /path"``."""
    letter, color = _STATUS_STYLE[obj.status]
    return f"[{color}]{letter}[/]  {_escape_path(str(obj.path))}"
