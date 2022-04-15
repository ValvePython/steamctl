
from time import time
from steamctl.utils.storage import SqliteDict, UserCacheFile
from steamctl.utils.web import make_requests_session
from steam import webapi

webapi._make_requests_session = make_requests_session

def get_app_names():
    papps = SqliteDict(UserCacheFile("app_names.sqlite3"))

    try:
        last = int(papps[-7])  # use a key that will never be used
    except KeyError:
        last = 0

    if last < time():
        resp = webapi.get('ISteamApps', 'GetAppList', version=2)
        apps = resp.get('applist', {}).get('apps', [])

        if not apps and len(papps) == 0:
            raise RuntimeError("Failed to fetch apps")

        for app in apps:
            papps[int(app['appid'])] = app['name']

        papps[-7] = str(int(time()) + 86400)
        papps.commit()

    return papps

