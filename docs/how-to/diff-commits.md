# Diff two commits

!!! warning "Planned feature — not yet implemented"

    A `neogit diff <ref1> <ref2>` subcommand is declared in the CLI's docopt usage
    block, but the service layer has no matching `Neogit.diff()` method yet.
    Invoking `neogit diff` today raises `AttributeError`. This page documents the
    intended shape so the design is on record; the implementation will follow
    in a separate PR.

## Intended CLI shape

```bash
neogit diff <ref1> <ref2>
```

`ref1` and `ref2` will be resolvable from either:

- a **commit hash** (full SHA-1), or
- a **commit name** (the `<name>` passed to `neogit commit`)

Planned output: paths grouped by added / removed / modified, relative to the commit root.

## Workaround today: query the graph

Until `diff` lands, you can compare two commits in Cypher. Each commit owns a
`Tree`, and the Merkle property guarantees that subtrees with identical content
share a node — so the diff is "find paths that disagree":

```cypher
// Children present in commit A but not B (added in A, or removed from B)
MATCH (a:Commit {name: $a})-[:OWNS_FILESYSTEM]->(rootA:Tree),
      (b:Commit {name: $b})-[:OWNS_FILESYSTEM]->(rootB:Tree)
MATCH (rootA)-[:HAS_CHILD_BLOB|HAS_CHILD_TREE*]->(n)
WHERE NOT (rootB)-[:HAS_CHILD_BLOB|HAS_CHILD_TREE*]->(n)
RETURN n
```

This is what the `diff` implementation will lean on internally.

## See also

- [Explanation / Merkle design](../explanation/merkle-design.md) — why content-addressed diffs are cheap
- [Reference / Data model](../reference/data-model.md) — node and edge shapes
