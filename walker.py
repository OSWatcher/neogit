#!/usr/bin/env python3

import argparse
import hashlib
import os
from pathlib import Path
from queue import Queue
from threading import Thread

import pypeln

MAX_WORKERS = 12


class InspectableQueue(Queue):
    def inspect(self):
        with self.mutex:
            return list(self.queue)


# backport Python3.9
def is_relative_to(p1: Path, p2: Path) -> bool:
    try:
        p1.relative_to(p2)
    except ValueError:
        return False
    else:
        return True


def explore_rec(root: Path, queue: Queue):
    def explore_sub(directory: Path):
        # pre order

        with os.scandir(directory) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    path_entry = Path(entry.path)
                    explore_sub(path_entry)
        # # post order
        queue.put(directory)
        print(f"📁 {directory}")

    explore_sub(root)
    queue.put(None)


def explore_iter(root: Path, queue: InspectableQueue):
    visited = set()
    stack = []
    stack.append(root)

    while stack:
        # pop next
        cur_dir = stack.pop()

        if cur_dir not in visited:
            # visit DFS
            stack.append(cur_dir)

            with os.scandir(cur_dir) as it:
                dirs = [entry for entry in it if entry.is_dir(follow_symlinks=False)]
                for entry in dirs:
                    path_entry = Path(entry.path)
                    stack.append(path_entry)
            visited.add(cur_dir)
        else:
            # remove from set to avoid a huge set in RAM
            visited.remove(cur_dir)

            # TODO: add to queue only if cur_dir Path is not relative to any task directories
            # # add to task queue if possible
            # stack.append(cur_dir)
            # tasks: List[Path] = queue.inspect()
            # found = False
            # print(f"tasks: {tasks}")
            # for candidate in reversed(stack[1: len(stack) - 1]):
            #     print(f"testing candidate: {candidate}")
            #     relatives = [t for t in tasks if is_relative_to(t, candidate)]
            #     if relatives:
            #         stack.pop()
            #         stack.insert(1, candidate)
            #         continue
            #     else:
            #         # found candidate
            #         stack.append(candidate)
            #         break
            # candidate = stack.pop()
            candidate = cur_dir
            queue.put(candidate)

    # done
    queue.put(None)


def process_task(item):
    # compute all sha1s
    with os.scandir(item) as it:
        sha1 = hashlib.sha1()
        for entry in it:
            if entry.is_file():
                buffer = bytearray(65536)
                view = memoryview(buffer)
                with open(entry, "rb", buffering=0) as f:
                    for block in iter(lambda: f.readinto(view), 0):
                        sha1.update(view[:block])
        print(f"📁 {item}: {sha1.hexdigest()}")
        return sha1.hexdigest()

    # simulate cpu stress


def iterable_queue(queue: InspectableQueue):
    while True:
        item = queue.get()
        if item is None:
            return
        yield item


parser = argparse.ArgumentParser()
parser.add_argument("directory")
args = parser.parse_args()

directory = args.directory

queue = InspectableQueue(maxsize=50)

fs_walker = Thread(target=explore_iter, name="fs_walker", args=(directory, queue))
fs_walker.start()


stage = pypeln.process.map(process_task, iterable_queue(queue), workers=MAX_WORKERS)
#
for _res in stage:
    pass

fs_walker.join()
