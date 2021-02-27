import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

import sys
import json
import codecs
import logging
import functools
from binascii import hexlify
from contextlib import contextmanager
from steam.exceptions import SteamError
from steam.enums import EResult
from steam.client import EMsg
from steam import webapi
from steam.utils import chunks
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session

webapi._make_requests_session = make_requests_session

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

def cmd_apps_list(args):
    resp = webapi.get('ISteamApps', 'GetAppList', version=2)

    apps = resp.get('applist', {}).get('apps', [])

    if not apps:
        LOG.error("Failed to get app list")
        return 1  # error

    if args.all:
        width = len(str(max(map(lambda app: app['appid'], apps))))

        for app in sorted(apps, key=lambda app: app['appid']):
            print(str(app['appid']).ljust(width), app['name'])

    else:
        with init_client(args) as s:
            if not s.licenses and s.steam_id.type != s.steam_id.EType.AnonUser:
                s.wait_event(EMsg.ClientLicenseList, raises=False, timeout=10)

            cdn = s.get_cdnclient()
            cdn.load_licenses()

            owned_apps = list(cdn.licensed_app_ids)

        apps = dict(map(lambda x: (x['appid'], x['name']), apps))
        width = len(str(max(owned_apps)))

        for app_id in sorted(owned_apps):
            print(str(app_id).ljust(width), apps.get(app_id, 'Unknown App {}'.format(app_id)))


def cmd_apps_item_def(args):
    app_id = args.app_id

    # special case apps
    if app_id in (440, 570, 620, 730, 205790):
        LOG.error("The app's item schema cannot be retrieved via this method")

        if app_id == 440:
            LOG.error("Use: steamctl webapi call IEconItems_440.GetSchemaItems")
        if app_id == 570:
            LOG.error("Use: steamctl webapi call IEconItems_570.GetSchemaURL")
            LOG.error("     steamctl depot download -a 570 --vpk --name '*pak01_dir.vpk:*/items_game.txt' --no-directories -o dota_items")
        if app_id == 620:
            LOG.error("Use: steamctl webapi call IEconItems_620.GetSchema")
        if app_id == 730:
            LOG.error("Use: steamctl webapi call IEconItems_730.GetSchema")
            LOG.error("     steamctl depot download -a 730 --regex 'items_game(_cdn)?\.txt$' --no-directories --output csgo_item_def")
        if app_id == 205790:
            LOG.error("Use: steamctl webapi call IEconItems_205790.GetSchemaURL")

        return 1 # error

    # regular case
    with init_client(args) as s:
        resp = s.send_um_and_wait("Inventory.GetItemDefMeta#1", {'appid': app_id})

        if resp.header.eresult != EResult.OK:
            LOG.error("Request failed: %r", EResult(resp.header.eresult))
            return 1  # error

        digest = resp.body.digest

        sess = make_requests_session()
        resp = sess.get('https://api.steampowered.com/IGameInventory/GetItemDefArchive/v1/',
                        params={'appid': app_id, 'digest': resp.body.digest},
                        stream=True)

        if resp.status_code != 200:
            LOG.error("Request failed: HTTP %s", resp.status_code)
            return 1  # error

        resp.raw.read = functools.partial(resp.raw.read, decode_content=True)
        reader = codecs.getreader('utf-8')(resp.raw, 'replace')

        for chunk in iter(lambda: reader.read(8096), ''):
            if chunk[-1] == '\x00':
                chunk = chunk[:-1]

            sys.stdout.write(chunk)
