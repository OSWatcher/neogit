from pathlib import Path
from threading import local

from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, FileSizeColumn, Progress, SpinnerColumn, TotalFileSizeColumn

from .abstract import AbstractConsoleAdapter


class RichConsoleAdapter(AbstractConsoleAdapter):
    """This adapter will use Rich library for console output"""

    def __init__(self):
        # sha1 progress bar
        self._sha1_progress = Progress(
            SpinnerColumn(),
            # centered text
            "{task.description}",
            BarColumn(bar_width=None),
            FileSizeColumn(),
            TotalFileSizeColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
        )
        # main panel
        self._panel = Panel(self._sha1_progress, title="SHA1 Pool")
        self._live = Live(self._panel, refresh_per_second=4)
        self._local = local()

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()

    def set_sha1_task(self, filepath: Path, size: int):
        try:
            task = self._local.sha1_task
        except AttributeError:
            # create new task for this thread
            task = self._sha1_progress.add_task(description=str(filepath), total=size)
            self._local.sha1_task = task
        else:
            # set description and total
            self._sha1_progress.update(task, description=str(filepath), total=size, completed=0)

    def update_sha1_task(self, advance: int):
        try:
            task = self._local.sha1_task
        except AttributeError:
            raise RuntimeError("SHA1 task not created")
        else:
            self._sha1_progress.update(task, advance=advance)
