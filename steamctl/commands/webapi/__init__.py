
import sys
from steamctl.argparser import register_command
from steamctl.utils.storage import UserDataFile, UserCacheFile
from argcomplete import warn


def get_webapi_key():
    return UserDataFile('apikey.txt').read_full()

epilog = """\
Steam Web API Key:

    To get a key login with a Steam account and visit https://steamcommunity.com/dev/apikey
    You can save the key and have it applied automatically by running:
        {prog} webapi set-key KEY

    Alternatively, you can provide for one-off calls:
        {prog} webapi call --apikey YOURKEY ISteamNews.GetNewsForApp appid=570 count=1

Examples:

    List all available Web API endpoints:
        {prog} webapi list

    Search for partial of the name:
        {prog} webapi list cmlist

    View endpoint parameters by supplying the --verbose flag:
        {prog} webapi list -v cmlist

    Call an Web API endpoint:
        {prog} webapi call ISteamNews.GetNewsForApp appid=570 count=1
"""

@register_command('webapi', help='Access to WebAPI', epilog=epilog)
def cmd_parser(cp):
    def print_help(*args, **kwargs):
        cp.print_help()

    cp.set_defaults(_cmd_func=print_help)

    sub_cp = cp.add_subparsers(metavar='<subcommand>',
                               dest='subcommand',
                               title='List of sub-commands',
                               description='',
                               )

    scp_key = sub_cp.add_parser("set-key", help="Set WebAPI key")
    scp_key.add_argument('key', nargs='?', type=str, help='WebAPI key to save')
    scp_key.set_defaults(_cmd_func=__name__ + '.cmds:cmd_webapi_set')

    scp_key = sub_cp.add_parser("clear-key", help="Remove saved key")
    scp_key.set_defaults(_cmd_func=__name__ + '.cmds:cmd_webapi_clear')

    scp_list = sub_cp.add_parser("list", help="List all available WebAPI endpoints")
    scp_list.add_argument('--apikey', type=str, help='WebAPI key to use')
    scp_list.add_argument('--format', choices=['text', 'json', 'json_line', 'vdf', 'xml'], default='text', help='Output format')
    scp_list.add_argument('-v' , '--verbose', action='store_true', help='List endpoint parameters')
    scp_list.add_argument('search', nargs='?', type=str, help='Text to search in the endpoint name. Only works with \'text\' format.')
    scp_list.set_defaults(_cmd_func=__name__ + '.cmds:cmd_webapi_list')

    def endpoint_autocomplete(prefix, parsed_args, **kwargs):
        interfaces = UserCacheFile('webapi_interfaces.json').read_json()

        if not interfaces:
            warn("To enable endpoint tab completion run: steamctl webapi list")
            return []

        return ('{}.{}'.format(a['name'], b['name']) for a in interfaces for b in a['methods'])

    def parameter_autocomplete(prefix, parsed_args, **kwargs):
        interfaces = UserCacheFile('webapi_interfaces.json').read_json()

        if not interfaces:
            warn("To enable endpoint tab completion run: steamctl webapi list")
            return []

        parameters = []
        ainterface, amethod = parsed_args.endpoint.split('.', 1)

        for interface in filter(lambda a: a['name'] == ainterface, interfaces):
            for method in filter(lambda b: b['name'] == amethod, interface['methods']):
                for param in method['parameters']:
                    if param['name'][-3:] == '[0]':
                        param['name'] = param['name'][:-3]

                    parameters.append(param['name'] + '=')
                break

        return parameters


    scp_call = sub_cp.add_parser("call", help="Call WebAPI endpoint")
    scp_call.add_argument('--apikey', type=str, help='WebAPI key to use')
    scp_call.add_argument('--format', choices=['json', 'json_line', 'vdf', 'xml'], default='json',
                          help='Output format')
    scp_call.add_argument('--method', choices=['GET', 'POST'], type=str,
                          help='HTTP method to use')
    scp_call.add_argument('--version', type=int,
                          help='Method version')
    scp_call.add_argument('endpoint', type=str,
                          help='WebAPI endpoint name (eg ISteamWebAPIUtil.GetSupportedAPIList)')\
            .completer = endpoint_autocomplete
    scp_call.add_argument('params', metavar='KEY=VAL', nargs='*',
                          type=lambda x: x.split('=', 1), default={},
                          help='param=value pairs to pass to endpoint')\
            .completer = parameter_autocomplete
    scp_call.set_defaults(_cmd_func=__name__ + '.cmds:cmd_webapi_call')
