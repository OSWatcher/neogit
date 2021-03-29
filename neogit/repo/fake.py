from typing import Optional, Type

from py2neo.ogm import Model

from .abstract import AbstractGraphRepository


class FakeRepository(AbstractGraphRepository):
    def __init__(self, url: Optional[str] = None):
        super().__init__(url)

    def delete(self, obj: Model):
        pass

    def exists(self, obj: Model):
        pass

    def get(self, obj: Type[Model]):
        pass

    def match(self, obj: Type[Model]):
        pass

    def reload(self, obj: Model):
        pass

    def save(self, *obj: Model):
        pass
