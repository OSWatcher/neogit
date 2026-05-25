# neogit

> A Git-like tool for filesystems, backed by a Neo4j graph and pluggable object storage.

Neogit takes content-addressed Merkle-tree snapshots of a directory tree and stores them in two places:

- **Neo4j** — the graph: commits, branches, trees, blobs, and their relationships
- **Object storage** — the bytes: file contents addressed by their SHA-1 (local filesystem, MinIO, or S3 via [Apache Libcloud](https://libcloud.apache.org/))

This split makes filesystem state **queryable as a graph** while keeping file contents in cheap blob storage.

## Where to start

This documentation follows the [Divio framework](https://documentation.divio.com/) — four kinds of docs, each serving a different need:

<div class="grid cards" markdown>

- :material-school: **[Tutorial](tutorial/first-snapshot.md)**

    Learning by doing. Take your first filesystem snapshot in five minutes.

- :material-tools: **[How-to guides](how-to/use-minio-storage.md)**

    Recipes for specific tasks: switching storage backends, diffing commits, embedding neogit in your own Python code.

- :material-book-open-variant: **[Reference](reference/cli.md)**

    The dry facts: every CLI flag, every config key, every node type in the graph.

- :material-lightbulb: **[Explanation](explanation/architecture.md)**

    Background and design rationale: why Neo4j, how the Merkle tree is laid out, what trade-offs were made.

</div>

## Where it's used

Neogit powers the storage layer of the [OSWatcher](https://github.com/OSWatcher) ecosystem, including [grapheos-plugins](https://github.com/OSWatcher/grapheos-plugins), which builds filetype detection, symbol extraction, and syscall-trace plugins on top of neogit's `Commit` / `PluginRun` graph.
