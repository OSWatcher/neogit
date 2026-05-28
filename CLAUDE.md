# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repository.
Keep this file lean and operational — deep reference lives in the `docs/`
MkDocs site and `README.md`. Update it when conventions or commands change.

## What neogit is

A Git-like tool backed by Neo4j: it builds content-addressed Merkle trees of
filesystem snapshots, storing the graph (Commit / Branch / Tree / Blob) in Neo4j
and raw file bytes (keyed by SHA-1) in pluggable object storage — local FS,
MinIO, or S3 via Apache Libcloud. Python 3.10+, Poetry, neomodel ORM, Dynaconf
config, docopt CLI.

It is used both as a **CLI** to capture filesystems (e.g. in OSWatcher) and as a
**library** that downstream projects extend with their own graph nodes attached
to a `Commit`.

## Essential commands

Everything runs through `poe` (poethepoet):

```bash
# Setup
poetry install                  # core deps
poetry install --with docs      # + docs toolchain (optional group)
poetry run poe create_dbs       # create Neo4j + MinIO test containers
poetry run poe start_dbs        # start existing containers
poetry run poe destroy_dbs      # remove containers

# Quality — run before every commit
poetry run poe ccode            # fmt + lint + type (black, flake8/isort, mypy)

# Tests
poetry run poe unit_test        # fast, FakeObjectStorage, no Docker
poetry run poe integration_test # needs Docker (Neo4j + MinIO)
poetry run poe test             # everything, with coverage
poetry run pytest -v tests/unit/test_x.py::test_y   # a single test
pytest --persistdb              # keep containers between runs
pytest --externdb               # use external DBs (CI)

# Docs (MkDocs Material)
poetry run poe docs_serve       # live preview
poetry run poe docs_build       # strict build (must pass)

# Run the CLI
neogit init                     # create Neo4j constraints + storage bucket
neogit commit <name> -r <path>
neogit commit <name> branch <branch> -r <path>
neogit branch <name> <commit-hash>   # resolves by SHA-1 hash, not name
```

## Conventions — follow these

- **Quality gate:** run `poetry run poe ccode` before committing. Black (line
  length 120), flake8 + isort, mypy. mypy is *not* fully strict
  (`disallow_untyped_defs = false`), but prefer type annotations on new code.
- **License headers:** the project is Apache 2.0. Every new source file under
  `neogit/` starts with this header, above the module docstring:
  ```python
  # Copyright 2021-2026 Mathieu Tarral
  # SPDX-License-Identifier: Apache-2.0
  ```
  Vendored fixtures under `tests/data/` are exempt — never relicense third-party code.
- **Commits:** Conventional Commits — `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- **Pull requests:** keep them small and single-purpose (one concern per PR).

## Repository map

- `neogit/service/neogit.py` — the main `Neogit` API (`commit`, `create_branch`,
  `filesystem_search`, object download). `cypher_query_with_backoff` wraps
  `db.cypher_query` with deadlock retry and a **required** `params` arg.
- `neogit/model/neo.py` — neomodel ORM nodes: `Commit`, `Branch`, `Tree`, `Blob`, `PluginRun`.
- `neogit/core/` — filesystem node model + Merkle visitor (`core/merkle/filesystem.py`).
- `neogit/merkle/` — Merkle tree builder + `hasher.py` (canonical Tree/Commit serialization).
- `neogit/object_storage/` — storage abstraction: `fake`, `lib_cloud`, `thread_safe` wrapper.
- `neogit/config/` — Dynaconf settings.
- `neogit/entrypoint/cmdline.py` — docopt CLI; the module `__doc__` *is* the usage spec.
- `neogit/diff/`, `neogit/search/`, `neogit/console/` — diff helpers, filesystem search, rich progress GUI.
- `neogit/testing/fixtures.py` — all pytest fixtures (single source of truth).

Design rationale and the full data model: `docs/explanation/` and `docs/reference/data-model.md`.

## Configuration

Dynaconf merges sources, highest precedence first: `NEOGIT_`-prefixed env vars →
`neogit/config/.secrets.toml` → `settings.toml` → `default_settings.toml`.
Nested keys use `__`, e.g. `NEOGIT_NEO4J__HOST`, `NEOGIT_OBJECT__PROVIDER`.
Defaults: Neo4j at `bolt://localhost:7687`, local object storage (no extra
config needed). Full table: `docs/reference/configuration.md`.

## Testing notes

- Fixtures are centralized in `neogit/testing/fixtures.py`, auto-imported by
  `tests/conftest.py`. Common ones: `neogit_init` (initialized service),
  `init_fake_object_storage` (in-memory, fast), `clean_neo4j_db` /
  `clean_minio_db`. The `neogit` fixture is parameterized across storage
  backends and worker counts, so a test using it runs many times.
- Layout: `tests/unit/` (fast, `FakeObjectStorage`), `tests/integration/`
  (needs Docker), `tests/bench/` (benchmarks), `tests/dev/` (skipped unless
  `-m dev`), `tests/data/` (vendored sample filesystems; excluded from
  formatting and coverage).

## Gotchas

- The CLI drops into an **ipdb post-mortem** on any unhandled exception
  (`post_mortem` decorator in `cmdline.py`). Pass `--debug` for stack traces and
  logging (config in `neogit/logging.yaml`).
- Integration/bench tests need running Neo4j + MinIO containers. If they hang or
  error, reset with `poetry run poe destroy_dbs && poetry run poe create_dbs`.
  Persistent container names: `neogit_neo4j_testdb`, `neogit_minio_testdb`.
  Neo4j browser: http://localhost:7474 · MinIO console: http://localhost:9001.
- `neogit diff <ref1> <ref2>` is declared in the CLI usage but `Neogit.diff()`
  is not implemented yet — the command currently raises. Don't assume it works.
- A `Commit`'s identity hash is `name + date + tree_sha1` (see `merkle/hasher.py`);
  `name` is **not** unique, only `hash`/`sha1sum` are.
