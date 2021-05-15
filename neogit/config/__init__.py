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

settings = Dynaconf(
    envvar_prefix="NEOGIT",
    environments=True,
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
        # compute the URL from the settings if not provided by env var NEOGIT_NEO4J__URL
        Validator(
            "neo4j.url",
            default=lambda _settings, _url: f"{_settings.neo4j.proto}://{_settings.neo4j.host}:{_settings.neo4j.port}",
        ),
        Validator("object.key", default=USER_DATA_DIR),
        Validator("object.secret_key", default=None),
        Validator("object.host", default=None),
        Validator("object.port", default=None),
        Validator("object.secure", default=None),
        Validator("object.container_name", default=CONTAINER_NAME),
    ],
)


@dataclass
class ObjectConfig:
    provider: str
    key: str
    secret_key: Optional[str] = field(default=None)
    host: Optional[str] = field(default=None)
    port: Optional[int] = field(default=None)
    secure: Optional[bool] = field(default=None)

    @staticmethod
    def from_settings(settings: LazySettings) -> "ObjectConfig":
        return ObjectConfig(
            settings.object.provider,
            settings.object.key,
            settings.object.secret_key,
            settings.object.host,
            settings.object.port,
            settings.object.secure,
        )
