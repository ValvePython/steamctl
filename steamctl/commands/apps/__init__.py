
import argparse
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


epilog = """\

Examples:

    TODO

"""

@register_command('apps', help='Get information about apps', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    # ---- list_names
    scp_l = sub_cp.add_parser("list_names", help="List all public apps and their names")
    scp_l.set_defaults(_cmd_func=__name__ + '.cmds:cmd_apps_list_names')

    # ---- product_info
    scp_l = sub_cp.add_parser("product_info", help="Show product info about an app")
    scp_l.add_argument('--skip-licenses', action='store_true', help='Skip license check')
    scp_l.add_argument('app_ids', nargs='+', metavar='AppID', type=int, help='AppID to query')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_product_info')
