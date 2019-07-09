
import sys
import logging
from tqdm import tqdm as _tqdm


class TQDMHandler(logging.Handler):
    def __init__(self, tqdm_instance):
        self._tqdm = tqdm_instance
        logging.Handler.__init__(self)
    def emit(self, record):
        message = self.format(record).rstrip()
        self._tqdm.write(message, sys.stderr)
    def flush(self):
        pass

class tqdm(_tqdm):
    _xclosed = False

    def __init__(self, *args, **kwargs):
        _tqdm.__init__(self, *args, **kwargs)
        self._xloghandler = TQDMHandler(self)

        log = logging.getLogger()
        self._xoldhandler = log.handlers.pop()
        self._xloghandler.level = self._xoldhandler.level
        self._xloghandler.formatter = self._xoldhandler.formatter
        log.addHandler(self._xloghandler)

        self._xrootlog = log

    def write(self, s, file=sys.stdout):
        super().write(s, file)

    def close(self):
        _xclosed = True
        _tqdm.close(self)
        self._xrootlog.removeHandler(self._xloghandler)
        self._xrootlog.addHandler(self._xoldhandler)

    def gevent_refresh_loop(self):
        from gevent import sleep
        while not self._xclosed:
            self.refresh()
            sleep(0.5)

class fake_tqdm(object):
    def write(self, s):
        print(s)
    def update(self, n):
        pass
    def refresh(self):
        pass
    def close(self):
        pass
