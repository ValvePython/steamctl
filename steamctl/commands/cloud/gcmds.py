import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

from gevent.pool import Pool as GPool

import re
import os
import sys
import logging
from contextlib import contextmanager
from steam.exceptions import SteamError
from steam.client import EResult, EMsg, MsgProto, SteamID
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session
from steamctl.utils.tqdm import tqdm, fake_tqdm
from steamctl.utils.format import fmt_size
from steamctl.utils.storage import ensure_dir, sanitizerelpath
from steamctl.utils.apps import get_app_names

LOG = logging.getLogger(__name__)


@contextmanager
def init_client(args):
    s = CachingSteamClient()
    s.login_from_args(args)
    yield s
    s.disconnect()


def get_cloud_files(s, app_id):
    job_id = s.send_um('Cloud.EnumerateUserFiles#1',
                       {'appid': app_id,
                        'extended_details': True,
                        })

    files = []
    total_files, n_files, total_size = None, 0, 0

    while total_files != n_files:
        msg = s.wait_msg(job_id, timeout=10)

        if not msg:
            raise SteamError("Failed listing UFS files", EResult.Timeout)
        if msg.header.eresult != EResult.OK:
            raise SteamError("Failed listing UFS files", EResult(msg.header.eresult))

        total_files = msg.body.total_files
        n_files += len(msg.body.files)

        for entry in msg.body.files:
            files.append(entry)
            total_size += entry.file_size

    return files, total_files, total_size

def cmd_cloud_list(args):
    with init_client(args) as s:
        files, n_files, total_size = get_cloud_files(s, args.app_id)

        for entry in files:
            if not args.long:
                print(entry.filename)
            else:
                print("{} - size:{:,d} sha1:{}".format(
                        entry.filename,
                        entry.file_size,
                        entry.file_sha,
                        )
                      )

def cmd_cloud_list_apps(args):
    with init_client(args) as s:
        msg = s.send_um_and_wait('Cloud.EnumerateUserApps#1', timeout=10)

        if msg is None or  msg.body is None:
            return 1 # error

        app_names = get_app_names()

        for app in msg.body.apps:
            print("{} - {} - Files: {} Size: {}".format(
                    app.appid,
                    app_names.get(app.appid, f'Unknown App {app.appid}'),
                    app.totalcount,
                    fmt_size(app.totalsize),
                    )
                 )

def download_file(args, sess, file, pbar_size, pbar_files):
    fstream = sess.get(file.url, stream=True)
    filename = file.filename

    if fstream.status_code != 200:
        LOG.error("Failed to download: {}".format(filename))
        return 1 # error

    relpath = sanitizerelpath(filename)
    # ensure there is a / after %vars%, and replace % with _
    relpath = re.sub(r'^%([A-Za-z0-9]+)%', r'_\1_/', relpath)

    relpath = os.path.join(args.output, relpath)

    filepath = os.path.abspath(relpath)
    ensure_dir(filepath)

    with open(filepath, 'wb') as fp:
        for chunk in iter(lambda: fstream.raw.read(8388608), b''):
            fp.write(chunk)
            pbar_size.update(len(chunk))

    pbar_files.update(1)

def cmd_cloud_download(args):
    with init_client(args) as s:
        files, total_files, total_size = get_cloud_files(s, args.app_id)

        if not args.no_progress and sys.stderr.isatty():
            pbar = tqdm(desc='Data ', mininterval=0.5, maxinterval=1, miniters=1024**3*10, total=total_size, unit='B', unit_scale=True)
            pbar2 = tqdm(desc='Files', mininterval=0.5, maxinterval=1, miniters=10, total=total_files, position=1, unit=' file', unit_scale=False)
            gevent.spawn(pbar.gevent_refresh_loop)
            gevent.spawn(pbar2.gevent_refresh_loop)
        else:
            pbar = fake_tqdm()
            pbar2 = fake_tqdm()

        tasks = GPool(6)
        sess = make_requests_session()

        for entry in files:
            tasks.spawn(download_file, args, sess, entry, pbar, pbar2)

        tasks.join()

        pbar.refresh()
        pbar2.refresh()
        pbar.close()
