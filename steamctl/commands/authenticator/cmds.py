
import logging
from getpass import getpass
from time import time
from base64 import b64decode
from steamctl import __appname__
from steamctl.utils.storage import UserDataFile, UserDataDirectory
from steamctl.utils.prompt import pmt_confirmation, pmt_input
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import print_table, fmt_datetime
from steam import webapi, webauth
from steam.enums import EResult
from steam.guard import SteamAuthenticator, SteamAuthenticatorError

# patch session method
webapi._make_requests_session = make_requests_session

_LOG = logging.getLogger(__name__)

class BetterMWA(webauth.MobileWebAuth):
    def __init__(self, username):
        webauth.MobileWebAuth.__init__(self, username)

    def bcli_login(self, password=None, auto_twofactor=False, sa_instance=None):
        email_code = twofactor_code = ''

        while True:
            try:
                if not password:
                    raise webauth.LoginIncorrect
                return self.login(password, captcha, email_code, twofactor_code)
            except (webauth.LoginIncorrect, webauth.CaptchaRequired) as exp:
                email_code = twofactor_code = ''

                if auto_twofactor and sa_instance:
                    twofactor_code = sa_instance.get_code()

                if isinstance(exp, webauth.LoginIncorrect):
                    prompt = ("Enter password for %s: " if not password else
                              "Invalid password for %s. Enter password: ")
                    password = getpass(prompt % repr(self.username))
                if isinstance(exp, webauth.CaptchaRequired):
                    if captcha:
                        print("Login error: %s" % str(exp))
                        if not pmt_confirmation("Try again?", default_yes=True):
                            raise EOFError
                        self.refresh_captcha()

                    if self.captcha_url:
                        prompt = "Solve CAPTCHA at %s\nCAPTCHA code: " % self.captcha_url
                        captcha = input(prompt)
                        continue

                captcha = ''
            except webauth.EmailCodeRequired:
                prompt = ("Enter email code: " if not email_code else
                          "Incorrect code. Enter email code: ")
                email_code, twofactor_code = input(prompt), ''
            except webauth.TwoFactorCodeRequired as exp:
                if auto_twofactor:
                    print("Steam did not accept 2FA code")
                    raise EOFError

                if sa_instance:
                    print("Authenticator available. Leave blank to use it, or manually enter code")

                prompt = ("Enter 2FA code: " if not twofactor_code else
                          "Incorrect code. Enter 2FA code: ")

                code = input(prompt)

                if sa_instance and not code:
                    code = sa_instance.get_code()

                email_code, twofactor_code = '', code


def cmd_authenticator_add(args):
    account = args.account.lower().strip()
    secrets_file = UserDataFile('authenticator/{}.json'.format(account))
    sa = None

    if secrets_file.exists():
        if not args.force:
            print("There is already an authenticator for that account. Use --force to overwrite")
            return 1  # error
        sa = SteamAuthenticator(secrets_file.read_json())

    if args.from_secret:
        secret = b64decode(args.from_secret)
        if len(secret) != 20:
            print("Provided secret length is not 20 bytes (got %s)" % len(secret))
            return 1  # error

        sa = SteamAuthenticator({
            'account_name': account,
            'shared_secret': args.from_secret,
            'token_gid': 'Imported secret',
            'server_time': int(time()),
        })
        print("To import a secret, we need to login to Steam to verify")
    else:
        print("To add an authenticator, first we need to login to Steam")
    print("Account name:", account)

    wa = BetterMWA(account)
    try:
        wa.bcli_login(sa_instance=sa, auto_twofactor=bool(args.from_secret))
    except (KeyboardInterrupt, EOFError):
        print("Login interrupted")
        return 1  # error

    print("Login successful. Checking status...")

    if sa:
        sa.backend = wa
    else:
        sa = SteamAuthenticator(backend=wa)

    status = sa.status()
    _LOG.debug("Authenticator status: %s", status)

    if args.from_secret:
        if status['state'] == 1:
            sa.secrets['token_gid'] = status['token_gid']
            sa.secrets['server_time'] = status['time_created']
            sa.secrets['state'] = status['state']
            secrets_file.write_json(sa.secrets)
            print("Authenticator added successfully")
            return
        else:
            print("No authenticator on account, but we logged in with 2FA? This is impossible")
            return 1  # error

    if status['state'] == 1:
        print("This account already has an authenticator.")
        print("You need to remove it first, before proceeding")
        return 1 # error

    if not status['email_validated']:
        print("Account needs a verified email address")
        return 1 # error

    if not status['authenticator_allowed']:
        print("This account is now allowed to have authenticator")
        return 1 # error

    # check phone number, and add one if its missing
    if not sa.has_phone_number():
        print("No phone number on this account. This is required.")

        if pmt_confirmation("Do you want to add a phone number?", default_yes=True):
            print("Phone number need to include country code and no spaces.")

            while True:
                phnum = pmt_input("Enter phone number:", regex=r'^(\+|00)[0-9]+$')

                resp = sa.validate_phone_number(phnum)
                _LOG.debug("Phone number validation for %r: %s", phnum, resp)

                if not resp.get('is_valid', False):
                    print("That number is not valid for Steam.")
                    continue

                if not sa.add_phone_number(phnum):
                    print("Failed to add phone number!")
                    continue

                print("Phone number added. Confirmation SMS sent.")

                while not sa.confirm_phone_number(pmt_input("Enter SMS code:", regex='^[0-9]+$')):
                    print("Code was incorrect. Try again.")

                break
        else:
            # user declined adding a phone number, we cant proceed
            return 1  # error

    # being adding authenticator setup
    sa.add()

    _LOG.debug("Authenticator secrets obtained. Saving to disk")

    secrets_file.write_json(sa.secrets)

    # Setup Steam app in conjuction
    if pmt_confirmation("Do you want to use Steam Mobile app too? (Needed for trades)", default_yes=False):
        print("Great! Go and setup Steam Guard in your app.")
        print("Once completed, generate a code and enter it below.")

        showed_fail_info = False
        fail_counter = 0

        while True:
            code = pmt_input("Steam Guard code:", regex='^[23456789BCDFGHJKMNPQRTVWXYbcdfghjkmnpqrtvwxy]{5}$')

            # code match
            if sa.get_code() == code.upper():
                break # success
            # code do not match
            else:
                fail_counter += 1

                if fail_counter >= 3 and not showed_fail_info:
                    showed_fail_info = True
                    print("The codes do not match. This can be caused by:")
                    print("* The code was not entered correctly")
                    print("* Your system time is not synchronized")
                    print("* Steam has made changes to their backend")

                if not pmt_confirmation("Code mismatch. Try again?", default_yes=True):
                    _LOG.debug("Removing secrets file")
                    secrets_file.secure_remove()
                    return 1 # failed, exit

    # only setup steamctl 2fa
    else:
        print("Authenticator secrets obtained. SMS code for finalization sent.")

        while True:
            code = pmt_input("Enter SMS code:", regex='^[0-9]+$')
            try:
                sa.finalize(code)
            except SteamAuthenticatorError as exp:
                print("Finalization error: %s", exp)
                continue
            else:
                break

    # finish line
    print("Authenticator added successfully!")
    print("Get a code: {} authenticator code {}".format(__appname__, account))
    print("Or QR code: {} authenticator qrcode {}".format(__appname__, account))


