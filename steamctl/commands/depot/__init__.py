
import argparse
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


epilog = """\

Examples:

    Show manifest info for specific manifest:
        {prog} depot info --app 570 --depot 570 --manifest 7280959080077824592

    Show manifest info from a file:
        {prog} depot info -f /Steam/depotcache/381450_8619474727384971127.manifest

    List manifest files:
        {prog} depot list -f /Steam/depotcache/381450_8619474727384971127.manifest

    List files from all manifest for app:
        {prog} depot list --app 570

    Download files from a manifest to a directory called 'temp':
        {prog} depot download --app 570 --depot 570 --manifest 7280959080077824592 -o ./temp

    Download all files for an app to a directory called 'temp':
        {prog} depot download --app 570 -o ./temp

"""

@register_command('depot', help='List and download from Steam depots', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_i = sub_cp.add_parser("info", help="View info about a depot(s)")
    scp_i.add_argument('--cell_id', type=int, help='Cell ID to use for download')
    scp_i.add_argument('-os', choices=['any', 'windows', 'windows64', 'linux', 'linux64', 'macos'],
                       default='any',
                       help='Operating system (Default: any)')
    scp_i.add_argument('-f', '--file', type=argparse.FileType('rb'), nargs='?', help='Path to a manifest file')
    scp_i.add_argument('-a', '--app', type=int, help='App ID')
    scp_i.add_argument('-d', '--depot', type=int, help='Depot ID')
    scp_i.add_argument('-m', '--manifest', type=int, help='Manifest GID')
    scp_i.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_depot_info')

    scp_l = sub_cp.add_parser("list", help="List files from depot(s)")
    scp_l.add_argument('--cell_id', type=int, help='Cell ID to use for download')
    scp_l.add_argument('-os', choices=['any', 'windows', 'windows64', 'linux', 'linux64', 'macos'],
                       default='any',
                       help='Operating system (Default: any)')
    scp_l.add_argument('-f', '--file', type=argparse.FileType('rb'), nargs='?', help='Path to a manifest file')
    scp_l.add_argument('-a', '--app', type=int, help='App ID')
    scp_l.add_argument('-d', '--depot', type=int, help='Depot ID')
    scp_l.add_argument('-m', '--manifest', type=int, help='Manifest GID')
    scp_l.add_argument('-l', '--long', action='store_true', help='Shows extra info for every file')
    fexcl = scp_l.add_mutually_exclusive_group()
    fexcl.add_argument('-n', '--name', type=str, help='Wildcard for matching filepath')
    fexcl.add_argument('-re', '--regex', type=str, help='Reguar expression for matching filepath')
    scp_l.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_depot_list')

    scp_dl = sub_cp.add_parser("download", help="Download depot files")
    scp_dl.add_argument('--cell_id', type=int, help='Cell ID to use for download')
    scp_dl.add_argument('-os', choices=['any', 'windows', 'windows64', 'linux', 'linux64', 'macos'],
                        default='any',
                        help='Operating system (Default: any)')
    scp_dl.add_argument('-o', '--output', type=str, default='', help='Path to directory for the downloaded files (default: cwd)')
    scp_dl.add_argument('-nd', '--no-directories', action='store_true', help='Do not create directories')
    scp_dl.add_argument('-np', '--no-progress', action='store_true', help='Do not create directories')
    scp_dl.add_argument('-a', '--app', type=int, help='App ID')
    scp_dl.add_argument('-d', '--depot', type=int, help='Depot ID')
    scp_dl.add_argument('-m', '--manifest', type=int, help='Manifest GID')
    fexcl = scp_dl.add_mutually_exclusive_group()
    fexcl.add_argument('-n', '--name', type=str, help='Wildcard for matching filepath')
    fexcl.add_argument('-re', '--regex', type=str, help='Reguar expression for matching filepath')
    scp_dl.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_depot_download')
