
from steamctl.argparser import register_command


epilog = """\
"""

@register_command('assistant', help='Helpful automation', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_i = sub_cp.add_parser("idle-games", help="Idle up to 32 games for game time")
    scp_i.set_defaults(_cmd_func=__name__ + '.card_idler:cmd_assistant_idle_games')
    scp_i.add_argument('app_ids', nargs='+', metavar='AppID', type=int, help='App ID(s) to idle')

    scp_i = sub_cp.add_parser("idle-cards", help="Automatic idling for game cards")
    scp_i.set_defaults(_cmd_func=__name__ + '.card_idler:cmd_assistant_idle_cards')

    scp_i = sub_cp.add_parser("discovery-queue", help="Explore a single discovery queue")
    scp_i.set_defaults(_cmd_func=__name__ + '.discovery_queue:cmd_assistant_discovery_queue')
