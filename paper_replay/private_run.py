"""Exclusive outputs for trusted local runs, not a sandbox."""
import os
from pathlib import Path
from .core import Invalid


def parents(path):
    if path.is_symlink():
        raise Invalid('output parent link is not allowed')
    if path.exists():
        if not path.is_dir():
            raise Invalid('output parent must be a directory')
        return
    parents(path.parent)
    path.mkdir(mode=0o700)


class Output:
    def __init__(self, path):
        self.path = Path(os.path.abspath(path))  # do not resolve the output leaf
        self.fd = None
        parents(self.path.parent)
        self.path.mkdir(mode=0o700)
        self.identity = self.path.stat()
        if os.name == 'posix':
            self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            info = os.fstat(self.fd)
            if (info.st_dev, info.st_ino) != (self.identity.st_dev, self.identity.st_ino):
                self.close()
                raise Invalid('output directory changed')

    def check(self):
        now = self.path.lstat()
        if self.path.is_symlink() or (now.st_dev, now.st_ino) != (self.identity.st_dev, self.identity.st_ino):
            raise Invalid('output directory changed')

    def open(self, name):
        self.check()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
        fd = os.open(name if self.fd is not None else self.path / name,
                     flags, 0o600, **({'dir_fd': self.fd} if self.fd is not None else {}))
        return os.fdopen(fd, 'wb')

    def write(self, name, data):
        with self.open(name) as stream:
            stream.write(data)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
