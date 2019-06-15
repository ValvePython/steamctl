
import requests
from steam import __version__ as steam_ver
from steamctl import  __version__


def make_requests_session():
    """
    :returns: requests session
    :rtype: :class:`requests.Session`
    """
    session = requests.Session()

    version = __import__('steam').__version__
    ua = "python-steamctl/{} python-steam/{} {}".format(
		__version__,
		steam_ver,
                session.headers['User-Agent'],
		)
    session.headers['User-Agent'] = ua

    return session
