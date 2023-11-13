from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from appdirs import user_data_dir
from dynaconf import Dynaconf, LazySettings, Validator

APPNAME = "Neogit"
CUR_DIR = Path(__file__).parent
LOG_FMT = "%(asctime)s:%(name)s:%(levelname)s:%(message)s"
USER_DATA_DIR = Path(user_data_dir(APPNAME))
CONTAINER_NAME = "objects"
NEO4J_HTTP_PORT = 7474

settings = Dynaconf(
    envvar_prefix="NEOGIT",
    environments=True,
    load_dotenv=True,
    # use absolute paths to import the conf from parent modules
    # from neogit.config import settings
    settings_files=[
        str(CUR_DIR / "default_settings.toml"),
        str(CUR_DIR / "settings.toml"),
        str(CUR_DIR / ".secrets.toml"),
    ],
    validators=[
        Validator("branch", must_exist=True),
        Validator("log_fmt", default=LOG_FMT),
        Validator("neo4j.proto", "neo4j.host", "neo4j.port", must_exist=True),
        Validator("neo4j.user", default=None),
        Validator("neo4j.password", default=None),
        Validator(
            "neo4j.creds",
            default=lambda _settings, _creds: (_settings.neo4j.user, _settings.neo4j.password)
            if _settings.neo4j.user or _settings.neo4j.password
            else None,
        ),
        # compute the URL from the settings if not provided by env var NEOGIT_NEO4J__URL
        Validator(
            "neo4j.url",
            default=lambda _settings, _url: f"{_settings.neo4j.proto}://{_settings.neo4j.host}:{_settings.neo4j.port}",
        ),
        Validator(
            "neo4j.url_full",
            default=lambda _settings, _url: f"{_settings.neo4j.proto}://{_settings.neo4j.user}:"
            f"{_settings.neo4j.password}@{_settings.neo4j.host}:{_settings.neo4j.port}",
        ),
        Validator("neo4j.http_url", default=lambda _settings, _url: f"http://{_settings.neo4j.host}:{NEO4J_HTTP_PORT}"),
        Validator("object.key", default=USER_DATA_DIR),
        Validator("object.secret", default=None),
        Validator("object.host", default=None),
        Validator("object.port", default=None),
        Validator("object.secure", default=None),
        Validator("object.region", default=None),
        Validator("object.ex_force_auth_url", default=None),
        Validator("object.ex_force_auth_version", default=None),
        Validator("object.ex_tenant_name", default=None),
        Validator("object.container_name", default=CONTAINER_NAME),
    ],
)


@dataclass
class ObjectConfig:
    provider: str
    key: str
    secret: Optional[str] = field(default=None)
    host: Optional[str] = field(default=None)
    port: Optional[int] = field(default=None)
    secure: Optional[bool] = field(default=None)
    region: Optional[str] = field(default=None)
    ex_force_auth_url: Optional[str] = field(default=None)
    ex_force_auth_version: Optional[str] = field(default=None)
    ex_tenant_name: Optional[str] = field(default=None)

    @staticmethod
    def from_settings(settings: LazySettings) -> "ObjectConfig":
        return ObjectConfig(
            settings.object.provider,
            settings.object.key,
            settings.object.secret,
            settings.object.host,
            settings.object.port,
            settings.object.secure,
            settings.object.region,
            settings.object.ex_force_auth_url,
            settings.object.ex_force_auth_version,
            settings.object.ex_tenant_name,
        )
