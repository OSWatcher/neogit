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

## Regenerating the README demo GIF

The animated demo (`docs/assets/neogit-commit-demo.gif`) is recorded with
[asciinema](https://asciinema.org/), rendered with
[agg](https://github.com/asciinema/agg), and optimized with `gifsicle`. It
snapshots two Debian container root filesystems — see
[Snapshot a container filesystem](snapshot-a-container-filesystem.md) for the
commands it runs.

To re-record it (Neo4j must be running):

```bash
# 1. Export the two rootfs trees (see the how-to above)
for v in 11 12; do
  mkdir -p ~/local/debian_$v
  cid=$(docker create debian:$v); docker export "$cid" | tar -C ~/local/debian_$v -xf -; docker rm "$cid"
done

# 2. IMPORTANT: wipe the graph AND the object store first. Otherwise leftover
#    blobs make the first commit show everything as deduped, killing the
#    "heavy upload" beat.
docker exec neogit_neo4j_testdb cypher-shell -d neo4j "MATCH (n) DETACH DELETE n;"
rm -rf ~/.local/share/Neogit/objects

# 3. Size your terminal to ~100x28 (the --gui panes need the room; a narrow
#    terminal cramps them), then record the run:
asciinema rec demo.cast --overwrite -c "poetry run bash -c '
  neogit init
  neogit commit Debian_11 -r ~/local/debian_11 --gui
  neogit commit Debian_12 -r ~/local/debian_12 --gui
  neogit log
  neogit diff \$(neogit log | grep Debian_11 | grep -oE \"[0-9a-f]{40}\") \
             \$(neogit log | grep Debian_12 | grep -oE \"[0-9a-f]{40}\")
'"

# 4. Render and optimize (~3 MB output)
agg --font-size 16 --fps-cap 10 demo.cast demo.gif
gifsicle -O3 --lossy=100 --colors 64 demo.gif -o docs/assets/neogit-commit-demo.gif
```

`~/.local/share/Neogit/objects` is the default local object-storage bucket
(`appdirs` user-data dir); adjust if you set `object.key` in your config.

## Submitting changes

1. Fork the repo, create a feature branch
2. Make your change with tests
3. Run `poetry run poe ccode && poetry run poe test`
4. Open a PR against `master`

CI runs format, lint, type, unit, integration, and a Docker build on every PR.
