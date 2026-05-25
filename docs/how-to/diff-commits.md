# Diff two commits

`neogit diff` compares two commit references and reports paths that were added, removed, or modified between them.

## From the CLI

```bash
neogit diff <ref1> <ref2>
```

`ref1` and `ref2` can be either:

- a **commit hash** (full SHA-1), or
- a **commit name** (the `<name>` you passed to `neogit commit`)

Example workflow:

```bash
neogit commit snap-before -r /etc
# ... change files ...
neogit commit snap-after  -r /etc
neogit diff snap-before snap-after
```

Output groups changes by kind (added / removed / modified) and prints paths relative to the commit root.

## From Python

```python
from neogit.service import Neogit

git = Neogit()
diff = git.diff("snap-before", "snap-after")
```

The `diff` object exposes the same add / remove / modify partitions, suitable for feeding into downstream tools or reports.

## See also

- [Reference / CLI](../reference/cli.md) for the full flag list
- [Explanation / Merkle design](../explanation/merkle-design.md) — why the diff is cheap
