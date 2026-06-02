# Use MinIO or S3 as object storage

By default, neogit stores file contents on the **local filesystem** (under an `appdirs` path). To use MinIO or any S3-compatible store instead, override the `object` configuration block.

## Switch to MinIO

```bash
export NEOGIT_OBJECT__PROVIDER=minio
export NEOGIT_OBJECT__KEY=minioadmin
export NEOGIT_OBJECT__SECRET_KEY=minioadmin
export NEOGIT_OBJECT__HOST=127.0.0.1
export NEOGIT_OBJECT__PORT=9000
export NEOGIT_OBJECT__SECURE=false
```

Then run `neogit init` against the new backend (this creates the bucket if needed) and you're set:

```bash
neogit init
neogit commit hello -r .
```

## Switch to AWS S3

Same shape, just different credentials and host:

```bash
export NEOGIT_OBJECT__PROVIDER=s3
export NEOGIT_OBJECT__KEY=AKIA...
export NEOGIT_OBJECT__SECRET_KEY=...
# region-specific endpoint is picked up by libcloud
```

## Use a settings file instead of env vars

Drop a `settings.toml` next to `neogit/config/default_settings.toml`:

```toml
[default.object]
provider = "minio"
key = "minioadmin"
secret_key = "minioadmin"
host = "127.0.0.1"
port = 9000
secure = false
```

Credentials are better placed in `neogit/config/.secrets.toml` (which is git-ignored).

## See also

- [Reference / Configuration](../reference/configuration.md) for every supported key
