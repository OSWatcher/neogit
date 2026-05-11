import logging
from contextlib import AbstractContextManager, ExitStack, contextmanager
from logging.config import dictConfig
from pathlib import Path
from types import TracebackType
from typing import Optional, Self, Tuple
from urllib.parse import ParseResult, urlparse, urlunparse

import coloredlogs
import yaml
from attrs import Factory, define, field

DEFAULT_CLASS_LOGGER = Factory(
    lambda self: logging.getLogger(f"{self.__module__}.{self.__class__.__name__}"),
    takes_self=True,
)


def uri_to_py2neo_uri(uri: str, auth: Optional[Tuple[str, str]] = None) -> str:
    """
    convert a uri to py2neo uri, adding credentials information

    >>> uri_to_py2neo_uri("bolt://localhost:7687")
    'bolt://localhost:7687'
    >>> uri_to_py2neo_uri("bolt://localhost:7687", auth=('david', 'secret'))
    'bolt://david:secret@localhost:7687'
    """
    parsed_uri = urlparse(uri)
    netloc = auth_to_netloc(parsed_uri.netloc, auth)
    new_parts = ParseResult(
        parsed_uri.scheme, netloc, parsed_uri.path, parsed_uri.params, parsed_uri.query, parsed_uri.fragment
    )
    return urlunparse(new_parts)


def auth_to_netloc(netloc: str, auth: Optional[Tuple[str, str]] = None) -> str:
    auth_str = ""
    if auth:
        auth_str = f"{auth[0]}:{auth[1]}@"  # noqa: E231
    return f"{auth_str}{netloc}"


def cypher_unescape(string: str) -> str:
    return string.strip("`")


@define(auto_attribs=True)
class BetterContextManager(AbstractContextManager):
    logger: logging.Logger = field(default=DEFAULT_CLASS_LOGGER, init=False)
    ex: ExitStack = field(default=Factory(ExitStack), init=False)

    def __enter__(self):
        with self._cleanup_on_error():
            return self.safe_enter()

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> bool | None:
        self.ex.__exit__(__exc_type, __exc_value, __traceback)
        return super().__exit__(__exc_type, __exc_value, __traceback)

    def safe_enter(self) -> Self:
        return self

    @contextmanager
    def _cleanup_on_error(self):
        with ExitStack() as stack:
            stack.push(self)
            yield
            # The validation check passed and didn't raise an exception
            # Accordingly, we want to keep the resource, and pass it
            # back to our caller
            stack.pop_all()


def setup_logging(debug_enabled: bool, basic_config: bool = False):
    log_config_path = Path(__file__).parent / "logging.yaml"
    with open(log_config_path) as f:
        config = yaml.safe_load(f)

    try:
        if debug_enabled:
            config["root"]["level"] = "DEBUG"
    except KeyError:
        root_level = "INFO"
    else:
        root_level = config["root"]["level"]

    formatter = config["formatters"]["simple"]["format"]

    dictConfig(config)
    if basic_config:
        coloredlogs.install(level=root_level, fmt=formatter)
