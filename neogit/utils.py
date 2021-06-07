from typing import Tuple
from urllib.parse import ParseResult, urlparse, urlunparse


def uri_to_py2neo_uri(uri: str, auth: Tuple[str, str] = None) -> str:
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


def auth_to_netloc(netloc: str, auth: Tuple[str, str] = None) -> str:
    auth_str = ""
    if auth:
        auth_str = f"{auth[0]}:{auth[1]}@"
    return f"{auth_str}{netloc}"


def cypher_unescape(string: str) -> str:
    return string.strip("`")
