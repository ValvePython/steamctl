
import logging
import sys
import json
from steam import webapi
from steamctl.utils.storage import UserDataFile, UserCacheFile
from steamctl.utils.web import make_requests_session
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

def cmd_apps_list_names(args):
    resp = webapi.get('ISteamApps', 'GetAppList', version=2)

    apps = resp.get('applist', {}).get('apps', [])

    if not apps:
        LOG.error("Failed to get app list")
        return 1  # error

    width = len(str(max(map(lambda app: app['appid'], apps))))

    for app in sorted(apps, key=lambda app: app['appid']):
        print(str(app['appid']).ljust(width), app['name'])
