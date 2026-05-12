from .abstract import AbstractConsoleAdapter
from .empty import EmptyConsoleAdapter
from .rich import RichConsoleAdapter

DEFAULT_ADAPTER = EmptyConsoleAdapter()

__all__ = ["AbstractConsoleAdapter", "EmptyConsoleAdapter", "RichConsoleAdapter", "DEFAULT_ADAPTER"]
