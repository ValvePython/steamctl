
import os
import json
import logging
from time import time
from io import open
from contextlib import contextmanager
from appdirs import AppDirs
from steamctl import __appname__

_LOG = logging.getLogger(__name__)
_appdirs = AppDirs(__appname__)

def ensure_data_dir(path):
    dirpath = os.path.dirname(path)

    if not os.path.exists(dirpath):
        _LOG.debug("Making missing dirs: %s", dirpath)
        os.makedirs(dirpath, 0o700)

class DataFile(object):
    _root_path = None

    def __init__(self, name, mode='r'):
        self.mode = mode
        self.path = os.path.join(self._root_path, name)

    def exists(self):
        return os.path.exists(self.path)

    def older_than(seconds=0, minutes=0, hours=0, days=0):
        delta = seconds + (minutes*60) + (hours*3600) + (days*86400)
        ts = os.path.getmtime(self.path)
        return ts + delta > time()

    def open(self, mode):
        _LOG.debug("Opening file (%s): %s", mode, self.path)
        ensure_data_dir(self.path)
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

class UserDataFile(DataFile):
    _root_path = _appdirs.user_data_dir

class UserCacheFile(DataFile):
    _root_path = _appdirs.user_cache_dir
