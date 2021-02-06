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

        if not args.skip_licenses:
            if not s.licenses and s.steam_id.type != s.steam_id.EType.AnonUser:
                s.wait_event(EMsg.ClientLicenseList, raises=False, timeout=10)

            cdn = s.get_cdnclient()
            cdn.load_licenses()

            for app_id in args.app_ids:
                if app_id not in cdn.licensed_app_ids:
                    LOG.error("No license available for App ID: %s (%s)", app_id, EResult.AccessDenied)
                    return 1  #error

        data = s.get_product_info(apps=args.app_ids)

        if not data:
            LOG.error("No results")
            return 1  # error

        data = data['apps']

        for k, v in data.items():
            json.dump(v, sys.stdout, indent=4, sort_keys=True)

