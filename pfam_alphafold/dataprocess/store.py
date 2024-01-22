import bisect
import heapq
import os
import pickle
import struct
from dataclasses import dataclass, field
from tempfile import mkstemp
from typing import Any, Iterable

from . import io


@dataclass
class SimpleStore:
    path: str
    mode: str = "r"
    keys: list[str] = field(default_factory=list, init=False)
    offsets: list[int] = field(default_factory=list, init=False)
    buffer: dict[str, Any] = field(default_factory=dict, init=False)
    # Read mode only
    offset_index: int = field(default=-1, init=False)
    # Write mode only
    tempbuffersize: int = 1000000
    tempbuffer: list[Any] = field(default_factory=list, init=False)
    files: list[str] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.path = os.path.abspath(self.path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        if self.mode == "r":
            # Load index
            self.load()

    def add(self, key: str, value: Any):
        self.tempbuffer.append((key, value))
        if len(self.tempbuffer) == self.tempbuffersize:
            self.dump()

    def dump(self):
        if self.tempbuffer:
            fd, path = mkstemp(prefix=os.path.basename(self.path),
                               dir=os.path.dirname(self.path))
            with open(fd, "wb") as fh:
                for item in sorted(self.tempbuffer, key=lambda x: x[0]):
                    pickle.dump(item, fh)

            self.files.append(path)
            self.tempbuffer.clear()

    @staticmethod
    def iter_dump(file: str):
        with open(file, "rb") as fh:
            while True:
                try:
                    yield pickle.load(fh)
                except EOFError:
                    break

    def build(self, iterable: Iterable | None = None,
              buffersize: int = 100000,
              verbose: bool = False):
        self.dump()
        self.buffer.clear()
        self.keys.clear()
        self.offsets.clear()
        with open(self.path, "wb") as fh:
            fh.write(struct.pack("<Q", 0))

            if iterable is None:
                iterable = [self.iter_dump(path) for path in self.files]

            progress = 0
            step = milestone = 1e7
            for key, value in heapq.merge(*iterable, key=lambda x: x[0]):
                self.buffer[key] = value

                if len(self.buffer) == buffersize:
                    self.keys.append(min(self.buffer))
                    self.offsets.append(fh.tell())
                    pickle.dump(self.buffer, fh)
                    progress += len(self.buffer)
                    self.buffer.clear()

                    if verbose and progress >= milestone:
                        io.log(f"\t{progress:,}")
                        milestone += step

            if self.buffer:
                self.keys.append(min(self.buffer))
                self.offsets.append(fh.tell())
                pickle.dump(self.buffer, fh)
                progress += len(self.buffer)
                self.buffer.clear()

            offset = fh.tell()
            pickle.dump(self.keys, fh)
            pickle.dump(self.offsets, fh)

            fh.seek(0)
            fh.write(struct.pack("<Q", offset))

            if verbose:
                io.log(f"\t{progress:,}")

        for path in self.files:
            os.unlink(path)

    def load(self, offset: int = 0):
        with open(self.path, "rb") as fh:
            if offset > 0:
                fh.seek(offset)
                self.buffer = pickle.load(fh)
            else:
                offset, = struct.unpack("<Q", fh.read(8))
                fh.seek(offset)
                self.keys = pickle.load(fh)
                self.offsets = pickle.load(fh)

    def __getitem__(self, item):
        if item in self.buffer:
            return self.buffer[item]

        i = bisect.bisect_right(self.keys, item) - 1
        if i < 0 or i == self.offset_index:
            raise KeyError(item)

        self.offset_index = i

        try:
            offset = self.offsets[i]
        except IndexError:
            raise KeyError(item)

        self.load(offset)
        return self.buffer[item]

    def items(self):
        for offset in self.offsets:
            self.load(offset)
            for key in sorted(self.buffer):
                value = self.buffer[key]
                yield key, value
