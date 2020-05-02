import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

from gevent.pool import Pool as GPool

import re
import os
import sys
import logging
from io import open
from contextlib import contextmanager
from re import search as re_search
from fnmatch import fnmatch
import vpk
from steam import webapi
from steam.exceptions import SteamError
from steam.enums import EResult, EDepotFileFlag
from steamctl.clients import CachingSteamClient, CTLDepotManifest, CTLDepotFile
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_size, fmt_datetime
from steamctl.utils.tqdm import tqdm, fake_tqdm
from steamctl.commands.webapi import get_webapi_key

from steamctl.utils.storage import ensure_dir, sanitizerelpath

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

# overload VPK with a missing method
class c_VPK(vpk.VPK):
    def c_iter_index(self):
        if self.tree:
            index = self.tree.items()
        else:
            index = self.read_index_iter()

        for path, metadata in index:
            yield path, metadata

# find and cache paths to vpk depot files, and set them up to be read directly from CDN
class ManifestFileIndex(object):
    def __init__(self, manifests):
        self.manifests = manifests
        self._path_cache = {}

    def _locate_file_mapping(self, path):
        ref = self._path_cache.get(path, None)

        if ref:
            return ref
        else:
            self._path_cache[path] = None

            for manifest in self.manifests:
                try:
                    foundfile = next(manifest.iter_files(path))
                except StopIteration:
                    continue
                else:
                    self._path_cache[path] = ref = (manifest, foundfile.file_mapping)
        return ref

    def index(self, pattern):
        for manifest in self.manifests:
            for filematch in manifest.iter_files(pattern):
                self._path_cache[filematch.filename_raw] = (manifest, filematch.file_mapping)

    def file_exists(self, path):
        return self._locate_file_mapping(path) != None

    def get_file(self, path, *args, **kwargs):
        ref = self._locate_file_mapping(path)
        if ref:
            return CTLDepotFile(*ref)
        raise SteamError("File not found: {}".format(path))

    def get_vpk(self, path):
        return c_VPK(path, fopen=self.get_file)


# vpkfile download task
def vpkfile_download_to(vpk_path, vpkfile, target, no_make_dirs, pbar):
    relpath = sanitizerelpath(vpkfile.filepath)

    if no_make_dirs:
        relpath = os.path.basename(relpath)

    relpath = os.path.join(target,         # output directory
                           vpk_path[:-4],  # vpk path with extention (e.g. pak01_dir)
                           relpath)        # vpk relative path

    filepath = os.path.abspath(relpath)
    ensure_dir(filepath)

    LOG.info("Downloading VPK file to {} ({}, crc32:{})".format(relpath,
                                                                fmt_size(vpkfile.file_length),
                                                                vpkfile.crc32,
                                                                ))

    with open(filepath, 'wb') as fp:
        for chunk in iter(lambda: vpkfile.read(16384), b''):
            fp.write(chunk)

            if pbar:
                pbar.update(len(chunk))

@contextmanager
def init_clients(args):
    s = CachingSteamClient()

    if args.cell_id is not None:
        s.cell_id = args.cell_id

    cdn = s.get_cdnclient()

    if getattr(args, 'file', None):
        manifest = CTLDepotManifest(cdn, args.app or -1, args.file.read())
        yield s, cdn, [manifest]
    else:
        if not args.app:
            raise SteamError("No app id specified")

        # only login if we dont have depot decryption key
        if (not args.app or not args.depot or not args.manifest or
            args.depot not in cdn.depot_keys):
            result = s.login_from_args(args)

            if result == EResult.OK:
                LOG.info("Login to Steam successful")
            else:
                raise SteamError("Failed to login: %r" % result)

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

            def depot_filter(depot_id, info):
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

            branch = args.branch
            password = args.password

            LOG.info("Getting manifests for %s branch", repr(branch))

            manifests = []
            for manifest in cdn.get_manifests(args.app, branch=branch, password=password, filter_func=depot_filter, decrypt=False):
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
    def print_file_info(filepath, info=None):
        # filepath filtering
        if args.name and not fnmatch(filepath, args.name):
            return
        if args.regex and not re_search(args.regex, filepath):
            return

        # output
        if info:
            print("{} - {}".format(filepath, info))
        else:
            print(filepath)

    try:
        with init_clients(args) as (s, cdn, manifests):
            fileindex = ManifestFileIndex(manifests)

            # pre-index vpk file to speed up lookups
            if args.vpk:
                fileindex.index('*.vpk')

            for manifest in manifests:
                if manifest.filenames_encrypted:
                    LOG.error("Manifest filenames are encrypted")
                    continue

                for mapping in manifest.payload.mappings:
                    # ignore symlinks and directorys
                    if mapping.linktarget or mapping.flags & EDepotFileFlag.Directory:
                        continue

                    filepath = mapping.filename.rstrip('\x00 \n\t')

                    # filepath filtering
                    if (   (not args.name and not args.regex)
                        or (args.name  and fnmatch(filepath, args.name))
                        or (args.regex and re_search(args.regex, filepath))
                        ):

                        # print out for manifest file
                        if not args.long:
                            print(filepath)
                        else:
                            print("{} - size:{:,d} sha1:{}".format(
                                    filepath,
                                    mapping.size,
                                    mapping.sha_content.hex(),
                                    )
                                  )

                    # list files inside vpk
                    if args.vpk and filepath.endswith('.vpk'):
                        # fast skip VPKs that can't possibly match
                        if args.name and ':' in args.name:
                            pre = args.name.split(':', 1)[0]
                            if not fnmatch(filepath, pre):
                                continue
                        if args.regex and ':' in args.regex:
                            pre = args.regex.split(':', 1)[0]
                            if not re_search(pre + '$', filepath):
                                continue

                        # scan VPKs, but skip data only ones
                        if filepath.endswith('_dir.vpk') or not re.search("_\d+\.vpk$", filepath):
                            LOG.debug("Scanning VPK file: %s", filepath)

                            try:
                                fvpk = fileindex.get_vpk(filepath)
                            except ValueError as exp:
                                LOG.error("VPK read error: %s", str(exp))
                            else:
                                for vpkfile_path, (_, crc32, _, _, _, size) in fvpk.c_iter_index():
                                    complete_path = "{}:{}".format(filepath, vpkfile_path)

                                    if (   (not args.name and not args.regex)
                                        or (args.name  and fnmatch(complete_path, args.name))
                                        or (args.regex and re_search(args.regex, complete_path))
                                        ):

                                        if args.long:
                                            print("{} - size:{:,d} crc32:{}".format(
                                                    complete_path,
                                                    size,
                                                    crc32,
                                                    )
                                                  )
                                        else:
                                            print(complete_path)


    except SteamError as exp:
        LOG.error(str(exp))
        return 1  # error

