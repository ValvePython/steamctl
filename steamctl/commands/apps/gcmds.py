import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

import sys
import json
import logging
from binascii import hexlify
from contextlib import contextmanager
from steam.exceptions import SteamError
from steam.enums import EResult
from steam.client import EMsg
from steamctl.clients import CachingSteamClient

LOG = logging.getLogger(__name__)

@contextmanager
def init_client(args):
    s = CachingSteamClient()
    s.login_from_args(args)
    yield s
    s.disconnect()

def cmd_apps_product_info(args):
    with init_client(args) as s:
        s.check_for_changes()
        data = s.get_product_info(apps=args.app_ids)

        if not data:
            LOG.error("No results")
            return 1  # error

        data = data['apps']

        for k, v in data.items():
            json.dump(v, sys.stdout, indent=4, sort_keys=True)

