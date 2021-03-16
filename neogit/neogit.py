"""Contains main Neogit class"""
from typing import Tuple

from neo4j import GraphDatabase

DEFAULT_NEO4J_URI = "neo4j://localhost:7687"


class Neogit:
    def __init__(self, uri: str = None, auth: Tuple[str, str] = None):
        if uri and not isinstance(uri, str):
            raise TypeError("uri should be a string")
        if auth and not isinstance(auth, tuple):
            raise TypeError("auth should be a tuple")
        self._uri = uri if uri is not None else DEFAULT_NEO4J_URI
        self._auth = auth
        self._driver = GraphDatabase.driver(self._uri, auth=self._auth)
