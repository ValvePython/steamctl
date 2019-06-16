
import os
import re
import json
import logging
from time import time
from io import open
from contextlib import contextmanager
import fnmatch
from appdirs import AppDirs
from steamctl import __appname__

_LOG = logging.getLogger(__name__)
_appdirs = AppDirs(__appname__)

def ensure_dir(path, mode=0o750):
    dirpath = os.path.dirname(path)

    if not os.path.exists(dirpath):
        _LOG.debug("Making missing dirs: %s", dirpath)
        os.makedirs(dirpath, mode)

def normpath(path):
    if os.sep == '/':
        path = path.replace('\\', '/')
    return os.path.normpath(path)

def sanitizerelpath(path):
    return re.sub(r'^((\.\.)?[\\/])*', '', normpath(path))


class FileBase(object):
    _root_path = None

    def __init__(self, relpath, mode='r'):
        self.mode = mode
        self.relpath = relpath
        self.path = os.path.join(self._root_path, relpath)
        self.filename = os.path.basename(self.path)

    def __repr__(self):
        return "%s(%r, mode=%r)" % (
            self.__class__.__name__,
            self.relpath,
            self.mode,
            )

    def exists(self):
        return os.path.exists(self.path)

    def older_than(seconds=0, minutes=0, hours=0, days=0):
        delta = seconds + (minutes*60) + (hours*3600) + (days*86400)
        ts = os.path.getmtime(self.path)
        return ts + delta > time()

    def open(self, mode):
        _LOG.debug("Opening file (%s): %s", mode, self.path)
        ensure_dir(self.path, 0o700)
        return open(self.path, mode)

    def read_full(self):
        if self.exists():
            with self.open('r') as fp:
                return fp.read()

    def read_json(self):
        if self.exists():
            with self.open('r') as fp:
                return json.load(fp)

    def write_json(self, data, pretty=True):
        with self.open('w') as fp:
            if pretty:
                json.dump(data, fp, indent=4, sort_keys=True)
            else:
                json.dump(data, fp)

    def remove(self):
        _LOG.debug("Removing file: %s", self.path)

        if self.exists():
            os.remove(self.path)

    def __enter__(self):
        self._fp = self.open(self.mode)
        return self._fp

    def __exit__(self, exc_type, exc_value, traceback):
        self._fp.close()

class UserDataFile(FileBase):
    _root_path = _appdirs.user_data_dir

class UserCacheFile(FileBase):
    _root_path = _appdirs.user_cache_dir

class DirectoryBase(object):
    _root_path = None
    _file_type = None

    def __init__(self, path='.'):
        self.path = os.path.join(self._root_path, path)

        if self.exists() and not os.path.isdir(self.path):
            raise ValueError("Path is not a directory: %s" % self.path)

    def exists(self):
        return os.path.exists(self.path)

    def list_files(self, pattern=None):
        if not os.path.exists(self.path):
            return []

        for root, dirs, files in os.walk(self.path):
            if pattern:
                files =  fnmatch.filter(files, pattern)
            return [self._file_type(os.path.join(self.path, filename)) for filename in files]

class UserDataDirectory(DirectoryBase):
    _root_path = _appdirs.user_data_dir
    _file_type = UserDataFile

class UserCacheDirectory(DirectoryBase):
    _root_path = _appdirs.user_cache_dir
    _file_type = UserCacheFile
