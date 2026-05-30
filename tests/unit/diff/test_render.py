# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

import io
from pathlib import Path

import pytest
from rich.console import Console

from neogit.diff.render import render_diff_line
from neogit.model import DiffStatus, FSDiffObject


def _obj(status: DiffStatus, path: str = "/fs/jffs2/acl.c") -> FSDiffObject:
    return FSDiffObject(status, False, Path(path), "old1234", "new5678")


@pytest.mark.parametrize(
    "status, expected",
    [
        (DiffStatus.NEW, "[green]A[/]  /fs/jffs2/acl.c"),
        (DiffStatus.MOD, "[yellow]M[/]  /fs/jffs2/acl.c"),
        (DiffStatus.DEL, "[red]D[/]  /fs/jffs2/acl.c"),
        (DiffStatus.TYP, "[cyan]T[/]  /fs/jffs2/acl.c"),
    ],
)
def test_render_diff_line_markup(status, expected):
    assert render_diff_line(_obj(status)) == expected


def test_render_diff_line_escapes_brackets_in_path():
    # A filename containing '[...]' must not be parsed as Rich markup.
    line = render_diff_line(_obj(DiffStatus.NEW, "/weird [1].txt"))
    assert line == "[green]A[/]  /weird \\[1].txt"


def test_render_diff_line_plain_when_not_a_tty():
    # A Console writing to a StringIO is not a terminal, so Rich strips all
    # styling -> piped output is clean, greppable plain text with the real path.
    buffer = io.StringIO()
    console = Console(file=buffer)
    console.print(render_diff_line(_obj(DiffStatus.MOD)))
    console.print(render_diff_line(_obj(DiffStatus.NEW, "/weird [1].txt")))
    assert buffer.getvalue() == "M  /fs/jffs2/acl.c\nA  /weird [1].txt\n"
