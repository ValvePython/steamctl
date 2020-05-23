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

class DEWEY(CachingSteamClient):
    _LOG = logging.getLogger("DEWEY")

@contextmanager
def init_client(args):
    s = DEWEY()
    s.login_from_args(args)
    yield s
    s.disconnect()


def cmd_assistant_sc2020(args):
    with init_client(args) as s:
        web = s.get_web_session()

        if not web:
            print("Failed getting a web session")
            return 1 # error

        resp = web.get('https://store.steampowered.com/springcleaning')

        if resp.status_code != 200:
            LOG.error("Error checking tasks: HTTP %s", resp.status_code)
            return

        page = BeautifulSoup(resp.content, 'html.parser')

        progress = page.select('.badge_progress_meter')

        if progress and "You've completed" in progress[0].get('data-tooltip-text'):
            print("You've already completed the Spring Cleaning 2020 badge!")
            return

        apps_to_play = []

        for floor in page.select('.task_dialog_row'):
            for game in floor.select('[href^=steam]'):
                apps_to_play.append(int(game.get('href').split('/')[-1]))
                break

        if not apps_to_play:
            print("No games found. Spring Cleaning 2020 sale is over?")
            return 1 # error

        s.games_played(apps_to_play)
        s.sleep(1)

        print("All tasks done. Enjoy")
