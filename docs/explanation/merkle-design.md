# Merkle tree design

A [Merkle tree](https://en.wikipedia.org/wiki/Merkle_tree) is a tree where every node's identity is the hash of its content *and* its children's identities. Two subtrees with the same content collapse to the same node. This is the same insight Git is built on.

## Three node kinds

Neogit's Merkle tree has three kinds of node:

- **Blob** — leaf. Identity = `SHA-1(file bytes)`.
- **Tree** — internal node = a directory. Identity = `SHA-1(sorted list of (name, child_hash, kind) tuples)`.
- **Commit** — root with metadata. Identity = `SHA-1(root_tree_hash + name + date + description + previous_hash)`.

The exact canonical serialization lives in `neogit/core/` — the contract is: same inputs, same hash, always.

## Why the children are sorted

If we hashed children in insertion order, two directories with the same files in different filesystem-walk orders would get different hashes. Sorting by name makes the hash a true function of the *set* of children, which is what we want.

## What dedup buys us

Consider a 50,000-file source tree, snapshotted twice with one file changed.

- 1 new `Blob` (the changed file)
- ≤ depth-of-changed-file new `Tree` nodes (every ancestor directory)
- 1 new `Commit`

Everything else is reused — no new database rows, no new object-store uploads. A "snapshot" of a barely-changed tree costs roughly *log(N)* writes, not *N*.

For OSWatcher's whole-OS captures, where consecutive snapshots differ in dozens of files out of millions, this matters by orders of magnitude.

## Why diffs are cheap

A diff between two commits walks both root trees in parallel:

- If both subtrees have the same hash → no recursion, no changes there
- If hashes differ → recurse into children
- Hit a `Blob` mismatch → that's an edit; mismatched `Blob` on one side → add/remove

Most of the tree usually hashes-equal at the top, so diffs touch O(changed paths) nodes, not O(total paths).

## What we don't do (and could)

- **No re-chunking of large files.** A 4 GB ISO that flips one byte gets re-uploaded in full. Real Git mitigates this with delta packs; neogit doesn't (yet).
- **No content-defined chunking.** Each blob is one file. Fine for typical OS captures; weaker for huge binaries.

These are extension points, not architectural limits — the object-storage layer already abstracts the byte plane, so an alternative chunking strategy could slot in without touching the graph.
