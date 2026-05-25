# Embed neogit as a library

Neogit's CLI is a thin shell over a Python API you can call directly. This is how downstream projects like [grapheos-plugins](https://github.com/OSWatcher/grapheos-plugins) build on top of the same graph.

## Install

Add neogit to your `pyproject.toml`:

```toml
[tool.poetry.dependencies]
neogit = { git = "https://github.com/OSWatcher/neogit.git", tag = "v0.13.1" }
```

(Once neogit is published to PyPI, this will become a plain version pin.)

## Take a snapshot from Python

```python
from pathlib import Path
from neogit.service import Neogit

git = Neogit()
git.init()                                            # idempotent
commit_hash = git.commit("snapshot-1", Path("/path/to/capture"))
```

`Neogit()` reads its Neo4j and object-storage settings from the same configuration system as the CLI — environment variables prefixed with `NEOGIT_` and TOML files under `neogit/config/`. See [Reference / Configuration](../reference/configuration.md).

## Work with the graph directly

The Neo4j models are [neomodel](https://neomodel.readthedocs.io/) `StructuredNode` classes:

```python
from neogit.model.neo import Commit, Branch

master = Branch.nodes.get(name="master")
head = master.tracks.single()
for c in Commit.nodes.all():
    print(c.hash, c.name)
```

You can run arbitrary Cypher via the service helper. It retries deadlocked
transactions with exponential backoff, and (unlike `neomodel.db.cypher_query`)
its `params` argument is **required** — pass an empty dict for parameter-less
queries:

```python
from neogit.service.neogit import cypher_query_with_backoff

rows, _ = cypher_query_with_backoff(
    "MATCH (b:Blob) RETURN b.sha1sum AS hash LIMIT 5",
    {},
)

# Parameterised:
rows, _ = cypher_query_with_backoff(
    "MATCH (c:Commit {name: $name}) RETURN c",
    {"name": "snap-1"},
)
```

## Attach your own nodes

Downstream projects can attach domain nodes to neogit's `Commit` — for example, a `PluginRun` node that records when an analyzer ran against a specific commit. See `neogit.model.neo.PluginRun` for the shape, and grapheos-plugins' `plugins/types.py` for a real-world consumer.

## Reuse the test fixtures

If your library uses neogit, you can reuse its pytest fixtures:

```python
# conftest.py
from neogit.testing.fixtures import *  # noqa: F401, F403
```

This gives you `neogit`, `neogit_init`, `clean_neo4j_db`, parameterized object-storage fixtures, and more. See `neogit/testing/fixtures.py` for the full list.
