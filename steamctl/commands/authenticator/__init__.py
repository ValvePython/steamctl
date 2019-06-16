
import sys
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


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
    scp.add_argument('account', type=str, help='Account name')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_add')

    scp = sub_cp.add_parser("remove", help="Remove an authenticator")
    scp.add_argument('--force', action='store_true',
                     help='Force removed authenticator. '
                          'If authenticator is still attached to an account '
                          'you will lose access to the account!'
                     )
    scp.add_argument('account', type=str, help='Account name')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_remove')

    scp = sub_cp.add_parser("list", help="List all authenticators")
    scp.add_argument('--utc', action='store_true', help='Show datetime in UTC')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_list')

    scp = sub_cp.add_parser("code", help="Generate auth code")
    scp.add_argument('account', nargs='?', type=str, help='Account name')
    scp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_authenticator_code')

