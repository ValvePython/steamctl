
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


epilog = """\

Examples:

    Listing and downloading personal game files, such as saved files for Black Mesa (362890):
        {prog} cloud list 362890
        {prog} cloud download -o savefiles 362890

    Listing all screenshots on the account. App 760 is where Steam stores screenshots.
        {prog} cloud list 760

    Downloading all screenshots to a directory called "screenshots":
        {prog} cloud download -o screenshots 760

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
    scp_l.add_argument('--long', action='store_true', help='Shows extra info for every file')
#   fexcl = scp_l.add_mutually_exclusive_group()
#   fexcl.add_argument('-n', '--name', type=str, help='Wildcard for matching filepath')
#   fexcl.add_argument('-re', '--regex', type=str, help='Reguar expression for matching filepath')
    scp_l.add_argument('app_id', metavar='AppID', type=int, help='AppID to query')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_cloud_list')

    scp_la = sub_cp.add_parser("list_apps", help="List all apps with cloud files")
    scp_la.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_cloud_list_apps')

    scp_dl = sub_cp.add_parser("download", help="Download files for app")
    scp_dl.add_argument('-o', '--output', type=str, default='', help='Path to directory for the downloaded files (default: cwd)')
    scp_dl.add_argument('-np', '--no-progress', action='store_true', help='Do not create directories')
    scp_dl.add_argument('app_id', metavar='AppID', type=int, help='AppID to query')
    scp_dl.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_cloud_download')
