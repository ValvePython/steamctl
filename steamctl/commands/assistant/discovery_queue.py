import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_select()
gevent.monkey.patch_ssl()

import logging
from gevent.pool import Pool
from contextlib import contextmanager
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session
from steam.client import EMsg, EResult

import steam.client.builtins.web
steam.client.builtins.web.make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)


class SteamClient(CachingSteamClient):
    _LOG = logging.getLogger("SteamClient")

    def __init__(self, *args, **kwargs):
        CachingSteamClient.__init__(self, *args, **kwargs)

        self.on(self.EVENT_DISCONNECTED, self.__handle_disconnected)
        self.on(self.EVENT_RECONNECT, self.__handle_reconnect)
        self.on(EMsg.ClientItemAnnouncements, self.__handle_item_notification)

    def connect(self, *args, **kwargs):
        self._LOG.info("Connecting to Steam...")
        return CachingSteamClient.connect(self, *args, **kwargs)

    def __handle_disconnected(self):
        self._LOG.info("Disconnected from Steam")

    def __handle_reconnect(self, delay):
        if delay:
            self._LOG.info("Attemping reconnect in %s second(s)..", delay)

    def __handle_item_notification(self, msg):
        if msg.body.count_new_items == 100:
            self._LOG.info("Notification: over %s new items", msg.body.count_new_items)
        else:
            self._LOG.info("Notification: %s new item(s)", msg.body.count_new_items)

@contextmanager
def init_client(args):
    s = SteamClient()
    s.login_from_args(args)
    yield s
    s.disconnect()

def cmd_assistant_discovery_queue(args):
    with init_client(args) as s:
        web = s.get_web_session()

        if not web:
            LOG.error("Failed to get web session")
            return 1  # error

        sessionid = web.cookies.get('sessionid', domain='store.steampowered.com')

        LOG.info("Generating new discovery queue...")

        try:
            data = web.post('https://store.steampowered.com/explore/generatenewdiscoveryqueue', {'sessionid': sessionid, 'queuetype': 0}).json()
        except Exception as exp:
            LOG.debug("Exception: %s", str(exp))
            data = None

        if not isinstance(data, dict) or not data.get('queue', None):
            LOG.error("Invalid/empty discovery response")
            return 1  # error

        def explore_app(appid):
            for delay in (1,3,5,8,14):
                resp = web.post('https://store.steampowered.com/app/10', {'appid_to_clear_from_queue': appid, 'sessionid': sessionid})

                if resp.status_code == 200:
                    return True

                LOG.warning('Failed to explore app %s, retrying in %s second(s)', appid, delay)
                s.sleep(delay)

            return False

        pool = Pool(6)

        result = pool.imap(explore_app, data['queue'])

        if all(result):
            LOG.info("Discovery queue explored successfully")
        else:
            LOG.error("Failed to explore some apps, try again")
            return 1  #error

