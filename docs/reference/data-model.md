# Data model reference

All persistent state lives in two places: a Neo4j graph (structure and metadata) and an object store (file bytes, addressed by SHA-1).

## Graph nodes

| Label | Module | Key properties | Purpose |
|---|---|---|---|
| `Branch` | `neogit.model.neo` | `name` | Named pointer to a commit |
| `Commit` | `neogit.model.neo` | `hash`, `sha1sum`, `name`, `date`, `description` | A snapshot |
| `Tree` | `neogit.model.merkle` | `hash`, `sha1sum` | A directory in the Merkle tree |
| `Blob` | `neogit.model.merkle` | `hash`, `sha1sum` | A file content reference |
| `PluginRun` | `neogit.model.neo` | (varies) | Attaches downstream analysis state to a commit |

`hash` is the Merkle hash of the node; `sha1sum` is the SHA-1 of the content (for `Blob`) or of the canonical serialization (for `Tree` / `Commit`).

## Relationships

```
Branch --[TRACKS_COMMIT]--> Commit
Commit --[HAS_PREVIOUS]--> Commit          (commit history)
Commit --[OWNS_FILESYSTEM]--> Tree         (the root directory)
Tree   --[HAS_CHILD_TREE {name}]--> Tree   (subdirectories)
Tree   --[HAS_CHILD_BLOB {name}]--> Blob   (files)
```

Edge properties (`name`) carry the path component, so the same `Tree` or `Blob` can appear under different names in different parents — that's the whole point of content addressing.

## Object storage layout

The object store contains one entry per unique `Blob` SHA-1. Keys are the hex SHA-1; values are the raw file bytes. Identical files across commits, branches, or snapshots deduplicate automatically.

## Example Cypher queries

Latest commit on `master`:

```cypher
MATCH (b:Branch {name: "master"})-[:TRACKS_COMMIT]->(c:Commit)
RETURN c
```

Full file tree of a commit:

```cypher
MATCH (c:Commit {name: "snap-1"})-[:OWNS_FILESYSTEM]->(root:Tree)
MATCH path = (root)-[:HAS_CHILD_TREE|HAS_CHILD_BLOB*]->(n)
RETURN path
```

History walk:

```cypher
MATCH (b:Branch {name: "master"})-[:TRACKS_COMMIT]->(head:Commit)
MATCH path = (head)-[:HAS_PREVIOUS*]->(ancestor)
RETURN ancestor.name, ancestor.date
ORDER BY ancestor.date DESC
```
