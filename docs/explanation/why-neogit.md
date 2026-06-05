# Why neogit?

neogit turns filesystem history into a **content-addressed temporal graph**. That phrase is
doing a lot of work, so this page unpacks it, then shows the three kinds of question the graph
makes cheap, two of which Git cannot answer at all.

## A content-addressed temporal graph (not a "temporal database")

It's tempting to call neogit a *temporal database*, but that term already means something
specific: SQL:2011 valid-time / transaction-time, row-level versioning, "what did this record
look like *as of* date X." neogit is not that.

neogit borrows Git's model instead:

- **Content-addressed.** Every file, directory, and commit is identified by the hash of its
  own content. Identical content is the same node everywhere, so deduplication is free and
  identity is global across snapshots, branches, and machines.
- **Temporal.** The time axis is the **commit DAG**, exactly like Git. History is a chain of
  immutable snapshots, not a timestamp column.
- **Graph.** Instead of packing that DAG into files on disk, neogit stores it in Neo4j, so
  the history is *queryable* with Cypher rather than only *walkable* through git's history
  commands.

The data model is small (`Commit`, `Branch`, `Tree`, `Blob`; see the
[data model reference](../reference/data-model.md)). The power comes from putting it in a graph.

## neogit is a substrate you enrich

Capturing the filesystem is only the foundation. Because every node is content-addressed and
lives in one graph, downstream tools can **hang their own hashable characteristics off it**:
symbols, structs, registry values, syscalls, anything you can hash. Those characteristics
inherit the same deduplication, the same temporal identity, and the same queryability as the
file bytes.

[OSWatcher](https://github.com/OSWatcher) is the reference example. It builds on neogit to trace
a **file, a registry key, a symbol, or a struct field** across an operating system's entire
release history, the same "git log for any characteristic" experience, on data Git's object
model never knew about.

## The three pillars

### 1. Evolution: how one thing changed over time

The classic version-control question: walk a characteristic backwards through history and see
when it appeared and how it changed. This is what `neogit diff` and OSWatcher's "git log"
feature surface, for example how `_EPROCESS.Flags2` (a Windows kernel struct field) evolved
build to build, or every SHA-1 of `/Windows/System32/OpenSSH/ssh.exe` since it first shipped.

Git can do *this* one too, via diff. The next two are where it can't follow.

### 2. Provenance: where has this characteristic ever appeared?

Given one object, find **every commit that contained it**. With content-addressing this is a
reverse traversal, the free inverted index Git has no equivalent for:

```cypher
// Which commits contain a file with this content hash?
MATCH (c:Commit)-[:OWNS_FILESYSTEM]->(:Tree)
      -[:HAS_CHILD_TREE|HAS_CHILD_BLOB*]->(b:Blob {sha1sum: $sha1})
RETURN DISTINCT c.name, c.date
ORDER BY c.date
```

Because enrichment nodes live in the same graph, the *same shape* answers
"which operating systems ever shipped this exact symbol / struct / registry value?" You just
start the traversal from the enriched node instead of a `Blob`.

### 3. Commonality: what is common or stable across all of history?

Aggregate across the whole corpus, not just two snapshots. Pairwise intersection/difference
(what `neogit diff` does) is the *n = 2* special case; the graph also answers corpus-wide
questions in a few lines of Cypher:

```cypher
// Top 20 most widely-shared files across every captured snapshot
MATCH (c:Commit)-[:OWNS_FILESYSTEM]->(:Tree)
      -[:HAS_CHILD_TREE|HAS_CHILD_BLOB*]->(b:Blob)
WITH b.sha1sum AS content, count(DISTINCT c) AS seen_in_commits
RETURN content, seen_in_commits
ORDER BY seen_in_commits DESC
LIMIT 20
```

"Most *stable*" is the same idea with the time axis folded in: a characteristic whose content
hash is unchanged across the most consecutive releases. *"Top 20 most stable kernel structs
across Windows history"* is a one-screen Cypher query, and has no Git equivalent, because Git
can't enumerate membership across history without scanning all of it.

## Why a graph, and not Git plus a script?

The honest answer is one structural fact about [how Git's object model works](why-neo4j.md):

> Git objects are addressed by the hash of their own content, and an object's bytes never
> reference what points at it, so the object graph is navigable only **forward**:
> commit → tree → blob. There is no native way to ask the reverse, *"which commits have this
> object in their tree?"* `git log --find-object` looks like it, but it's pickaxe: it reports
> where an object's count *changed* in a diff (addition/deletion), so it misses commits that
> carry the object unchanged and falsely includes commits that *deleted* it. The only correct
> answer is to walk all of history and inspect every tree, a scan rather than a lookup. (The
> commit-graph file and reachability bitmaps don't help: both are forward-only.)

Provenance and commonality are exactly those reverse and aggregate questions. Put the
content-addressed objects in a graph and they become single traversals, which is the whole
reason neogit exists.

## Where to look next

- [Why Neo4j?](why-neo4j.md): the choice of graph database, and the Git comparison in full
- [Architecture overview](architecture.md): how structure and bytes are split across two stores
- [Merkle tree design](merkle-design.md): how the hashing works
- [Data model reference](../reference/data-model.md): exact node and edge shapes
