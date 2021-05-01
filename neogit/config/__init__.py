from pathlib import Path

from dynaconf import Dynaconf, Validator

CUR_DIR = Path(__file__).parent

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
        Validator("log_fmt", must_exist=True),
        Validator("neo4j.proto", "neo4j.host", "neo4j.port", must_exist=True),
        # compute the URL from the settings if not provided by env var NEOGIT_NEO4J__URL
        Validator(
            "neo4j.url",
            default=lambda _settings, _url: f"{_settings.neo4j.proto}://{_settings.neo4j.host}:{_settings.neo4j.port}",
        ),
    ],
)
