
import os
import re
import json
import logging
from time import time
from io import open
from contextlib import contextmanager
import fnmatch
import shutil
from collections import UserDict
import sqlite3
from appdirs import AppDirs
from steamctl import __appname__

_LOG = logging.getLogger(__name__)
_appdirs = AppDirs(__appname__)

def ensure_dir(path, mode=0o750):
    dirpath = os.path.dirname(path)

    if not os.path.exists(dirpath):
        _LOG.debug("Making dirs: %s", dirpath)
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
        self.path = normpath(os.path.join(self._root_path, relpath))
        self.filename = os.path.basename(self.path)

    def __repr__(self):
        return "%s(%r, mode=%r)" % (
            self.__class__.__name__,
            self.relpath,
            self.mode,
            )

    def exists(self):
        return os.path.exists(self.path)

    def mkdir(self):
        ensure_dir(self.path, 0o700)

    def older_than(seconds=0, minutes=0, hours=0, days=0):
        delta = seconds + (minutes*60) + (hours*3600) + (days*86400)
        ts = os.path.getmtime(self.path)
        return ts + delta > time()

    def open(self, mode):
        _LOG.debug("Opening file (%s): %s", mode, self.path)
        self.mkdir()
        return open(self.path, mode)

    def read_text(self):
        if self.exists():
            with self.open('r') as fp:
                return fp.read()

    def write_text(self, data):
        with self.open('w') as fp:
            fp.write(data)

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

    def secure_remove(self):
        _LOG.debug("Securely removing file: %s", self.path)

        if self.exists():
            with open(self.path, 'r+b') as fp:
                size = fp.seek(0, 2)

                fp.seek(0)
                chunk = b'0' * 4096

                while fp.tell() + 4096 < size:
                    fp.write(chunk)
                fp.write(chunk[:max(size - fp.tell(), 0)])

                fp.flush()
                os.fsync(fp.fileno())

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
        self.path = normpath(os.path.join(self._root_path, path))

        if self.exists() and not os.path.isdir(self.path):
            raise ValueError("Path is not a directory: %s" % self.path)

    def mkdir(self):
        ensure_dir(self.path + os.sep, 0o700)

    def exists(self):
        return os.path.exists(self.path)

    def remove(self):
        _LOG.debug("Removing directory: %s", self.path)
        shutil.rmtree(self.path)

    def iter_files(self, pattern=None, recurse=False):
        if not os.path.exists(self.path):
            return

        for root, dirs, files in os.walk(self.path):
            if not recurse and self.path != root:
                break

            if pattern:
                files =  fnmatch.filter(files, pattern)

            yield from (self._file_type(os.path.join(root, filename)) for filename in files)

class UserDataDirectory(DirectoryBase):
    _root_path = _appdirs.user_data_dir
    _file_type = UserDataFile

class UserCacheDirectory(DirectoryBase):
    _root_path = _appdirs.user_cache_dir
    _file_type = UserCacheFile


class SqliteDict(UserDict):
    def __init__(self, path=':memory:'):
        if isinstance(path, FileBase):
            path.mkdir()
            path = path.path

        self._db = sqlite3.connect(path)
        self._db.execute('CREATE TABLE IF NOT EXISTS kv (key INTEGER PRIMARY KEY, value TEXT)')
        self._db.commit()

    def __len__(self):
         return self._db.execute('SELECT count(*) FROM kv').fetchone()[0]

    def __contain__(self, key):
        return self.get(key) is not None

    def get(self, key, default=None):
        row = self._db.execute('SELECT value FROM kv WHERE key = ?', (key,)).fetchone()
        return row[0] if row else default

    def __getitem__(self, key):
        val = self.get(key)

        if val is None:
            raise KeyError(key)
        else:
            if val and val[0] == '{' and val[-1] == '}':
                val = json.loads(val)
            return val

    def __setitem__(self, key, val):
        if isinstance(val, str):
            pass
        elif isinstance(val, dict):
            val = json.dumps(val)
        else:
            raise TypeError("Only str or dict types are allowed")

        self._db.execute("REPLACE INTO kv VALUES (?, ?)", (key, val))

    def items(self):
        for item in self._db.execute("SELECT key, value FROM kv ORDER BY key ASC"):
            yield item

    def commit(self):
        self._db.commit()

    def __del__(self):
        self.commit()

        try:
            self._db.close(do_log=False, force=True)
        except Exception:
            pass
