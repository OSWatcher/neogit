# Diff two commits

Compare the filesystem snapshots of two commits:

```bash
neogit diff <commit-hash-1> <commit-hash-2>
```

Both refs are **commit SHA-1 hashes** (the value printed by `neogit commit` and
used by `neogit branch`). The first is the *old* commit, the second the *new* one.

Each line of output is an `FSDiffObject`:

| field | meaning |
|-------|---------|
| `status` | `NEW`, `DEL`, or `MOD` |
| `is_dir` | whether the entry is a directory (`Tree`) or a file (`Blob`) |
| `path` | absolute path within the snapshot |
| `old_sha1sum` / `new_sha1sum` | content hashes on each side (`None` where absent) |

The diff is **recursive by default**: an added or removed directory is expanded to
all of its descendants, and modified directories are descended into. Because neogit
stores directories as nodes, empty directories also appear (unlike `git`, which
cannot track them). A path that switches between file and directory is reported as a
`DEL` of the old node plus a `NEW` of the new one.

Internally this walks the two `Tree` graphs keyed by the `HAS_CHILD_TREE` /
`HAS_CHILD_BLOB` relationship `name`, so it is genuinely path-aware — moved or
duplicated blobs are not confused. Refs that do not resolve to a commit raise a
`ValueError`.

## Using it as a library

```python
from neogit.service import Neogit

git = Neogit()
for change in git.diff(old_hash, new_hash):
    print(change.status.name, change.path)
```

`Neogit.diff()` returns an iterator of `FSDiffObject`; pass `recursive=False` to get
only the top-level entries.

## See also

- [Explanation / Merkle design](../explanation/merkle-design.md) — why content-addressed diffs are cheap
- [Reference / Data model](../reference/data-model.md) — node and edge shapes
