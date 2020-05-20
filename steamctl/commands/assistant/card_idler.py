import gevent
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

import os
import re
import sys
import random
import logging
from io import open
from contextlib import contextmanager
from collections import namedtuple
from steamctl.clients import CachingSteamClient
from steamctl.utils.web import make_requests_session
from steam.client import EMsg
from bs4 import BeautifulSoup

import steam.client.builtins.web
steam.client.builtins.web.make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

class IdleClient(CachingSteamClient):
    def __init__(self, *args, **kwargs):
        CachingSteamClient.__init__(self, *args, **kwargs)

        self.wakeup = gevent.event.Event()

        self.on(self.EVENT_DISCONNECTED, self.__handle_disconnected)
        self.on(self.EVENT_RECONNECT, self.__handle_reconnect)
        self.on(EMsg.ClientItemAnnouncements, self.__handle_item_notification)

    def connect(self, *args, **kwargs):
        self.wakeup.clear()
        CachingSteamClient.connect(self, *args, **kwargs)

    def __handle_disconnected(self):
        self._LOG.info("Disconnected from Steam")
        self.wakeup.set()

    def __handle_reconnect(self, delay):
        if delay:
            self._LOG.info("Attemping reconnect in %s second(s)..", delay)

    def __handle_item_notification(self, msg):
        self._LOG.info("Notification: %s new item(s)", msg.body.count_new_items)
        self.wakeup.set()

@contextmanager
def init_client(args):
    s = IdleClient()
    s.login_from_args(args)
    yield s
    s.disconnect()


Game = namedtuple('Game', 'appid name cards_left playtime')

def get_remaining_cards(s):
    resp = s.get_web_session().get('https://steamcommunity.com/my/badges/')

    page = BeautifulSoup(resp.content, 'html.parser')

    games = {}

    for badge in page.select('div.badge_row'):
        status = badge.select('.progress_info_bold')

        if not status:
            continue

        m = re.match('(\d+) card drops', status[0].get_text(strip=True))

        if not m:
            continue

        cards_left = int(m.group(1))
        name = badge.select('.badge_title')[0].get_text('\x00', True).split('\x00', 1)[0]
        appid = int(re.search('gamecards/(\d+)/', badge.select('[href*=gamecards]')[0].get('href')).group(1))
        playtime = float((badge.select('.badge_title_stats_playtime')[0].get_text(strip=True) or '0').split(' ', 1)[0])

        games[appid] = Game(appid, name, cards_left, playtime)

    return games

def cmd_assistant_idle_cards(args):
    with init_client(args) as s:
        LOG.info("Checking for games with cards left..")

        while True:
            # ensure we are connected and logged in
            if not s.connected:
                s.reconnect()

            if not s.logged_on:
                s.relogin()  # TODO: check return for failed pass
                s.sleep(1)

            # check badges for any games with cards left
            games = get_remaining_cards(s)

            if not games:
                LOG.info("No cards left to idle")
                s.wakeup.wait(timeout=900)
                continue

            n_games = len(games)
            n_cards = sum(map(lambda game: game.cards_left, games.values()))

            LOG.info("%s card(s) left across %s game(s)", n_cards, n_games)

            # pick game or games to idle
            low_playtime_games = list(filter(lambda game: game.playtime <= 3, games.values()))

            if low_playtime_games:
                random.shuffle(low_playtime_games)
                games_to_play = low_playtime_games[:32]
                LOG.info("Playing: %s", ', '.join(sorted(map(lambda game: game.name, games_to_play))))
            else:
                games_to_play = sorted(games.values(), key=lambda game: game.cards_left)[:1]
                LOG.info("Playing: %s - %s card(s) left", games_to_play[0].name, games_to_play[0].cards_left)

            # play games
            s.games_played(list(map(lambda game: game.appid, games_to_play)))

            # hold and wait for wakeup, or refresh after interval
            s.wakeup.wait(timeout=600)
            s.wakeup.clear()

            s.games_played([])