def cmd_authenticator_remove(args):
    account = args.account.lower().strip()
    secrets_file = UserDataFile('authenticator/{}.json'.format(account))
    secrets = secrets_file.read_json()

    if not secrets:
        print("No authenticator found for %r" % account)
        return 1  #error

    if args.force:
        secrets_file.secure_remove()
        print("Forceful removal of %r successful" % account)
        return

    print("To remove an authenticator, first we need to login to Steam")
    print("Account name:", account)

    wa = BetterMWA(account)
    sa = SteamAuthenticator(secrets, backend=wa)

    try:
        wa.bcli_login(sa_instance=sa)
    except (KeyboardInterrupt, EOFError):
        print("Login interrupted")
        return 1  # error

    print("Login successful.")
    print("Steam Guard will be set to email, after removal.")

    while True:
        if not pmt_confirmation("Proceed with removing Steam Authenticator?"):
            break
        else:
            try:
                sa.remove()
            except SteamAuthenticatorError as exp:
                print("Removal error: %s" %  exp)
                continue
            except (EOFError, KeyboardInterrupt):
                break
            else:
                secrets_file.secure_remove()
                print("Removal successful!")
                return

    print("Removal cancelled.")

def cmd_authenticator_list(args):
    rows = []

    for secrets_file in UserDataDirectory('authenticator').iter_files('*.json'):
        secrets = secrets_file.read_json()
        rows.append([
            secrets_file.filename,
            secrets['account_name'],
            secrets['token_gid'],
            fmt_datetime(int(secrets['server_time']), utc=args.utc),
            'Created via steamctl' if 'serial_number' in secrets else 'Imported from secret'
            ])

    if rows:
        print_table(rows,
                    ['Filename', 'Account', 'Token GID', 'Created', 'Note'],
                    )
    else:
        print("No authenticators found")

def cmd_authenticator_status(args):
    account = args.account.lower().strip()
    secrets_file = UserDataFile('authenticator/{}.json'.format(account))
    sa = None

    wa = BetterMWA(account)

    if secrets_file.exists():
        sa = SteamAuthenticator(secrets_file.read_json(), backend=wa)

    try:
        wa.bcli_login(sa_instance=sa)
    except (KeyboardInterrupt, EOFError):
        print("Login interrupted")
        return 1  # error

    if sa is None:
        sa = SteamAuthenticator(backend=wa)

    status = sa.status()

    print("----- Status ------------")
    mode = status['steamguard_scheme']

    if mode == 0:
        print("Steam Guard mode: disabled/insecure")
    elif mode == 1:
        print("Steam Guard mode: enabled (email)")
    elif mode == 2:
        print("Steam Guard mode: enabled (authenticator)")
    else:
        print("Steam Guard mode: unknown ({})".format(mode))

    print("Authenticator enabled:", "Yes" if status['state'] == 1 else "No")
    print("Authenticator allowed:", "Yes" if status['state'] else "No")
    print("Email verified:", "Yes" if status['email_validated'] else "No")
    print("External allowed:", "Yes" if status['allow_external_authenticator'] else "No")

    if status['state'] == 1:
        print("----- Token details -----")
        print("Token GID:", status['token_gid'])
        print("Created at:", fmt_datetime(status['time_created']))
        print("Device identifier:", status['device_identifier'])
        print("Classified agent:", status['classified_agent'])
        print("Revocation attempts remaining:", status['revocation_attempts_remaining'])

