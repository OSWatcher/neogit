# neogit

> A Git-like tool for filesystems, backed by a Neo4j graph and pluggable object storage.

Neogit takes content-addressed Merkle-tree snapshots of a directory tree and stores them in two places:

- **Neo4j** — the graph: commits, branches, trees, blobs, and their relationships
- **Object storage** — the bytes: file contents addressed by their SHA-1 (local filesystem, MinIO, or S3 via [Apache Libcloud](https://libcloud.apache.org/))

This split makes filesystem state **queryable as a graph** (Cypher over commits, diff trees, walk history) while keeping file contents in cheap blob storage.

## Where it's used

- **CLI tool** — capture and diff filesystem snapshots from the command line
- **Python library** — embed the Merkle model and Neo4j layer in your own pipeline. For example, [OSWatcher](https://github.com/OSWatcher) uses neogit as the storage foundation, and [grapheos-plugins](https://github.com/OSWatcher/grapheos-plugins) builds analysis plugins (filetype detection, symbol extraction, syscall tracing, …) on top of the `Commit` / `PluginRun` graph

## Quickstart

Requirements: Python 3.11+, Poetry, Docker.

```bash
git clone https://github.com/OSWatcher/neogit.git
cd neogit
poetry install
poetry run poe create_dbs        # spins up Neo4j + MinIO test containers
poetry run neogit init           # creates Neo4j constraints
poetry run neogit commit hello -r .
```

Open the Neo4j browser at <http://localhost:7474> and run:

```cypher
MATCH (c:Commit)-[r]->(t:Tree) RETURN c, r, t LIMIT 25
```

## CLI overview

```bash
neogit init                                    # initialize database constraints
neogit commit <name> -r <path>                 # snapshot a directory on the default branch
neogit branch <name> <commit_hash>             # create a branch pointing at a commit hash
```

> **Note:** the `branch <branch>` sub-argument of `commit` and the `diff` subcommand
> are present in the docopt usage but not yet wired through to the service layer —
> see [docs/reference/cli.md](docs/reference/cli.md) for the current status.

See [docs/reference/cli.md](docs/reference/cli.md) for the full reference.

## Use as a library

```python
from pathlib import Path
from neogit.service import Neogit

git = Neogit()
git.init()
commit_hash = git.commit("snapshot-1", Path("/path/to/capture"))
```

The graph model (`Commit`, `Branch`, `Tree`, `Blob`, `PluginRun`) is exposed under `neogit.model` for downstream tools that want to attach their own nodes — see [docs/explanation/data-model.md](docs/explanation/data-model.md).

## Documentation

Full documentation lives under [`docs/`](docs/) and follows the [Divio framework](https://documentation.divio.com/):

- **[Tutorial](docs/tutorial/first-snapshot.md)** — your first snapshot in 5 minutes
- **[How-to guides](docs/how-to/)** — recipes for specific tasks (MinIO, S3, diffs, embedding the library)
- **[Reference](docs/reference/)** — CLI flags, config keys, data model
- **[Explanation](docs/explanation/)** — design rationale, Merkle layout, why Neo4j

To preview the docs locally:

```bash
poetry install --with docs       # one-time, installs mkdocs into the venv
poetry run poe docs_serve        # equivalent to: poetry run mkdocs serve
```

## Development

```bash
poetry install
poetry run poe ccode      # fmt + lint + type-check
poetry run poe test       # full test suite
```

See [docs/how-to/contributing.md](docs/how-to/contributing.md) for the full dev workflow.

## License

License **TBD** — this repository is not yet licensed for redistribution. A formal license will be added in a follow-up; until then, please open an issue if you want to use or redistribute the code so we can discuss terms.
