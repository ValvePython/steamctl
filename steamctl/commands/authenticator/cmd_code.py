import logging
import struct
from time import time
from base64 import b64decode, b32encode
from hashlib import sha1
import hmac
from steamctl import __appname__
from steamctl.utils.storage import UserDataFile

_LOG = logging.getLogger(__name__)

def generate_twofactor_code_for_time(shared_secret, timestamp):
    """Generate Steam 2FA code for timestamp

    :param shared_secret: authenticator shared secret
    :type shared_secret: bytes
    :param timestamp: timestamp to use, if left out uses current time
    :type timestamp: int
    :return: steam two factor code
    :rtype: str
    """
    hashed = hmac.new(bytes(shared_secret), struct.pack('>Q', int(timestamp)//30), sha1).digest()

    start = ord(hashed[19:20]) & 0xF
    codeint = struct.unpack('>I', hashed[start:start+4])[0] & 0x7fffffff

    charset = '23456789BCDFGHJKMNPQRTVWXY'
    code = ''

    for _ in range(5):
        codeint, i = divmod(codeint, len(charset))
        code += charset[i]

    return code

def cmd_authenticator_code(args):
    account = args.account.lower().strip()
    secrets = UserDataFile('authenticator/{}.json'.format(account)).read_json()

    if not secrets:
        print("No authenticator for %r" % account)
        return 1  # error

    print(generate_twofactor_code_for_time(b64decode(secrets['shared_secret']), time()))

def cmd_authenticator_qrcode(args):
    account = args.account.lower().strip()
    secrets = UserDataFile('authenticator/{}.json'.format(account)).read_json()

    if not secrets:
        print("No authenticator for %r" % account)
        return 1  # error

    import pyqrcode

    if args.invert:
        FG, BG = '0', '1'
    else:
        FG, BG = '1', '0'

    charmap = {
      (BG, BG): '█',
      (FG, FG): ' ',
      (BG, FG): '▀',
      (FG, BG): '▄',
    }

    if args.compat:
        uri = 'otpauth://totp/steamctl:{user}?secret={secret}&issuer=Steam&digits=5'
    else:
        uri = 'otpauth://steam/steamctl:{user}?secret={secret}&issuer=Steam'


    uri = uri.format(user=secrets['account_name'],
                     secret=b32encode(b64decode(secrets['shared_secret'])).decode('ascii'),
                     )

    qrlines = pyqrcode.create(uri, error='M').text(1).split('\n')[:-1]

    print("Suggested 2FA App: Aegis, andOTP")
    print("Scan the QR code below:")

    for y in range(0, len(qrlines), 2):
        for x in range(0, len(qrlines[y])):
            print(charmap[(qrlines[y][x], FG if y+1 >= len(qrlines) else qrlines[y+1][x])], end='')
        print()

