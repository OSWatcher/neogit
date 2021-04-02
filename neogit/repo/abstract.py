from abc import ABC, abstractmethod
from typing import Optional, Type

from py2neo.ogm import Model

DEFAULT_URL = "bolt://localhost:7687"


class AbstractGraphRepository(ABC):
    """
    Abstract repository pattern for graph databases
    """

    def __init__(self, url: Optional[str]):
        self._url = url
        if url is None:
            self._url = DEFAULT_URL

    @abstractmethod
    def delete(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def exists(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def get(self, obj: Type[Model], primary_value=None):
        raise NotImplementedError

    @abstractmethod
    def match(self, obj: Type[Model], primary_value=None):
        raise NotImplementedError

    @abstractmethod
    def reload(self, obj: Model):
        raise NotImplementedError

    @abstractmethod
    def save(self, *obj: Model):
        raise NotImplementedError
