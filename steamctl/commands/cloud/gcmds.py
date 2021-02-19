import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

import os
import sys
import logging
from contextlib import contextmanager
from steam import webapi
from steam.exceptions import SteamError
from steam.client import EResult, EMsg, MsgProto, SteamID
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import fmt_size

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)


@contextmanager
def init_client(args):
    s = CachingSteamClient()
    s.login_from_args(args)
    yield s
    s.disconnect()


def _get_cloud_files(s, app_id):
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
        files, n_files, total_size = _get_cloud_files(s, args.app_id)

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
