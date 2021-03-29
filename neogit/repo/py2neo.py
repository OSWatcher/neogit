from typing import Optional, Type

from py2neo.ogm import Model, Repository

from .abstract import AbstractGraphRepository


class Py2NeoRepository(AbstractGraphRepository):
    def __init__(self, url: Optional[str] = None):
        super().__init__(url)
        self._repo = Repository(self._url)

    def delete(self, obj: Model):
        return self._repo.delete(obj)

    def exists(self, obj: Model):
        return self._repo.exists(obj)

    def get(self, obj: Type[Model]):
        return self._repo.get(obj)

    def match(self, obj: Type[Model]):
        return self._repo.match(obj)

    def reload(self, obj: Model):
        return self._repo.reload(obj)

    def save(self, *obj: Model):
        return self._repo.save(*obj)
