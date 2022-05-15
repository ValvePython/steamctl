import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

import os
import logging
from time import time
from steam.enums import EResult, EPersonaState
from steam.client import SteamClient, _cli_input, getpass
from steam.client.cdn import CDNClient, CDNDepotManifest, CDNDepotFile, ContentServer
from steam.exceptions import SteamError
from steam.core.crypto import sha1_hash

from steamctl.utils.format import fmt_size
from steamctl.utils.storage import (UserCacheFile, UserDataFile,
                                    UserCacheDirectory, UserDataDirectory,
                                    ensure_dir, sanitizerelpath
                                    )

cred_dir = UserDataDirectory('client')

class CachingSteamClient(SteamClient):
    credential_location = cred_dir.path
    persona_state = EPersonaState.Offline

    def __init__(self, *args, **kwargs):
        if not cred_dir.exists():
            cred_dir.mkdir()
        SteamClient.__init__(self, *args, **kwargs)
        _LOG = logging.getLogger('CachingSteamClient')
        self._bootstrap_cm_list_from_file()

    def _handle_login_key(self, message):
        SteamClient._handle_login_key(self, message)

        with UserDataFile('client/%s.key' % self.username).open('w') as fp:
            fp.write(self.login_key)

    def get_cdnclient(self):
        return CachingCDNClient(self)

    def login_from_args(self, args, print_status=True):
        result = None

        # anonymous login
        if args.anonymous and not args.user:
            self._LOG.info("Attempting anonymous login")
            return self.anonymous_login()

        # user login
        user = args.user
        lastFile = UserDataFile('client/lastuser')

        # check for previously used user
        if not user and lastFile.exists():
            user = lastFile.read_text()

            if user:
                self._LOG.info("Reusing previous username: %s", user)
                self._LOG.info("Hint: use 'steamctl --user <username> ...' to change")
            else:
                self._LOG.debug("lastuser file is empty?")
                lastFile.remove()

        if user:
            # attempt login
            self.username = user

            if not lastFile.exists() or lastFile.read_text() != self.username:
                lastFile.write_text(self.username)

            # check for userkey and login without a prompt
            userkey =  UserDataFile('client/%s.key' % self.username)
            if userkey.exists():
                self._LOG.info("Attempting login with remembered credentials")
                self.login_key = userkey.read_text()
                result = self.relogin()

                self._LOG.debug("Re-login result is: %s", repr(EResult(result)))

                if result == EResult.InvalidPassword:
                    self._LOG.info("Remembered credentials have expired")
                    userkey.remove()
                else:
                    return result

            self.sleep(0.1)

        # attempt manual cli login
        if not self.logged_on:
            result = EResult.InvalidPassword

            if not self.username:
                self._LOG.info("Enter Steam login")
                self.username = _cli_input("Username: ")
            else:
                self._LOG.info("Enter credentials for: %s", self.username)

            password = getpass()

            # check for existing authenticator
            secrets_file = UserDataFile('authenticator/{}.json'.format(self.username))

            if secrets_file.exists():
                from steam.guard import SteamAuthenticator
                sa = SteamAuthenticator(secrets_file.read_json())

                while result == EResult.InvalidPassword:
                    result = self.login(self.username, password, two_factor_code=sa.get_code())

                    if result == EResult.InvalidPassword:
                        password = getpass("Invalid password for %s. Enter password: " % repr(self.username))
                        self.sleep(0.1)

            if result != EResult.OK:
                result = self.cli_login(self.username, password)

        if not lastFile.exists() or lastFile.read_text() != self.username:
            lastFile.write_text(self.username)

        self._LOG.debug("Login result is: %s", repr(EResult(result)))

        if not self.relogin_available:
            self.wait_event(self.EVENT_NEW_LOGIN_KEY, timeout=10)

        return result

    def check_for_changes(self):
        """Check for changes since last check, and expire any cached appinfo"""
        changefile = UserCacheFile('last_change_number')
        change_number = 0

        if changefile.exists():
            try:
                change_number = int(changefile.read_text())
            except:
                changefile.remove()

        self._LOG.debug("Checking PICS for app changes")
        resp = self.get_changes_since(change_number, True, False)

        if resp.force_full_app_update:
            change_number = 0

        if resp.current_change_number != change_number:
            with changefile.open('w') as fp:
                fp.write(str(resp.current_change_number))

            changed_apps = set((entry.appid for entry in resp.app_changes))

            if change_number == 0 or changed_apps:
                self._LOG.debug("Checking for outdated cached appinfo files")

                for appinfo_file in UserCacheDirectory('appinfo').iter_files('*.json'):
                    app_id = int(appinfo_file.filename[:-5])

                    if change_number == 0 or app_id in changed_apps:
                        appinfo_file.remove()

    def has_cached_appinfo(self, app_id):
        return UserCacheFile("appinfo/{}.json".format(app_id)).exists()

    def get_cached_appinfo(self, app_id):
        cache_file = UserCacheFile("appinfo/{}.json".format(app_id))

        if cache_file.exists():
            return cache_file.read_json()

    def get_product_info(self, apps=[], packages=[], *args, **kwargs):
        resp = {'apps': {}, 'packages': {}}

        # if we have cached info for all apps, just serve from cache
        if apps and all(map(self.has_cached_appinfo, apps)):
            self._LOG.debug("Serving appinfo from cache")

            for app_id in apps:
                resp['apps'][app_id] = self.get_cached_appinfo(app_id)

            apps = []

        if apps or packages:
            self._LOG.debug("Fetching product info")
            fresh_resp = SteamClient.get_product_info(self, apps, packages, *args, **kwargs)

            if apps:
                for app_id, appinfo in fresh_resp['apps'].items():
                    if not appinfo['_missing_token']:
                        UserCacheFile("appinfo/{}.json".format(app_id)).write_json(appinfo)
                resp = fresh_resp
            else:
                resp['packages'] = fresh_resp['packages']

        return resp


