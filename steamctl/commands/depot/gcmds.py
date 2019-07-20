import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

from gevent.pool import Pool as GPool

import os
import sys
import logging
from io import open
from contextlib import contextmanager
from re import search as re_search
from fnmatch import fnmatch
from steam import webapi
from steam.exceptions import SteamError
from steam.enums import EResult, EDepotFileFlag
from steamctl.clients import CachingSteamClient, CTLDepotManifest
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_size, fmt_datetime
from steamctl.utils.tqdm import tqdm, fake_tqdm
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

@contextmanager
def init_clients(args):
    if getattr(args, 'file', None):
        manifest = CTLDepotManifest(None, -1, args.file.read())
        yield None, None, [manifest]
    else:
        s = CachingSteamClient()
        if args.cell_id is not None:
            s.cell_id = args.cell_id
        cdn = s.get_cdnclient()

        # only login if we dont have depot decryption key
        if (not args.app or not args.depot or not args.manifest or
            args.depot not in cdn.depot_keys):
            result = s.login_from_args(args)

            if result == EResult.OK:
                LOG.info("Login to Steam successful")
            else:
                LOG.error("Failed to login: %r" % result)
                return 1  # error

        if args.app and args.depot and args.manifest:
            try:
                manifests = [cdn.get_manifest(args.app, args.depot, args.manifest)]
            except SteamError as exp:
                if exp.eresult == EResult.AccessDenied:
                    raise SteamError("This account doesn't have access to the app depot", exp.eresult)
                else:
                    raise
        else:
            LOG.info("Checking licenses")
            cdn.load_licenses()

            if args.app not in cdn.licensed_app_ids:
                raise SteamError("No license available for App ID: %s" % args.app, EResult.AccessDenied)

            LOG.info("Checking change list")
            cdn.check_for_changes()

            def branch_filter(depot_id, info):
                if args.depot is not None:
                    if args.depot != depot_id:
                        return False

                if args.os != 'any':
                    if args.os[-2:] == '64':
                        os, arch = args.os[:-2], args.os[-2:]
                    else:
                        os, arch = args.os, None

                    config = info.get('config', {})

                    if 'oslist' in config and (os not in config['oslist'].split(',')):
                        return False
                    if 'osarch' in config and config['osarch'] != arch:
                        return False

                return True

            LOG.info("Getting manifests for 'public' branch")

            manifests = []
            for manifest in cdn.get_manifests(args.app, filter_func=branch_filter, decrypt=False):
                if manifest.depot_id not in cdn.licensed_depot_ids:
                    LOG.error("No license for depot: %r" % manifest)
                    continue
                if manifest.filenames_encrypted:
                    try:
                        manifest.decrypt_filenames(cdn.get_depot_key(manifest.app_id, manifest.depot_id))
                    except Exception as exp:
                        LOG.error("Failed to decrypt manifest: %s" % str(exp))
                        continue
                manifests.append(manifest)

        LOG.debug("Got manifests: %r", manifests)

        yield s, cdn, manifests

        # clean and exit
        cdn.save_cache()
        s.disconnect()

def cmd_depot_info(args):
    try:
        with init_clients(args) as (s, cdn, manifests):
            for i, manifest in enumerate(manifests, 1):
                print("-"*40)
                print("App ID:", manifest.app_id)
                print("Depot ID:", manifest.metadata.depot_id)
                print("Depot Name:", manifest.name if manifest.name else 'Unnamed Depot')
                print("Manifest GID:", manifest.metadata.gid_manifest)
                print("Created On:", fmt_datetime(manifest.metadata.creation_time))
                print("Size:", fmt_size(manifest.metadata.cb_disk_original))
                print("Compressed Size:", fmt_size(manifest.metadata.cb_disk_compressed))
                nchunks = sum((len(file.chunks) for file in manifest.payload.mappings))
                unique_chunks = manifest.metadata.unique_chunks
                print("Unique/Total chunks:", unique_chunks, "/", nchunks, "({:.2f}%)".format(((1-(unique_chunks / nchunks))*100) if nchunks else 0))
                print("Encrypted Filenames:", repr(manifest.metadata.filenames_encrypted))
                print("Number of Files:", len(manifest.payload.mappings))

                if cdn:
                    depot_info = cdn.app_depots.get(manifest.app_id, {}).get(str(manifest.metadata.depot_id))

                    if depot_info:
                        print("Config:", depot_info.get('config', '{}'))
                        if 'dlcappid' in depot_info:
                            print("DLC AppID:", depot_info['dlcappid'])

                        print("Open branches:", ', '.join(depot_info.get('manifests', {}).keys()))
                        print("Protected branches:", ', '.join(depot_info.get('encryptedmanifests', {}).keys()))

    except SteamError as exp:
        LOG.error(str(exp))
        return 1  # error

