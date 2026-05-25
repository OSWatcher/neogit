# Configuration reference

Neogit uses [Dynaconf](https://www.dynaconf.com/) to merge settings from multiple sources, with the following precedence (highest first):

1. **Environment variables** prefixed `NEOGIT_`
2. `neogit/config/.secrets.toml` (git-ignored, for credentials)
3. `neogit/config/settings.toml` (user overrides)
4. `neogit/config/default_settings.toml` (shipped defaults)

Nested keys use `__` (double underscore) in env vars: `NEOGIT_NEO4J__HOST` maps to `[default.neo4j] host`.

## Top-level settings

| Key | Env var | Default | Description |
|---|---|---|---|
| `branch` | `NEOGIT_BRANCH` | `master` | Default branch name when no `branch <name>` is passed to `commit` |

## Neo4j (`[default.neo4j]`)

| Key | Env var | Default | Description |
|---|---|---|---|
| `proto` | `NEOGIT_NEO4J__PROTO` | `bolt` | Driver protocol (`bolt`, `bolt+s`, `neo4j`, …) |
| `host` | `NEOGIT_NEO4J__HOST` | `localhost` | Neo4j host |
| `port` | `NEOGIT_NEO4J__PORT` | `7687` | Bolt port |
| `user` | `NEOGIT_NEO4J__USER` | — | Username (set in `.secrets.toml` or env) |
| `password` | `NEOGIT_NEO4J__PASSWORD` | — | Password |

## Object storage (`[default.object]`)

| Key | Env var | Default | Description |
|---|---|---|---|
| `provider` | `NEOGIT_OBJECT__PROVIDER` | `local` | `local`, `minio`, or any libcloud provider id (e.g. `s3`) |
| `key` | `NEOGIT_OBJECT__KEY` | — | For `local`: storage path. For S3/MinIO: access key |
| `secret_key` | `NEOGIT_OBJECT__SECRET_KEY` | — | S3/MinIO secret key |
| `host` | `NEOGIT_OBJECT__HOST` | — | S3/MinIO endpoint |
| `port` | `NEOGIT_OBJECT__PORT` | — | S3/MinIO port |
| `secure` | `NEOGIT_OBJECT__SECURE` | — | TLS toggle for S3/MinIO |
| `container_name` | `NEOGIT_OBJECT__CONTAINER_NAME` | — | Bucket / container name |

## Example: full MinIO setup via env

```bash
export NEOGIT_NEO4J__HOST=localhost
export NEOGIT_NEO4J__PORT=7687
export NEOGIT_NEO4J__USER=neo4j
export NEOGIT_NEO4J__PASSWORD=password

export NEOGIT_OBJECT__PROVIDER=minio
export NEOGIT_OBJECT__KEY=minioadmin
export NEOGIT_OBJECT__SECRET_KEY=minioadmin
export NEOGIT_OBJECT__HOST=127.0.0.1
export NEOGIT_OBJECT__PORT=9000
export NEOGIT_OBJECT__SECURE=false
```
