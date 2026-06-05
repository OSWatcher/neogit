# Merkle tree design

A [Merkle tree](https://en.wikipedia.org/wiki/Merkle_tree) is a tree where every node's identity is the hash of its content *and* its children's identities. Two subtrees with the same content collapse to the same node. This is the same insight Git is built on.

## Three node kinds

Neogit's Merkle tree has three kinds of node. The canonical serializations live
in `neogit/core/merkle/filesystem.py` (Blob, Tree) and `neogit/merkle/hasher.py`
(Commit). The contract is: same inputs, same hash, always.

### Blob: `SHA-1(content)`

Leaves. The identity is the SHA-1 of the node's content, where "content"
depends on the file kind (`FSMerkleVisitor.visit_FSFileNode`):

- **Regular file**: the raw file bytes.
- **Symlink**: the link target string from `os.readlink()`, *not* the bytes of
  whatever it points at. The symlink's own target is what is captured and hashed.
- **Anything else** (sockets, FIFOs, devices, or a file that raises `OSError`
  when read, such as an unreadable FUSE/reparse entry): hashed as empty content
  (`b""`).

### Tree: `SHA-1(sorted child entries)`

A directory. `FSMerkleVisitor.visit_FSDirectoryNode` walks the directory's
children, sorted **directories first, then by name**, and for each child feeds
the bytes `f"{child_name}{child_hash}\n"` into the running SHA-1. The final
digest is the tree's hash.

```python
# Equivalent of the canonical form, for one directory:
for child in sorted(children, key=lambda c: (not c.is_dir, c.name)):
    h.update(f"{child.name}{child.hash}\n".encode())
tree_hash = h.hexdigest()
```

Note that the entry contains only `name` and `child_hash`; there is no
explicit "kind" byte. The hash is unambiguous because each directory commits
to its sorted, newline-delimited child list.

### Commit: `SHA-1(name + date + tree_sha1)`

A snapshot. From `hasher.py`:

```python
COMMIT_STRING = "\n{name}{date}{tree_sha1}\n"
```

Note what is **not** in the commit hash: the description, the previous-commit
pointer, the branch. Two commits with the same name, same date, and the same
root tree therefore hash identically, and Neo4j's uniqueness constraint on
`Commit.hash` deduplicates them. If you need the description or the history
edge to participate in identity, that's a deliberate change to the canonical
form.

## Why the children are sorted

If we hashed children in insertion order, two directories with the same files in different filesystem-walk orders would get different hashes. The deterministic sort (dirs-first, then by name) makes the hash a true function of the *content* of the directory, not the order the OS happened to return entries in.

## What dedup buys us

Consider a 50,000-file source tree, snapshotted twice with one file changed.

- 1 new `Blob` (the changed file)
- ≤ depth-of-changed-file new `Tree` nodes (every ancestor directory)
- 1 new `Commit`

Everything else is reused: no new database rows, no new object-store uploads. A "snapshot" of a barely-changed tree costs roughly *log(N)* writes, not *N*.

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

These are extension points, not architectural limits: the object-storage layer already abstracts the byte plane, so an alternative chunking strategy could slot in without touching the graph.