def cmd_depot_list(args):
    try:
        with init_clients(args) as (s, cdn, manifests):
            for manifest in manifests:
                if manifest.filenames_encrypted:
                    LOG.error("Manifest filenames are encrypted")
                    continue

                for mapping in manifest.payload.mappings:
                    # ignore symlinks and directorys
                    if mapping.linktarget or mapping.flags & EDepotFileFlag.Directory:
                        continue

                    filepath = mapping.filename.rstrip('\x00')

                    # filepath filtering
                    if args.name and not fnmatch(filepath, args.name):
                        continue
                    if args.regex and not re_search(args.regex, filepath):
                        continue

                    # output
                    if args.long:
                        print("{} - size:{:,d} sha:{}".format(
                                filepath,
                                mapping.size,
                                mapping.sha_content.hex(),
                                ))
                    else:
                        print(filepath)
    except SteamError as exp:
        LOG.error(str(exp))
        return 1  # error

def cmd_depot_download(args):
    pbar = fake_tqdm()
    pbar2 = fake_tqdm()

    try:
        with init_clients(args) as (s, cdn, manifests):
            # calculate total size
            if not args.no_progress or args.name or args.regex:
                total_files = 0
                total_size = 0

                for manifest in manifests:
                    for depotfile in manifest:
                        if not depotfile.is_file:
                            continue
                        if args.name and not fnmatch(depotfile.filename, args.name):
                            continue
                        if args.regex and not re_search(args.regex, depotfile.filename):
                            continue

                        total_files += 1
                        total_size += depotfile.size
            else:
                total_files = sum(map(lambda x: len(x), manifests))
                total_size = sum(map(lambda x: x.size_original, manifests))

            # enable progress bar
            if not args.no_progress and sys.stderr.isatty():
                pbar = tqdm(desc='Downloaded', mininterval=0.5, maxinterval=1, total=total_size, unit=' B', unit_scale=True)
                pbar2 = tqdm(desc='Files     ', mininterval=0.5, maxinterval=1, total=total_files, position=1, unit=' file', unit_scale=False)
                gevent.spawn(pbar.gevent_refresh_loop)
                gevent.spawn(pbar2.gevent_refresh_loop)

            # download files
            tasks = GPool(4)

            for manifest in manifests:
                LOG.info("Processing (%s) '%s' ..." % (manifest.gid, manifest.name))

                for depotfile in manifest:
                    if not depotfile.is_file:
                        continue

                    # filepath filtering
                    if args.name and not fnmatch(depotfile.filename, args.name):
                        continue
                    if args.regex and not re_search(args.regex, depotfile.filename):
                        continue

                    tasks.spawn(depotfile.download_to, args.output,
                                no_make_dirs=args.no_directories,
                                pbar=pbar)

                    pbar2.update(1)

            # wait on all downloads to finish
            tasks.join()
            gevent.sleep(0.5)
    except KeyboardInterrupt:
        pbar.close()
        LOG.info("Download canceled")
        return 1  # error
    except SteamError as exp:
        pbar.close()
        pbar.write(str(exp))
        return 1  # error
    else:
        pbar.close()
        if not args.no_progress:
            pbar2.close()
            pbar2.write('\n')
        LOG.info('Download complete')
