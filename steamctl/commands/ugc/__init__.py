
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


epilog = """\
"""

@register_command('ugc', help='Info and download of user generated content', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_i = sub_cp.add_parser("info", help="Get details for UGC")
    scp_i.add_argument('ugc', type=int, help='UGC ID')
    scp_i.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_ugc_info')

    scp_dl = sub_cp.add_parser("download", help="Download UGC")
    scp_dl.add_argument('-o', '--output', type=str, default='', help='Path to directory for the downloaded files (default: cwd)')
    scp_dl.add_argument('-nd', '--no-directories', action='store_true', help='Do not create directories')
    scp_dl.add_argument('-np', '--no-progress', action='store_true', help='Do not create directories')
    scp_dl.add_argument('ugc', type=int, help='UGC ID')
    scp_dl.set_defaults(_cmd_func=__name__ + '.gcmds:cmd_ugc_download')
