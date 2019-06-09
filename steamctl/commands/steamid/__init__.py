
from steamctl.argparser import register_command

epilog = """\
Example usage:
    {prog} steamid 4
"""


@register_command('steamid', help='Parse SteamID representations', epilog=epilog)
def cmd_parser(cp):
    cp.add_argument('s_input', metavar='<accountid|steamid64|steam2|steam3|url>')
    cp.set_defaults(_cmd_func=__name__ + '.cmds:cmd_steamid')
