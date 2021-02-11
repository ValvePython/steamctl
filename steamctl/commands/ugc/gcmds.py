import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

import os
import sys
import logging
from io import open
from contextlib import contextmanager
from steam import webapi
from steam.exceptions import SteamError
from steam.client import EResult, EMsg, MsgProto, SteamID
from steamctl.clients import CachingSteamClient
from steamctl.utils.storage import ensure_dir, sanitizerelpath
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_size
from steamctl.utils.tqdm import tqdm, fake_tqdm
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)


class UGCSteamClient(CachingSteamClient):
    def get_ugc_details(self, ugc_id):
        if 0 > ugc_id > 2**64:
            raise SteamError("Invalid UGC ID")

        result = self.send_job_and_wait(MsgProto(EMsg.ClientUFSGetUGCDetails), {'hcontent': ugc_id}, timeout=5)

        if not result or result.eresult != EResult.OK:
            raise SteamError("Failed getting UGC details", EResult(result.eresult) if result else EResult.Timeout)

        return result

@contextmanager
def init_client(args):
    s = UGCSteamClient()
    s.login_from_args(args)
    yield s
    s.disconnect()

def cmd_ugc_info(args):
    with init_client(args) as s:
        ugcdetails = s.get_ugc_details(args.ugc)
        user = s.get_user(ugcdetails.steamid_creator)

        print("File URL:", ugcdetails.url)
        print("Filename:", ugcdetails.filename)
        print("File size:", fmt_size(ugcdetails.file_size))
        print("SHA1:", ugcdetails.file_encoded_sha1)
        print("App ID:", ugcdetails.app_id)
        print("Creator:", user.name)
        print("Creator Profile:", SteamID(ugcdetails.steamid_creator).community_url)


def cmd_ugc_download(args):
    with init_client(args) as s:
        ugcdetails = s.get_ugc_details(args.ugc)

    return download_via_url(args, ugcdetails.url, ugcdetails.filename)


def download_via_url(args, url, filename):
    sess = make_requests_session()
    fstream = sess.get(url, stream=True)
    total_size = int(fstream.headers.get('Content-Length', 0))

    relpath = sanitizerelpath(filename)

    if args.no_directories:
        relpath = os.path.basename(relpath)

    relpath = os.path.join(args.output, relpath)

    filepath = os.path.abspath(relpath)
    ensure_dir(filepath)

    with open(filepath, 'wb') as fp:
        if not args.no_progress and sys.stderr.isatty():
            pbar = tqdm(total=total_size, mininterval=0.5, maxinterval=1, miniters=1024**3*10, unit='B', unit_scale=True)
            gevent.spawn(pbar.gevent_refresh_loop)
        else:
            pbar = fake_tqdm()

#       LOG.info('Downloading to {} ({})'.format(
#                   relpath,
#                   fmt_size(total_size) if total_size else 'Unknown size',
#                   ))

        for chunk in iter(lambda: fstream.raw.read(8388608), b''):
            fp.write(chunk)
            pbar.update(len(chunk))

        pbar.close()

