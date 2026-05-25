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
| `--version` | Show neogit version |
| `-r ROOT`, `--root=ROOT` | Repository root directory (defaults to CWD) |
| `-g`, `--gui` | Enable the rich console progress GUI |
| `-d`, `--debug` | Enable debug logging |

## Commands

### `neogit init`

Creates uniqueness constraints in Neo4j and the storage bucket/container. Idempotent — safe to run again.

### `neogit commit <name>`

Snapshot the directory tree at `--root` into a new commit named `<name>` on the current branch.

| Flag | Effect |
|---|---|
| `branch <branch>` | Commit to the named branch instead of the default (`master`) |
| `--unique` | If a commit with the same name already exists on this branch, return its hash instead of creating a duplicate |
| `--before=<commit>` | Insert this commit *before* the named commit (rewrites history) |

### `neogit branch <name> <commit>`

Create a new branch named `<name>` pointing at the commit identified by `<commit>` (hash or commit name).

### `neogit diff <ref1> <ref2>`

Compare two commits and print added / removed / modified paths. Each ref can be a hash or a commit name.

## Exit behavior

On any unhandled exception the CLI drops into an `ipdb` post-mortem session (see `neogit/entrypoint/cmdline.py::post_mortem`). Combine with `--debug` to see the full stack trace.
