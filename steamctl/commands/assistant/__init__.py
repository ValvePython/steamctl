
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

    scp_i = sub_cp.add_parser("idle-cards", help="Automatic idling for game cards")
    scp_i.set_defaults(_cmd_func=__name__ + '.card_idler:cmd_assistant_idle_cards')

    scp_i = sub_cp.add_parser("springcleaning2020", help="Complete 'Dust off your library with DEWEY!'")
    scp_i.set_defaults(_cmd_func=__name__ + '.springcleaning2020:cmd_assistant_sc2020')
