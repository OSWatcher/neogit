# CLI reference

```
Usage:
  neogit [options] init
  neogit [options] commit <name> [branch <branch>] [--unique] [--before=<commit>]
  neogit [options] branch <name> <commit>
  neogit [options] diff <ref1> <ref2>
```

## Global options

| Option | Description |
|---|---|
| `-h`, `--help` | Show help and exit |
| `--version` | Print the installed neogit version and exit |
| `-r ROOT`, `--root=ROOT` | Repository root directory (defaults to CWD) |
| `-g`, `--gui` | Enable the rich console progress GUI |
| `-d`, `--debug` | Enable debug logging |

## Commands

### `neogit init`

Creates uniqueness constraints in Neo4j and the storage bucket/container. Idempotent — safe to run again.

### `neogit commit <name>`

Snapshot the directory tree at `--root` into a new commit named `<name>`.

| Flag | Effect |
|---|---|
| `branch <branch>` | Commit to the named branch, creating it if it does not exist. The CLI forwards this to `Neogit.commit(..., branch_name=<branch>)`. Omit it and commits land on the default branch (`master`, configurable via `NEOGIT_BRANCH`). |
| `--unique` | If a commit with the same name already exists on this branch, return its hash instead of creating a duplicate |
| `--before=<commit>` | Insert this commit *before* the named commit (rewrites history) |

### `neogit branch <name> <commit>`

Create a new branch named `<name>` pointing at `<commit>`, where `<commit>` is the SHA-1 hash returned by `neogit commit`. This mirrors Git, where branches are created from a commit ID rather than a commit message.

### `neogit diff <ref1> <ref2>`

Resolves each ref (a commit SHA-1 hash) to its tree and walks both Merkle trees.

Output is git `--name-status` style — one line per changed **file**: a status
letter, two spaces, then the path. `A` = added, `M` = modified, `D` = deleted,
`T` = type change. The letter is colored when stdout is a terminal
(green / yellow / red / cyan); when the output is piped or redirected, color is
stripped and you get plain, greppable lines like `M  /fs/jffs2/acl.c`.
Directory entries are not shown — only the files inside them.

See [How-to / Diff two commits](../how-to/diff-commits.md) for examples.

## Exit behavior

On any unhandled exception the CLI drops into an `ipdb` post-mortem session (see `neogit/entrypoint/cmdline.py::post_mortem`). Combine with `--debug` to see the full stack trace.