def cmd_depot_download(args):
    pbar = fake_tqdm()
    pbar2 = fake_tqdm()

    try:
        with init_clients(args) as (s, cdn, manifests):
            fileindex = ManifestFileIndex(manifests)

            # pre-index vpk file to speed up lookups
            if args.vpk:
                fileindex.index('*.vpk')

            # calculate total size
            total_files = 0
            total_size = 0

            LOG.info("Locating and counting files...")

            for manifest in manifests:
                for depotfile in manifest:
                    if not depotfile.is_file:
                        continue

                    filepath = depotfile.filename_raw

                    # list files inside vpk
                    if args.vpk and filepath.endswith('.vpk'):
                        # fast skip VPKs that can't possibly match
                        if args.name and ':' in args.name:
                            pre = args.name.split(':', 1)[0]
                            if not fnmatch(filepath, pre):
                                continue
                        if args.regex and ':' in args.regex:
                            pre = args.regex.split(':', 1)[0]
                            if not re_search(pre + '$', filepath):
                                continue

                        # scan VPKs, but skip data only ones
                        if filepath.endswith('_dir.vpk') or not re.search("_\d+\.vpk$", filepath):
                            LOG.debug("Scanning VPK file: %s", filepath)

                            try:
                                fvpk = fileindex.get_vpk(filepath)
                            except ValueError as exp:
                                LOG.error("VPK read error: %s", str(exp))
                            else:
                                for vpkfile_path, (_, _, _, _, _, size) in fvpk.c_iter_index():
                                    complete_path = "{}:{}".format(filepath, vpkfile_path)

                                    if args.name and not fnmatch(complete_path, args.name):
                                        continue
                                    if args.regex and not re_search(args.regex, complete_path):
                                        continue

                                    total_files += 1
                                    total_size += size

                    # account for depot files
                    if args.name and not fnmatch(filepath, args.name):
                        continue
                    if args.regex and not re_search(args.regex, filepath):
                        continue

                    total_files += 1
                    total_size += depotfile.size

            if not total_files:
                raise SteamError("No files found to download")

            # enable progress bar
            if not args.no_progress and sys.stderr.isatty():
                pbar = tqdm(desc='Downloaded', mininterval=0.5, maxinterval=1, total=total_size, unit=' B', unit_scale=True)
                pbar2 = tqdm(desc='Files     ', mininterval=0.5, maxinterval=1, total=total_files, position=1, unit=' file', unit_scale=False)
                gevent.spawn(pbar.gevent_refresh_loop)
                gevent.spawn(pbar2.gevent_refresh_loop)

            # download files
            tasks = GPool(6)

            for manifest in manifests:
                if pbar2.n == total_files:
                    break

                LOG.info("Processing manifest (%s) '%s' ..." % (manifest.gid, manifest.name or "<Unknown>"))

                for depotfile in manifest:
                    if pbar2.n == total_files:
                        break

                    if not depotfile.is_file:
                        continue

                    filepath = depotfile.filename_raw

                    if args.vpk and filepath.endswith('.vpk'):
                        # fast skip VPKs that can't possibly match
                        if args.name and ':' in args.name:
                            pre = args.name.split(':', 1)[0]
                            if not fnmatch(filepath, pre):
                                continue
                        if args.regex and ':' in args.regex:
                            pre = args.regex.split(':', 1)[0]
                            if not re_search(pre + '$', filepath):
                                continue

                        # scan VPKs, but skip data only ones
                        if filepath.endswith('_dir.vpk') or not re.search("_\d+\.vpk$", filepath):
                            LOG.debug("Scanning VPK file: %s", filepath)

                            try:
                                fvpk = fileindex.get_vpk(filepath)
                            except ValueError as exp:
                                LOG.error("VPK read error: %s", str(exp))
                            else:
                                for vpkfile_path, metadata in fvpk.c_iter_index():
                                    complete_path = "{}:{}".format(filepath, vpkfile_path)

                                    if args.name and not fnmatch(complete_path, args.name):
                                        continue
                                    if args.regex and not re_search(args.regex, complete_path):
                                        continue

                                    tasks.spawn(vpkfile_download_to,
                                                depotfile.filename,
                                                fvpk.get_vpkfile_instance(vpkfile_path,
                                                                          fvpk._make_meta_dict(metadata)),
                                                args.output,
                                                no_make_dirs=args.no_directories,
                                                pbar=pbar)

                                    pbar2.update(1)

                                    # break out of vpk file loop
                                    if pbar2.n == total_files:
                                        break

                    # break out of depotfile loop
                    if pbar2.n == total_files:
                        break

                    # filepath filtering
                    if args.name and not fnmatch(filepath, args.name):
                        continue
                    if args.regex and not re_search(args.regex, filepath):
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
