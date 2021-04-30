
import argparse
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


epilog = """\

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

    # ---- activate_key
    scp_l = sub_cp.add_parser("activate_key", help="Activate key(s) on account")
    scp_l.add_argument('keys', metavar='GameKey', nargs='+', type=str, help='Key(s) to activate')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_activate_key')

    # -------------- SUBCOMMAND ----------------------

    # ---- licenses
    lcp = sub_cp.add_parser("licenses", help="Manage licenses", description="Manage licenses")

    def print_help(*args, **kwargs):
        lcp.print_help()

    lcp.set_defaults(_cmd_func=print_help)

    lsub_cp = lcp.add_subparsers(metavar='<subcommand>',
                                 dest='subcommand2',
                                 title='List of sub-commands',
                                 description='',
                                 )

    # ---- licenses list
    scp_l = lsub_cp.add_parser("list", help="List owned or all apps")
    scp_l.add_argument('--app', type=int, nargs='*', help='Only licenses granting these app ids')

    def completer_billingtype(prefix, parsed_args, **kwargs):
        from steam.enums import EBillingType
        return [bt.name for bt in EBillingType]

    scp_l.add_argument('--billingtype', type=str, nargs='*', metavar='BT',
                       help='Only licenses of billing type (e.g. ActivationCode, Complimentary, FreeOnDemand)',
                       ).completer = completer_billingtype

    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_licenses_list')

    scp_l = lsub_cp.add_parser("add", help="Add free package license(s)")
    scp_l.add_argument('pkg_ids', metavar='PackageID', nargs='+', type=int, help='Package ID to add')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_licenses_add')

    scp_l = lsub_cp.add_parser("remove", help="Remove free package license(s)")
    scp_l.add_argument('pkg_ids', metavar='PackageID', nargs='+', type=int, help='Package ID to remove')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_licenses_remove')

    # -------------- END SUBCOMMAND ----------------------

    # ---- list
    scp_l = sub_cp.add_parser("list", help="List owned or all apps")
    scp_l.add_argument('--all', action='store_true', help='List all apps on Steam')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_list')

    # ---- product_info
    scp_l = sub_cp.add_parser("product_info", help="Show product info for app")
    scp_l.add_argument('--skip-licenses', action='store_true', help='Skip license check')
    scp_l.add_argument('app_ids', nargs='+', metavar='AppID', type=int, help='AppID to query')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_product_info')

    # ---- item_def
    scp_l = sub_cp.add_parser("item_def", help="Get item definitions for app")
    scp_l.add_argument('app_id', metavar='AppID', type=int, help='AppID to query')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_apps_item_def')
