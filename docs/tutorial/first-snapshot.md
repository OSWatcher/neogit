# Your first snapshot

In this tutorial you'll clone neogit, spin up the supporting services, and take your first content-addressed snapshot of a directory. You don't need to know Neo4j, Cypher, or Merkle trees — we'll point at things to look at, not explain them. Explanations live under [Explanation](../explanation/architecture.md).

## What you'll need

- Python 3.11 or newer
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for Neo4j and MinIO)

## 1. Get the code

```bash
git clone https://github.com/OSWatcher/neogit.git
cd neogit
poetry install
```

## 2. Start Neo4j and MinIO

Neogit ships a Poe task that creates the two containers it needs and seeds them:

```bash
poetry run poe create_dbs
```

When this finishes you should see:

- a Neo4j instance on <http://localhost:7474> (login `neo4j` / `password`)
- a MinIO instance on <http://localhost:9001> (login `minioadmin` / `minioadmin`)

Leave both browser tabs open — we'll come back to them.

## 3. Initialize the repository

```bash
poetry run neogit init
```

This creates unique constraints in Neo4j and the object-storage container. Run it once per database; running it again is harmless.

## 4. Take your first snapshot

Pick any directory — let's use the neogit source itself:

```bash
poetry run neogit commit my-first-snapshot -r .
```

You'll see progress logs while neogit walks the tree, hashes each file, uploads blobs, and stitches everything into a graph commit. It prints the commit hash at the end.

## 5. Look at what just happened

**In Neo4j** (<http://localhost:7474>), run:

```cypher
MATCH (b:Branch)-[:TRACKS_COMMIT]->(c:Commit)-[:OWNS_FILESYSTEM]->(t:Tree)
RETURN b, c, t
```

You'll see a `Branch` node pointing at your `Commit`, which owns a root `Tree`. Click the tree to expand its children — you're looking at your directory, as a graph.

**In MinIO** (<http://localhost:9001>), browse the bucket. Each object is one file's content, named by its SHA-1.

## 6. Take a second snapshot and diff

Touch a file, then snapshot again:

```bash
echo "hello" >> README.md
poetry run neogit commit my-second-snapshot -r .
poetry run neogit diff my-first-snapshot my-second-snapshot
```

The diff tells you which paths added, removed, or changed between the two commits.

## Where to next

- Switch object storage to MinIO or S3: [How-to / MinIO and S3](../how-to/use-minio-storage.md)
- Use neogit inside your own Python code: [How-to / Library usage](../how-to/use-as-library.md)
- Understand the data model you just created: [Explanation / Architecture](../explanation/architecture.md)
