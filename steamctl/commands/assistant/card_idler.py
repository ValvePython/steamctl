import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

import os
import re
import sys
import math
import random
import logging
from io import open
from itertools import count
from contextlib import contextmanager
from collections import namedtuple
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session
from steam.client import EMsg, EResult
from bs4 import BeautifulSoup

import steam.client.builtins.web
steam.client.builtins.web.make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

class IdleClient(CachingSteamClient):
    _LOG = logging.getLogger("IdleClient")

    def __init__(self, *args, **kwargs):
        CachingSteamClient.__init__(self, *args, **kwargs)

        self.wakeup = gevent.event.Event()
        self.newcards = gevent.event.Event()

        self.on(self.EVENT_DISCONNECTED, self.__handle_disconnected)
        self.on(self.EVENT_RECONNECT, self.__handle_reconnect)
        self.on(EMsg.ClientItemAnnouncements, self.__handle_item_notification)

    def connect(self, *args, **kwargs):
        self.wakeup.clear()
        return CachingSteamClient.connect(self, *args, **kwargs)

    def __handle_disconnected(self):
        self._LOG.info("Disconnected from Steam")
        self.wakeup.set()

    def __handle_reconnect(self, delay):
        if delay:
            self._LOG.info("Attemping reconnect in %s second(s)..", delay)

    def __handle_item_notification(self, msg):
        if msg.body.count_new_items == 100:
            self._LOG.info("Notification: over %s new items", msg.body.count_new_items)
        else:
            self._LOG.info("Notification: %s new item(s)", msg.body.count_new_items)
        self.newcards.set()
        self.wakeup.set()

@contextmanager
def init_client(args):
    s = IdleClient()
    s.login_from_args(args)
    yield s
    s.disconnect()


Game = namedtuple('Game', 'appid name cards_left playtime')

def get_remaining_cards(s):
    # introduced delay in case account takes longer to login
    if not s.licenses:
        s.wait_event(EMsg.ClientLicenseList, raises=False, timeout=5)

    web = s.get_web_session()

    if not web:
        LOG.error("Failed to get web session")
        return


    games = []
    n_pages = 1

    for n in count(1):
        LOG.debug("Loading badge page %s", n)
        resp = web.get('https://steamcommunity.com/profiles/{}/badges?sort=p&p={}'.format(
                            s.steam_id.as_64,
                            n,
                           ))

        if resp.status_code != 200:
            LOG.error("Error fetching badges: HTTP %s", resp.status_code)
            return

        page = BeautifulSoup(resp.content, 'html.parser')

        if n_pages == 1:
            elms = page.select('.profile_paging')

            if elms:
                m = re.search('of (\S+) badges', elms[0].get_text(strip=True))
                if m:
                    n_badges = int(re.sub('[^0-9]', '', m.group(1)))
                    n_pages = math.ceil(n_badges / 150)

        for badge in page.select('div.badge_row'):
            status = badge.select('.progress_info_bold')

            if not status:
                continue

            m = re.match('(\d+) card drops?', status[0].get_text(strip=True))

            if not m:
                continue

            cards_left = int(m.group(1))
            name = badge.select('.badge_title')[0].get_text('\x00', True).split('\x00', 1)[0]
            appid = int(re.search('gamecards/(\d+)/', badge.select('[href*=gamecards]')[0].get('href')).group(1))
            playtime = float((badge.select('.badge_title_stats_playtime')[0].get_text(strip=True) or '0').split(' ', 1)[0])

            games.append(Game(appid, name, cards_left, playtime))

        if n == n_pages:
            break

    return games

def cmd_assistant_idle_cards(args):
    with init_client(args) as s:
        while True:
            # ensure we are connected and logged in
            if not s.connected:
                s.reconnect()
                continue

            if not s.logged_on:
                if not s.relogin_available:
                    return 1 # error

                result = s.relogin()

                if result != EResult.OK:
                    LOG.warning("Login failed: %s", repr(EResult(result)))

                continue

            # check badges for cards
            LOG.info("Checking for games with cards left..")
            games = get_remaining_cards(s)

            if not games:
                LOG.info("No games with card left were found. Checking again in 10 mins...")
                s.wakeup.wait(timeout=600)
                continue

            n_games = len(games)
            n_cards = sum(map(lambda game: game.cards_left, games))

            LOG.info("%s card(s) left across %s game(s)", n_cards, n_games)

            # pick games to idle
            if len(games) > 32:
                random.shuffle(games)

            # only 32 can be idled at a single time
            games = games[:32]
            LOG.info("Playing: %s", ', '.join(sorted(map(lambda game: game.name, games))))

            # play games
            games_to_play = list(map(lambda game: game.appid, games))
            s.newcards.clear()

            # rapid fire playing
            for _ in range(6):
                s.wakeup.clear()
                s.games_played(games_to_play)
                s.wakeup.wait(timeout=10)
                s.games_played([])
                s.sleep(1)

                if s.newcards.is_set():
                    break

            if s.newcards.is_set():
                continue

            # accumulate play time
            s.wakeup.clear()
            s.games_played(games_to_play)
            s.wakeup.wait(timeout=600)
            s.games_played([])
            s.sleep(1)











