
import logging
from getpass import getpass
from steamctl import __appname__
from steamctl.utils.storage import UserDataFile, UserDataDirectory
from steamctl.utils.prompt import pmt_confirmation, pmt_input
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import print_table, fmt_datetime
from steam import webapi, webauth
from steam.guard import SteamAuthenticator, SteamAuthenticatorError

# patch session method
webapi._make_requests_session = make_requests_session

_LOG = logging.getLogger(__name__)

class BetterMWA(webauth.MobileWebAuth):
    def __init__(self, username):
        webauth.MobileWebAuth.__init__(self, username)

    def bcli_login(self, password=None, sa_instance=None):
        email_code = twofactor_code = ''

        while True:
            try:
                if not password:
                    raise webauth.LoginIncorrect
                return self.login(password, captcha, email_code, twofactor_code)
            except (webauth.LoginIncorrect, webauth.CaptchaRequired) as exp:
                email_code = twofactor_code = ''

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
                if not sa_instance:
                    prompt = ("Enter 2FA code: " if not twofactor_code else
                              "Incorrect code. Enter 2FA code: ")
                    email_code, twofactor_code = '', input(prompt)
                else:
                    if twofactor_code:
                        print("Login error: %s" % str(exp))
                        if not pmt_confirmation("Try again?", default_yes=True):
                            raise EOFError

                    email_code, twofactor_code = '', sa_instance.get_code()


def cmd_authenticator_add(args):
    account = args.account.lower().strip()
    secrets_file = UserDataFile('authenticator/{}.json'.format(account))

    if secrets_file.exists() and not args.force:
        print("There is already an authenticator for that account. Use --force to overwrite")
        return 1  # error

    print("To add an authenticator, first we need to login to Steam")
    print("Account name:", account)

    wa = BetterMWA(account)
    try:
        wa.bcli_login()
    except (KeyboardInterrupt, EOFError):
        print("Login interrupted")
        return 1  # error

    print("Login successful. Checking pre-conditions...")

    sa = SteamAuthenticator(backend=wa)

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
    if pmt_confirmation("Do you want to use Steam app too?", default_yes=False):
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
                    secrets_file.remove()
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
    print("To get a code run: {} authenticator code {}".format(__appname__, account))
    print("Or for QRcode run: {} authenticator qrcode {}".format(__appname__, account))


def cmd_authenticator_remove(args):
    account = args.account.lower().strip()
    secrets_file = UserDataFile('authenticator/{}.json'.format(account))
    secrets = secrets_file.read_json()

    if not secrets:
        print("No authenticator found for %r" % account)
        return 1  #error

    if args.force:
        secrets_file.remove()
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
                secrets_file.remove()
                print("Removal successfu!")
                return

    print("Removal cancelled.")

def cmd_authenticator_list(args):
    rows = []

    for secrets_file in UserDataDirectory('authenticator').iter_files('*.json'):
        secrets = secrets_file.read_json()
        rows.append([
            secrets['account_name'],
            secrets['token_gid'],
            fmt_datetime(int(secrets['server_time']), utc=args.utc),
            ])

    if rows:
        print_table(rows,
                    ['Account', 'Token GID', 'Created'],
                    )
    else:
        print("No authenticators found")

def cmd_authenticator_code(args):
    account = args.account.lower().strip()
    secrets = UserDataFile('authenticator/{}.json'.format(account)).read_json()

    if not secrets:
        print("No authenticator for %r" % account)
        return 1  # error

    print(SteamAuthenticator(secrets).get_code())

def cmd_authenticator_qrcode(args):
    account = args.account.lower().strip()
    secrets = UserDataFile('authenticator/{}.json'.format(account)).read_json()

    if not secrets:
        print("No authenticator for %r" % account)
        return 1  # error

    import pyqrcode
    from base64 import b64decode, b32encode

    if args.alt:
        FG, BG = '0', '1'
    else:
        FG, BG = '1', '0'

    charmap = {
      (BG, BG): '█',
      (FG, FG): ' ',
      (BG, FG): '▀',
      (FG, BG): '▄',
    }

    uri = 'otpauth://totp/steamctl:{user}?secret={secret}&issuer=Steam&digits=5'.format(user=secrets['account_name'],
                                                                                        secret=b32encode(b64decode(secrets['shared_secret'])).decode('ascii'),
                                                                                        )

    qrlines = pyqrcode.create(uri, error='M').text(1).split('\n')[:-1]

    print("Scan the QR code with Aegis Authenticator")
    print("!!! Change the type from TOTP to Steam in the app !!!")

    for y in range(0, len(qrlines), 2):
        for x in range(0, len(qrlines[y])):
            print(charmap[(qrlines[y][x], FG if y+1 >= len(qrlines) else qrlines[y+1][x])], end='')
        print()

