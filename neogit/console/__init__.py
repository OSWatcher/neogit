from .abstract import AbstractConsoleAdapter, TaskPool
from .empty import EmptyConsoleAdapter
from .rich import RichConsoleAdapter

DEFAULT_ADAPTER = EmptyConsoleAdapter()
