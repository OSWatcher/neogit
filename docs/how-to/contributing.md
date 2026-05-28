# Contribute

## Set up

```bash
git clone https://github.com/OSWatcher/neogit.git
cd neogit
poetry install
poetry run poe create_dbs
```

## Day-to-day commands

```bash
poetry run poe fmt          # black
poetry run poe lint         # flake8 + isort
poetry run poe type         # mypy (strict)
poetry run poe ccode        # fmt + lint + type, run all three
poetry run poe unit_test    # unit tests only
poetry run poe integration_test
poetry run poe test         # everything with coverage
```

Run `poetry run poe ccode` before opening a PR — CI will reject anything that doesn't pass.

## Test database lifecycle

```bash
poetry run poe create_dbs    # spin up Neo4j + MinIO
poetry run poe start_dbs     # start existing containers
poetry run poe shutdown_dbs  # stop, preserve data
poetry run poe destroy_dbs   # delete containers
```

For faster iteration on a specific test:

```bash
pytest -v --persistdb tests/integration/test_commit.py::test_commit_simple
```

`--persistdb` keeps containers between runs.

## Project layout

- `neogit/service/` — top-level `Neogit` class, the public API
- `neogit/model/` — neomodel ORM classes for the graph
- `neogit/core/` — Merkle tree computation (visitor pattern over filesystem nodes)
- `neogit/object_storage/` — pluggable storage backends (fake / libcloud / thread-safe wrapper)
- `neogit/config/` — Dynaconf-based settings
- `neogit/entrypoint/` — docopt CLI
- `neogit/testing/` — pytest fixtures (importable by downstream projects)

## Submitting changes

1. Fork the repo, create a feature branch
2. Make your change with tests
3. Run `poetry run poe ccode && poetry run poe test`
4. Open a PR against `master`

CI runs format, lint, type, unit, integration, and a Docker build on every PR.
