# Architecture overview

Neogit is shaped by one design choice: **structure and bytes live in different stores.**

```
┌──────────────┐       ┌────────────────────────┐
│   CLI / API  │       │     Neo4j (graph)      │
│  neogit ...  │──────▶│  Branch, Commit,       │
└──────┬───────┘       │  Tree, Blob, edges     │
       │               └────────────────────────┘
       │
       │               ┌────────────────────────┐
       └──────────────▶│  Object storage        │
                       │  (local / MinIO / S3)  │
                       │  blob bytes by SHA-1   │
                       └────────────────────────┘
```

## The graph store

A neomodel-backed Neo4j database holds the relationships: which commit is on which branch, which tree owns which subtree, which blob hangs off which tree under what name. Everything that's "shape" lives here.

Because it's a graph database, traversals that would be expensive in a relational schema — "give me every blob reachable from commit X", "walk history backwards", "find every commit that contains a blob with this hash" — are first-class queries.

## The object store

File contents never enter Neo4j. They live in a blob store keyed by SHA-1 of the content. Neogit's `object_storage` package wraps three backends behind one interface:

- `FakeObjectStorage` — in-memory, for fast tests
- `LibcloudObjectStorage` — production: local filesystem, MinIO, S3, or anything else [libcloud](https://libcloud.apache.org/) supports
- `TSObjectStorage` — thread-safe wrapper around either of the above, used during parallel commit walks

This split has two practical consequences:

1. **Deduplication is free.** Two identical files (across commits, across branches, across machines) share the same SHA-1 and the same single object.
2. **The graph stays small.** Even with terabytes of captured filesystem data, the Neo4j footprint is metadata-sized.

## The commit pipeline

When you run `neogit commit <name> -r <path>`:

1. `core/` walks the filesystem with the visitor pattern, producing `FSDirectoryNode` / `FSFileNode` objects.
2. `NeoMerkleTreeBuilder` hashes each file, **uploads new blobs** to the object store, and stitches `Tree` / `Blob` nodes into Neo4j inside a single transaction.
3. The new `Commit` is wired into the branch — either as the new head (default) or inserted at a chosen position (`--before`).

The Merkle property (a parent's hash is determined by its children's hashes) means re-snapshotting a tree where almost nothing changed reuses almost every existing node.

## Where to look next

- [Why Neo4j?](why-neo4j.md) — the choice of graph database
- [Merkle design](merkle-design.md) — how the hashing actually works
- [Data model reference](../reference/data-model.md) — exact node and edge shapes
