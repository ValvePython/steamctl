import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

from gevent.pool import Pool as GPool

import os
import sys
import logging
from io import open
from steam import webapi
from steam.exceptions import SteamError
from steam.enums import EResult
from steamctl.utils.storage import ensure_dir, sanitizerelpath
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_size
from steamctl.utils.tqdm import tqdm, fake_tqdm
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

_LOG = logging.getLogger(__name__)

def cmd_workshop_download(args):
    apikey = args.apikey or get_webapi_key()

    if not apikey:
        _LOG.error("No WebAPI key set. See: steamctl webapi -h")
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
        _LOG.error("Query failed: %s", str(exp))
        if getattr(exp, 'response', None):
            _LOG.error("Response body: %s", exp.response.text)
        return 1  # error

    if pubfile['result'] != EResult.OK:
        _LOG.error("Error accessing %s: %r", pubfile['publishedfileid'], EResult(pubfile['result']))
        return 1  # error

    print("Workshop item: (%s) %s" % (pubfile['publishedfileid'], pubfile['title'].strip()))
    print("App: (%s) %s" % (pubfile['consumer_appid'], pubfile['app_name']))

    if pubfile.get('file_url'):
        return download_via_url(args, pubfile)
    elif pubfile.get('hcontent_file'):
        return download_via_steampipe(args, pubfile)
    else:
        _LOG.error("This workshop file is not downloable")
        return 1


def download_via_url(args, pubfile):
    sess = make_requests_session()
    fstream = sess.get(pubfile['file_url'], stream=True)
    total_size = int(pubfile['file_size'])

    relpath = sanitizerelpath(pubfile['filename'])

    if args.no_directories:
        relpath = os.path.basename(relpath)

    relpath = os.path.join(args.output, relpath)

    filepath = os.path.abspath(relpath)
    ensure_dir(filepath)

    with open(filepath, 'wb') as fp:
        if not args.no_progress and sys.stderr.isatty():
            pbar = tqdm(total=total_size, unit='B', unit_scale=True)
            gevent.spawn(pbar.gevent_refresh_loop)
        else:
            pbar = fake_tqdm()

        pbar.write('Downloading to {} ({})'.format(
            relpath,
            fmt_size(total_size),
            ))

        for chunk in iter(lambda: fstream.raw.read(1024**2), b''):
            fp.write(chunk)
            pbar.update(len(chunk))

        pbar.close()

def download_via_steampipe(args, pubfile):
    from steamctl.clients import CachingSteamClient

    s = CachingSteamClient()
    if args.cell_id is not None:
        s.cell_id = args.cell_id
    cdn = s.get_cdnclient()


    key = pubfile['consumer_appid'], pubfile['consumer_appid'], pubfile['hcontent_file']

    # only login if we dont have depot decryption key
    if int(pubfile['consumer_appid']) not in cdn.depot_keys:
        result = s.login_from_args(args)

        if result == EResult.OK:
            print("Login to Steam successful")
        else:
            print("Failed to login: %r" % result)
            return 1  # error

    try:
        manifest = cdn.get_manifest(*key)
    except SteamError as exp:
        if exp.eresult == EResult.AccessDenied:
            print("This account doesn't have access to the app depot")
        else:
            print(str(exp))
        return 1  # error
    else:
        manifest.name = pubfile['title']

    _LOG.debug("Got manifest: %r", manifest)
    print("File manifest acquired")

    if not args.no_progress and sys.stderr.isatty():
        pbar = tqdm(total=manifest.size_original, unit='B', unit_scale=True)
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

    print("Download complete.")
