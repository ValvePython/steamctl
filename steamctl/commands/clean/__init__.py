
from steamctl.argparser import register_command

@register_command('clear', help='Remove data stored on disk')
def setup_arg_parser(cp):

    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)
    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_c = sub_cp.add_parser("cache", help="Remove all cache files")
    scp_c.set_defaults(_cmd_func=__name__ + '.cmds:cmd_clear_cache')
    scp_c = sub_cp.add_parser("credentials", help="Remove all credentials and saved logins")
    scp_c.set_defaults(_cmd_func=__name__ + '.cmds:cmd_clear_credentials')
    scp_c = sub_cp.add_parser("all", help="Remove all cache and data files")
    scp_c.set_defaults(_cmd_func=__name__ + '.cmds:cmd_clear_all')
