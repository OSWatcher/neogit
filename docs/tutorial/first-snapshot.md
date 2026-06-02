# Your first snapshot

In this tutorial you'll install neogit from PyPI, start a local Neo4j database, and take your first content-addressed snapshot of a directory. You don't need to know Neo4j, Cypher, or Merkle trees — we'll point at things to look at, not explain them. Explanations live under [Explanation](../explanation/architecture.md).

## What you'll need

- Python 3.10 or newer
- [pipx](https://pipx.pypa.io/stable/)
- Docker (for Neo4j)

## 1. Install neogit

```bash
pipx install neogit
```

## 2. Start Neo4j

Start a local Neo4j instance for the tutorial:

```bash
docker run --rm --name neogit-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=none \
  neo4j:5.26
```

When this finishes you should see:

- a Neo4j instance on <http://localhost:7474> — the test container runs with `NEO4J_AUTH=none`, so click **Connect** with no username / password

Leave the browser tab open — we'll come back to it.

## 3. Initialize the repository

```bash
neogit init
```

This creates unique constraints in Neo4j. Run it once per database; running it again is harmless.

## 4. Take your first snapshot

Pick any directory — let's use a real project checkout:

```bash
git clone --depth 1 https://github.com/psf/requests.git neogit-demo-root
neogit commit my-first-snapshot -r ./neogit-demo-root
```

You'll see progress logs while neogit walks the tree, hashes each file, uploads blobs, and stitches everything into a graph commit. It prints the commit hash at the end.

## 5. Look at what just happened

**In Neo4j** (<http://localhost:7474>), run:

```cypher
MATCH (b:Branch)-[:TRACKS_COMMIT]->(c:Commit)-[:OWNS_FILESYSTEM]->(t:Tree)
RETURN b, c, t
```

You'll see a `Branch` node pointing at your `Commit`, which owns a root `Tree`. Click the tree to expand its children — you're looking at your directory, as a graph.

By default neogit stores file contents in local object storage, so you do not need to run MinIO for this tutorial. If you want to inspect a blob store in the browser, see [How-to / MinIO and S3](../how-to/use-minio-storage.md).

## 6. Take a second snapshot

Touch a file, then snapshot again:

```bash
echo "hello" >> ./neogit-demo-root/README.md
neogit commit my-second-snapshot -r ./neogit-demo-root
```

Run the same Cypher query again — you'll now see two `Commit` nodes linked by a `HAS_PREVIOUS` edge, and the file's old and new content will be two distinct `Blob` nodes hanging off two distinct `Tree` nodes for `README.md`.

!!! note "Diffing two commits"

    Use `neogit diff <old-commit-hash> <new-commit-hash>` to compare two
    snapshots. The command prints git `--name-status`-style file changes; see
    [How-to / Diff two commits](../how-to/diff-commits.md).

## Where to next

- Switch object storage to MinIO or S3: [How-to / MinIO and S3](../how-to/use-minio-storage.md)
- Use neogit inside your own Python code: [How-to / Library usage](../how-to/use-as-library.md)
- Understand the data model you just created: [Explanation / Architecture](../explanation/architecture.md)