class CTLDepotFile(CDNDepotFile):
    _LOG = logging.getLogger('CTLDepotFile')

    def download_to(self, target, no_make_dirs=False, pbar=None, verify=True):
        relpath = sanitizerelpath(self.filename)

        if no_make_dirs:
            relpath = os.path.basename(relpath)

        relpath = os.path.join(target, relpath)

        filepath = os.path.abspath(relpath)
        ensure_dir(filepath)

        checksum = self.file_mapping.sha_content.hex()

        # don't bother verifying if file doesn't already exist
        if not os.path.exists(filepath):
            verify = False

        with open(filepath, 'r+b' if verify else 'wb') as fp:
            fp.seek(0, 2)

            # pre-allocate space
            if fp.tell() != self.size:
                newsize = fp.truncate(self.size)

                if newsize != self.size:
                    raise SteamError("Failed allocating space for {}".format(filepath))

#           self._LOG.info('{} {}  ({}, sha1:{})'.format(
#                              'Verifying' if verify else 'Downloading',
#                              relpath,
#                              fmt_size(self.size),
#                              checksum
#                              ))

            fp.seek(0)
            for chunk in self.chunks:
                # verify chunk sha hash
                if verify:
                    cur_data = fp.read(chunk.cb_original)

                    if sha1_hash(cur_data) == chunk.sha:
                        if pbar:
                            pbar.update(chunk.cb_original)
                        continue

                    fp.seek(chunk.offset)  # rewind before write

                # download and write chunk
                data = self.manifest.cdn_client.get_chunk(
                                self.manifest.app_id,
                                self.manifest.depot_id,
                                chunk.sha.hex(),
                                )

                fp.write(data)

                if pbar:
                    pbar.update(chunk.cb_original)

class CTLDepotManifest(CDNDepotManifest):
    DepotFileClass = CTLDepotFile


