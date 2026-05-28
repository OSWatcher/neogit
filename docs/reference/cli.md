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
| `branch <branch>` | **Planned.** Intended to commit to the named branch; the docopt usage exposes the argument but the CLI does not yet forward it to `Neogit.commit()` — currently the value is silently dropped. Commits land on the default branch (`master`, configurable via `NEOGIT_BRANCH`). |
| `--unique` | If a commit with the same name already exists on this branch, return its hash instead of creating a duplicate |
| `--before=<commit>` | Insert this commit *before* the named commit (rewrites history) |

### `neogit branch <name> <commit>`

Create a new branch named `<name>` pointing at `<commit>`, where `<commit>` is the SHA-1 hash returned by `neogit commit`. This mirrors Git, where branches are created from a commit ID rather than a commit message.

### `neogit diff <ref1> <ref2>`

!!! warning "Planned — not yet implemented"

    The `diff` subcommand is declared in the docopt usage block but `Neogit.diff()`
    does not exist yet; invoking it raises `AttributeError`. See
    [How-to / Diff two commits](../how-to/diff-commits.md) for a Cypher workaround
    and the intended design.

## Exit behavior

On any unhandled exception the CLI drops into an `ipdb` post-mortem session (see `neogit/entrypoint/cmdline.py::post_mortem`). Combine with `--debug` to see the full stack trace.

!!! note "`--version` flag"

    The docopt usage block lists a `--version` option, but `handle_cmdline()`
    invokes `docopt()` without a `version=` argument, so the flag is parsed
    but never produces output. Treat it as not implemented.
