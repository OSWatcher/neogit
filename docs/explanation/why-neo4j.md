# Why Neo4j?

Git stores its object database as files on disk and reconstructs history by chasing pointers between them. That works beautifully when the consumer is `git log`. It works less well when the consumer is a researcher who wants to ask:

> *"Across every snapshot we have of this system, which commits contain a binary whose SHA-1 is X?"*

…or:

> *"Give me every distinct version of `/etc/passwd` that has ever appeared in any branch."*

These are graph queries. Expressing them on top of a pile of pack files is painful; expressing them in Cypher is one or two lines.

!!! note "The reverse query Git can't answer"

    The second question isn't just *awkward* on Git. It has **no native answer at all**. Git objects are addressed by the hash of their own content, and an object's bytes never reference what points at it, so the object graph is navigable only forward: commit → tree → blob. Asking the reverse, *"which commits have this object in their tree?"*, is not something Git exposes.

    `git log --find-object` looks like the answer, but it's [pickaxe](https://git-scm.com/book/en/v2/Git-Tools-Searching): it reports where an object's count *changed* in a diff (addition/deletion), so it **misses** commits that carry the object unchanged and **falsely includes** commits that *deleted* it. The only correct answer is to walk all of history and inspect every tree, a scan rather than a lookup. (The [commit-graph](https://git-scm.com/docs/commit-graph) file and [reachability bitmaps](https://git-scm.com/docs/bitmap-format) don't help: both are forward-only.)

    Put the same content-addressed objects in a graph and that reverse question becomes a single traversal, which is exactly what makes neogit's *provenance* and *commonality* queries cheap. See [Why neogit?](why-neogit.md).

## What we get from a graph database

- **Cheap reachability queries.** "All blobs in commit X" and "all commits that contain blob Y" are symmetric: both are short Cypher patterns.
- **Schema enforcement at the boundary.** Uniqueness constraints on `Blob.hash`, `Tree.hash`, `Commit.hash`, and `Branch.name` are declared once, enforced by the engine.
- **Inspectable state.** The Neo4j browser is a built-in debugging tool. You can literally see your filesystem as a graph and click around it.
- **Edge properties.** A blob's *name* is a property of the edge, not the node, which is exactly right, because the same blob can be `passwd` in one tree and `passwd.bak` in another.

## What we give up

- **Operational complexity.** Neo4j is a real database with real ops. Git has none.
- **Portability.** A Git repo is a directory; a neogit repo is a database plus a bucket. You can't `scp` it.
- **Familiarity.** Most engineers know Git porcelain. Almost none know Cypher.

For the use cases neogit was built for (capturing and analyzing whole-OS filesystem snapshots), these trade-offs are easy. The query power dominates. For "version control my codebase," Git is still right.

## Why not a relational schema?

We considered it. A relational model could express the same data, but a few things steered us toward a graph:

- The natural unit of inquiry is a **path through the graph** (branch → commit → tree → subtree → blob). Recursive CTEs do this in SQL; first-class pattern matching does it in Cypher.
- Most "interesting" queries involve **arbitrary-depth walks**, which is exactly where graph engines shine.
- The downstream consumers (e.g. [OSWatcher](https://github.com/OSWatcher)) attach their own analysis nodes (`PluginRun`, symbol tables, syscall traces) to neogit's commits, and they want those to be just more edges in the same graph, not a parallel schema.