class CachingCDNClient(CDNClient):
    DepotManifestClass = CTLDepotManifest
    _LOG = logging.getLogger('CachingCDNClient')
    _depot_keys = None
    skip_licenses = False

    def __init__(self, *args, **kwargs):
        CDNClient.__init__(self, *args, **kwargs)

    def fetch_content_servers(self, *args, **kwargs):
        cached_cs = UserDataFile('cs_servers.json')

        data = cached_cs.read_json()

        # load from cache, only keep for 5 minutes
        if data and (data['timestamp'] + 300) > time():
            for server in data['servers']:
                entry = ContentServer()
                entry.__dict__.update(server)
                self.servers.append(entry)
            return

        # fetch cs servers
        CDNClient.fetch_content_servers(self, *args, **kwargs)

        # cache cs servers
        data = {
            "timestamp": int(time()),
            "cell_id": self.cell_id,
            "servers": list(map(lambda x: x.__dict__, self.servers)),
        }

        cached_cs.write_json(data)

    @property
    def depot_keys(self):
        if not self._depot_keys:
            self._depot_keys.update(self.get_cached_depot_keys())
        return self._depot_keys

    @depot_keys.setter
    def depot_keys(self, value):
        self._depot_keys = value

    def get_cached_depot_keys(self):
        return {int(depot_id): bytes.fromhex(key)
                for depot_id, key in (UserDataFile('depot_keys.json').read_json() or {}).items()
                }

    def save_cache(self):
        cached_depot_keys = self.get_cached_depot_keys()

        if cached_depot_keys == self.depot_keys:
            return

        self.depot_keys.update(cached_depot_keys)
        out = {str(depot_id): key.hex()
               for depot_id, key in self.depot_keys.items()
               }

        UserDataFile('depot_keys.json').write_json(out)

    def has_cached_app_depot_info(self, app_id):
        if app_id in self.app_depots:
            return True
        cached_appinfo = UserCacheFile("appinfo/{}.json".format(app_id))
        if cached_appinfo.exists():
            return True
        return False


    def has_license_for_depot(self, depot_id):
        if self.skip_licenses:
            return True
        else:
            return CDNClient.has_license_for_depot(self, depot_id)

    def get_app_depot_info(self, app_id):
        if app_id not in self.app_depots:
            try:
                appinfo = self.steam.get_product_info([app_id])['apps'][app_id]
            except KeyError:
                raise SteamError("Invalid app id")

            if appinfo['_missing_token']:
                raise SteamError("No access token available")

            self.app_depots[app_id] = appinfo.get('depots', {})

        return self.app_depots[app_id]

    def get_cached_manifest(self, app_id, depot_id, manifest_gid):
        key = (app_id, depot_id, manifest_gid)

        if key in self.manifests:
            return self.manifests[key]

        # if we don't have the manifest loaded, check cache
        cached_manifest = UserCacheFile("manifests/{}_{}_{}".format(app_id, depot_id, manifest_gid))

        # we have a cached manifest file, load it
        if cached_manifest.exists():
            with cached_manifest.open('r+b') as fp:
                try:
                    manifest = self.DepotManifestClass(self, app_id, fp.read())
                except Exception as exp:
                    self._LOG.debug("Error parsing cached manifest: %s", exp)
                else:
                    # if its not empty, load it
                    if manifest.gid > 0:
                        self.manifests[key] = manifest

                        # update cached file if we have depot key for it
                        if manifest.filenames_encrypted and manifest.depot_id in self.depot_keys:
                            manifest.decrypt_filenames(self.depot_keys[manifest.depot_id])
                            fp.seek(0)
                            fp.write(manifest.serialize(compress=False))
                            fp.truncate()

                        return manifest

            # empty manifest files shouldn't exist, handle it gracefully by removing the file
            if key not in self.manifests:
                self._LOG.debug("Found cached manifest, but encountered error or file is empty")
                cached_manifest.remove()

    def get_manifest(self, app_id, depot_id, manifest_gid, decrypt=True, manifest_request_code=None):
        key = (app_id, depot_id, manifest_gid)
        cached_manifest = UserCacheFile("manifests/{}_{}_{}".format(*key))

        if decrypt and depot_id not in self.depot_keys:
            self.get_depot_key(app_id, depot_id)

        manifest = self.get_cached_manifest(*key)

        # if manifest not cached, download from CDN
        if not manifest:
            manifest = CDNClient.get_manifest(
                self, app_id, depot_id, manifest_gid, decrypt=decrypt, manifest_request_code=manifest_request_code
            )

            # cache the manifest
            with cached_manifest.open('wb') as fp:
                fp.write(manifest.serialize(compress=False))

        return self.manifests[key]
