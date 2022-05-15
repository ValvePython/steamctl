import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

from gevent.pool import Pool as GPool

import os
import sys
import logging
from io import open
from steam import webapi
from steam.exceptions import SteamError, ManifestError
from steam.enums import EResult
from steamctl.utils.storage import ensure_dir, sanitizerelpath
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_size
from steamctl.utils.tqdm import tqdm, fake_tqdm
from steamctl.commands.webapi import get_webapi_key
from steamctl.commands.ugc.gcmds import download_via_url

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

def cmd_workshop_download(args):
    apikey = args.apikey or get_webapi_key()

    if not apikey:
        LOG.error("No WebAPI key set. See: steamctl webapi -h")
        return 1  #error

    params = {
        'key': apikey,
        'publishedfileids': [args.id],
        }


    try:
        pubfile = webapi.get('IPublishedFileService', 'GetDetails',
                             params=params,
                             )['response']['publishedfiledetails'][0]
    except Exception as exp:
        LOG.error("Query failed: %s", str(exp))
        if getattr(exp, 'response', None):
            LOG.error("Response body: %s", exp.response.text)
        return 1  # error

    if pubfile['result'] != EResult.OK:
        LOG.error("Error accessing %s: %r", pubfile['publishedfileid'], EResult(pubfile['result']))
        return 1  # error

    LOG.info("Workshop item: (%s) %s" % (pubfile['publishedfileid'], pubfile['title'].strip()))
    LOG.info("App: (%s) %s" % (pubfile['consumer_appid'], pubfile['app_name']))

    if pubfile.get('file_url'):
        # reuse 'ugc download' function
        return download_via_url(args, pubfile['file_url'], pubfile['filename'])
    elif pubfile.get('hcontent_file'):
        return download_via_steampipe(args, pubfile)
    else:
        LOG.error("This workshop file is not downloable")
        return 1


def download_via_steampipe(args, pubfile):
    from steamctl.clients import CachingSteamClient

    s = CachingSteamClient()
    if args.cell_id is not None:
        s.cell_id = args.cell_id
    cdn = s.get_cdnclient()


    key = pubfile['consumer_appid'], pubfile['consumer_appid'], pubfile['hcontent_file']
    manifest = cdn.get_cached_manifest(*key)

    # only login if we dont have depot decryption key
    if (
        not manifest
        or (
            manifest.filenames_encrypted
            and int(pubfile['consumer_appid']) not in cdn.depot_keys
       )
    ):
        result = s.login_from_args(args)

        if result == EResult.OK:
            LOG.info("Login to Steam successful")
        else:
            LOG.error("Failed to login: %r" % result)
            return 1  # error

    if not manifest or manifest.filenames_encrypted:
        try:
            manifest_code = cdn.get_manifest_request_code(*key)
            manifest = cdn.get_manifest(*key, manifest_request_code=manifest_code)
        except ManifestError as exc:
            LOG.error(str(exc))
            return 1  # error

    manifest.name = pubfile['title']

    LOG.debug("Got manifest: %r", manifest)
    LOG.info("File manifest acquired (%s)", pubfile['hcontent_file'])

    if not args.no_progress and sys.stderr.isatty():
        pbar = tqdm(total=manifest.size_original, mininterval=0.5, maxinterval=1, miniters=1024**3*10, unit='B', unit_scale=True)
        gevent.spawn(pbar.gevent_refresh_loop)
    else:
        pbar = fake_tqdm()

    tasks = GPool(4)

    for mfile in manifest:
        if not mfile.is_file:
            continue
        tasks.spawn(mfile.download_to, args.output,
                    no_make_dirs=args.no_directories,
                    pbar=pbar)

    # wait on all downloads to finish
    tasks.join()

    # clean and exit
    pbar.close()
    cdn.save_cache()
    s.disconnect()

    LOG.info("Download complete.")
