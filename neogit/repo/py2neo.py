from py2neo.ogm import Model, Repository

from .abstract import AbstractGraphRepository


class Py2NeoRepository(AbstractGraphRepository):
    def __init__(self, url: str):
        self._repo = Repository(url)

    def delete(self, obj: Model):
        return self._repo.delete(obj)

    def exists(self, obj: Model):
        return self._repo.exists(obj)

    def get(self, obj: Model):
        return self._repo.get(obj)

    def match(self, obj: Model):
        return self._repo.match(obj)

    def reload(self, obj: Model):
        return self._repo.reload(obj)

    def save(self, *obj: Model):
        return self._repo.save(*obj)
