
import logging
from steamctl.utils.storage import UserDataDirectory, UserCacheDirectory
from steamctl.utils.format import print_table, fmt_duration


_LOG = logging.getLogger(__name__)

def cmd_clear_cache(args):
    _LOG.debug("Removing all cache files")

    cache_dir = UserCacheDirectory()

    if cache_dir.exists():
        cache_dir.remove()
    else:
        _LOG.debug("Cache dir doesn't exist. Nothing to do")

def cmd_clear_credentials(args):
    _LOG.debug("Removing all stored credentials")

    data_dir = UserDataDirectory('client')

    for entry in data_dir.iter_files('*.key'):
        entry.secure_remove()
    for entry in data_dir.iter_files('*_sentry.bin'):
        entry.secure_remove()

def cmd_clear_all(args):
    _LOG.debug("Removing all files stored by this application")

    cmd_clear_cache(args)
    cmd_clear_credentials(args)

    data_dir = UserDataDirectory()

    if data_dir.exists():
        data_dir.remove()
    else:
        _LOG.debug("Data dir doesn't exist. Nothing to do")


