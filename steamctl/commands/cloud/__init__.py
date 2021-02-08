
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


epilog = """\
"""

@register_command('cloud', help='Manage Steam Cloud files (e.g. save files, settings, etc)', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_l = sub_cp.add_parser("list", help="List files for app")
    scp_l.add_argument('-l', '--long', action='store_true', help='Shows extra info for every file')
#   fexcl = scp_l.add_mutually_exclusive_group()
#   fexcl.add_argument('-n', '--name', type=str, help='Wildcard for matching filepath')
#   fexcl.add_argument('-re', '--regex', type=str, help='Reguar expression for matching filepath')
    scp_l.add_argument('app_id', metavar='AppID', type=int, help='AppID to query')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_cloud_list')
