
from steamctl.argparser import register_command

@register_command('hlmaster', help='Query master server and server information')
def setup_arg_parser(cp):

    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)
    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_query = sub_cp.add_parser("query", help="Query HL Master for servers")
    scp_query.add_argument('filter', type=str)
    scp_query.add_argument('--ip-only', action='store_true', help='Show short info about each server')
    scp_query.add_argument('-n', '--num-servers',  default=20, type=int, help="Number of result to return (Default: 20)")
    scp_query.add_argument('-m', '--master', default=None, type=str, help="Master server (default: hl2master.steampowered.com:27011)")
    scp_query.set_defaults(_cmd_func=__name__ + '.cmds:cmd_hlmaster_query')

    scp_info = sub_cp.add_parser("info", help="Query info from a goldsrc or source server")
    scp_info.add_argument('server', type=str)
    scp_info.add_argument('-i', '--info', action='store_true', help='Show server info')
    scp_info.add_argument('-r', '--rules', action='store_true', help='Show server rules')
    scp_info.add_argument('-p', '--players', action='store_true', help='Show player list')
    scp_info.add_argument('-s', '--short', action='store_true', help='Print server info in short form')
    scp_info.set_defaults(_cmd_func=__name__ + '.cmds:cmd_hlmaster_info')
