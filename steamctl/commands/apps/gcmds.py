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
from time import time
from binascii import hexlify
from contextlib import contextmanager
from steam.exceptions import SteamError
from steam.enums import EResult, EPurchaseResultDetail
from steam.client import EMsg
from steam.utils import chunks
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_datetime
from steam.enums import ELicenseType, ELicenseFlags, EBillingType, EType
from steam.core.msg import MsgProto
from steamctl.commands.apps.enums import EPaymentMethod, EPackageStatus
from steamctl.utils.apps import get_app_names

LOG = logging.getLogger(__name__)

@contextmanager
def init_client(args):
    s = CachingSteamClient()
    s.login_from_args(args)
    yield s
    s.disconnect()

def cmd_apps_activate_key(args):
    with init_client(args) as s:
        for key in args.keys:
            print("-- Activating: {}".format(key))
            result, detail, receipt = s.register_product_key(key)

            detail = EPurchaseResultDetail(detail)

            print(f"Result: {result.name} ({result:d}) Detail: {detail.name} ({detail:d})")

            products = [product.get('ItemDescription', '<NoName>') for product in receipt.get('lineitems', {}).values()]

            if result == EResult.OK:
                print("Products:", ', '.join(products) if products else "None")
            else:
                return 1  # error

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
    app_names = get_app_names()

    if args.all:
        for app_id, name in app_names.items():
            if app_id >= 0:
                print(app_id, name)

    else:
        with init_client(args) as s:
            if not s.licenses and s.steam_id.type != s.steam_id.EType.AnonUser:
                s.wait_event(EMsg.ClientLicenseList, raises=False, timeout=10)

            cdn = s.get_cdnclient()
            cdn.load_licenses()

        for app_id in sorted(cdn.licensed_app_ids):
            print(app_id, app_names.get(app_id, 'Unknown App {}'.format(app_id)))


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

# ---- licenses section

def cmd_apps_licenses_list(args):
    with init_client(args) as s:
        app_names = get_app_names()

        if s.steam_id.type == EType.AnonUser:
            from steam.protobufs.steammessages_clientserver_pb2 import CMsgClientLicenseList
            s.licenses = {
                17906: CMsgClientLicenseList.License(package_id=17906, license_type=1)
            }

        # ensure that the license list has loaded
        if not s.licenses:
            s.wait_event(EMsg.ClientLicenseList)

        for chunk in chunks(list(s.licenses), 100):
            packages = s.get_product_info(packages=chunk)['packages']

            for pkg_id in chunk:
                license = s.licenses[pkg_id]
                info = packages[pkg_id]

                # skip licenses not granting specified app ids
                if args.app and set(info['appids'].values()).isdisjoint(args.app):
                    continue

                # skip licenses not matching specified billingtype(s)
                if args.billingtype and EBillingType(info['billingtype']).name not in args.billingtype:
                    continue

                print(f"License: { pkg_id }")
                print(f"  Type:             { ELicenseType(license.license_type).name } ({license.license_type})")
                print(f"  Created:          { fmt_datetime(license.time_created) }")
                print(f"  Purchase country: { license.purchase_country_code }")
                print(f"  Payment method:   { EPaymentMethod(license.payment_method).name } ({license.payment_method})")

                flags = ', '.join((flag.name for flag in ELicenseFlags if flag & license.flags))

                print(f"  Flags:            { flags }")
                print(f"  Change number:    { license.change_number }")
                print(f"  SteamDB:          https://steamdb.info/sub/{ pkg_id }/")
                if 'billingtype' in info:
                    print(f"  Billing Type:     { EBillingType(info['billingtype']).name } ({info['billingtype']})")
                if 'status' in info:
                    print(f"  Status:           { EPackageStatus(info['status']).name } ({info['status']})")

                if info.get('extended', None):
                    print("  Extended:")
                    for key, val in info['extended'].items():
                        print(f"    {key}: {val}")

                if info.get('appids', None):
                    print("  Apps:")
                    for app_id in info['appids'].values():
                        app_name = app_names.get(app_id, f'Unknown App {app_id}')
                        print(f"    {app_id}: {app_name}")

def cmd_apps_licenses_add(args):
    with init_client(args) as s:
        web = s.get_web_session()
        app_names = get_app_names()

        for pkg_id in args.pkg_ids:
            if pkg_id in s.licenses:
                print(f'Already owned package: {pkg_id}')
                continue

            resp = web.post(f'https://store.steampowered.com/checkout/addfreelicense/{pkg_id}',
                            data={'ajax': 'true', 'sessionid': web.cookies.get('sessionid', domain='store.steampowered.com')},
                            )

            if resp.status_code != 200:
                LOG.error(f'Request failed with HTTP code {resp.status_code}')
                return 1  # error

            if resp.json() is None:
                print(f"Failed package: {pkg_id}")
                continue

            if pkg_id not in s.licenses:
                s.wait_event(EMsg.ClientLicenseList, timeout=2)

            if pkg_id in s.licenses:
                print(f'Activated package: {pkg_id}')

                for app_id in s.get_product_info(packages=[pkg_id])['packages'][pkg_id]['appids'].values():
                    app_name = app_names.get(app_id, f'Unknown App {app_id}')
                    print(f"  + {app_id}: {app_name}")
            else:
                # this shouldn't happen
                print(f'Activated package: {pkg_id} (BUT, NO LICENSE ON ACCOUNT?)')

def cmd_apps_licenses_remove(args):
    with init_client(args) as s:
        web = s.get_web_session()
        app_names = get_app_names()

        for pkg_id in args.pkg_ids:
            if pkg_id not in s.licenses:
                print(f'No license for: {pkg_id}')
                continue

            info = s.get_product_info(packages=[pkg_id])['packages'][pkg_id]

            resp = web.post(f'https://store.steampowered.com/account/removelicense',
                            data={'packageid': pkg_id, 'sessionid': web.cookies.get('sessionid', domain='store.steampowered.com')},
                            )

            if resp.status_code != 200:
                LOG.error(f'Request failed with HTTP code {resp.status_code}')
                return 1  # error

            if resp.json()['success']:
                print(f"Removed package: {pkg_id}")

                for app_id in info['appids'].values():
                    app_name = app_names.get(app_id, f'Unknown App {app_id}')
                    print(f"  - {app_id}: {app_name}")
            else:
                print(f"Failed to remove: {pkg_id}")
