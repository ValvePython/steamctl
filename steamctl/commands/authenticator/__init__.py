
import sys
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataDirectory

epilog = """\
"""

@register_command('authenticator', help='Manage Steam authenticators', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp = sub_cp.add_parser("add", help="Add authentictor to a Steam account")
    scp.add_argument('--force', action='store_true',
                     help='Overwrite existing authenticator.'
                     )
    scp.add_argument('--from-secret', type=str,
                     help='Provide the authenticator secret directly. Need to be base64 encoded.'
                     )
    scp.add_argument('account', type=str, help='Account name')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_add')

    scp = sub_cp.add_parser("remove", help="Remove an authenticator")
    scp.add_argument('--force', action='store_true',
                     help='Delete local secrets only. Does not attempt to remove from account. '
                          'This may lead to losing access to the account if the authenticator '
                          'is still attached to an account.'
                     )
    scp.add_argument('account', type=str, help='Account name')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_remove')

    scp = sub_cp.add_parser("list", help="List all authenticators")
    scp.add_argument('--utc', action='store_true', help='Show datetime in UTC')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_list')

    def account_autocomplete(prefix, parsed_args, **kwargs):
        return [userfile.filename[:-5]
                for userfile in UserDataDirectory('authenticator').iter_files('*.json')]

    scp = sub_cp.add_parser("status", help="Query Steam Guard status for account")
    scp.add_argument('account', type=str, help='Account name').completer = account_autocomplete
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_status')

    scp = sub_cp.add_parser("code", help="Generate auth code")
    scp.add_argument('account', type=str, help='Account name').completer = account_autocomplete
    scp.set_defaults(_cmd_func=__name__ + '.cmd_code:cmd_authenticator_code')

    scp = sub_cp.add_parser("qrcode", help="Generate QR code")
    scp.add_argument('--compat', action='store_true',
                     help='Alternative QR code mode (e.g. otpauth://totp/....). '
                          'The default mode is custom format (otpath://steam/...), and requires custom Steam support in your 2FA app. '
                          'Apps with support: Aegis and andOTP.'
                     )
    scp.add_argument('--invert', action='store_true',
                     help='Invert QR code colors. Try if app fails to scan the code.'
                     )
    scp.add_argument('account', type=str, help='Account name').completer = account_autocomplete
    scp.set_defaults(_cmd_func=__name__ + '.cmd_code:cmd_authenticator_qrcode')

