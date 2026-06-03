# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

import io
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

from neogit.init.render import build_init_summary, render_init_summary


def _fake_settings(provider, key=None, host=None, container_name="neogit"):
    """Duck-typed stand-in for dynaconf settings: the builder only reads these attrs."""
    return SimpleNamespace(
        neo4j=SimpleNamespace(url="bolt://localhost:7687"),
        object=SimpleNamespace(provider=provider, key=key, host=host, container_name=container_name),
    )


def _render_plain(summary) -> str:
    """Render through a non-TTY Console so styling is stripped to plain text."""
    buffer = io.StringIO()
    Console(file=buffer).print(render_init_summary(summary))
    return buffer.getvalue()


def test_build_local_uses_key_as_location():
    summary = build_init_summary(_fake_settings("local", key="/data/neogit"))
    assert summary.neo4j_url == "bolt://localhost:7687"
    assert summary.provider == "local"
    assert summary.location == "/data/neogit"
    assert summary.container_name == "neogit"


def test_build_minio_uses_host_as_location():
    summary = build_init_summary(_fake_settings("minio", host="127.0.0.1"))
    assert summary.provider == "minio"
    assert summary.location == "127.0.0.1"


def test_render_local_contains_url_provider_path_and_ready_lines():
    out = _render_plain(build_init_summary(_fake_settings("local", key="/data/neogit")))
    assert "bolt://localhost:7687" in out
    assert "local" in out
    assert "/data/neogit" in out
    assert "Graph constraints ready" in out
    assert "Object container ready: neogit" in out


def test_render_minio_contains_host():
    out = _render_plain(build_init_summary(_fake_settings("minio", host="127.0.0.1")))
    assert "minio" in out
    assert "127.0.0.1" in out


def test_render_omits_parenthetical_when_location_is_none():
    out = _render_plain(build_init_summary(_fake_settings("s3", host=None)))
    assert "s3" in out
    assert "(" not in out.split("Object store")[1].split("\n")[0]


def test_build_local_coerces_path_key_to_str():
    summary = build_init_summary(_fake_settings("local", key=Path("/data/neogit")))
    assert summary.location == "/data/neogit"
    assert isinstance(summary.location, str)


def test_markup_in_container_name_is_escaped():
    summary = build_init_summary(_fake_settings("local", key="/data/neogit", container_name="[red]neogit[/]"))
    out = _render_plain(summary)
    assert "[red]neogit[/]" in out
