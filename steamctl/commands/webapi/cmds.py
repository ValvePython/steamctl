
import logging
import sys
import json
from steam import webapi
from steamctl.utils import UserDataFile, UserCacheFile

_LOG = logging.getLogger(__name__)

def cmd_webapi_set(args):
    keyfile = UserDataFile('apikey.txt', 'w')

    if args.key:
        with keyfile as fp:
            fp.write(args.key)

    if keyfile.exists():
        print("Current key:", keyfile.read_full())
    else:
        print("Current key: NOT SET")

def cmd_webapi_clear(args):
    UserDataFile('apikey.txt').remove()

def cmd_webapi_list(args):
    params = {}
    params.setdefault('key', args.apikey if args.apikey else None)

    if args.format !='text':
        params['format'] = 'json' if args.format == 'json_line' else args.format
        params['raw'] = True

    try:
        resp = webapi.get('ISteamWebAPIUtil', 'GetSupportedAPIList', params=params)

        if args.format == 'text':
            interfaces = resp['apilist']['interfaces']
            UserCacheFile('webapi_interfaces.json').write_json(interfaces)
    except Exception as exp:
        _LOG.error("GetSupportedAPIList failed: %s", str(exp))
        if getattr(exp, 'response', None):
            _LOG.error("Response body: %s", exp.response.text)
        return 1

    if args.format != 'text':
        if args.format == 'json':
            json.dump(json.loads(resp), sys.stdout, indent=4, sort_keys=True)
            print('')
        else:
            print(resp)
        return

    for interface in interfaces:
        for method in interface['methods']:
            if args.search:
                if args.search.lower() not in "{}.{}".format(interface['name'], method['name']).lower():
                    continue

            out = "{:>4} {}.{} v{} {}".format(
                method['httpmethod'],
                interface['name'],
                method['name'],
                method['version'],
                ('- ' + method['description']) if 'description' in method else '',
                )

            print(out)

            if args.verbose:
                for param in method.get('parameters', []):
                    name = param['name']
                    if name[-3:] == '[0]':
                        name = name[:-3]

                    print("       {:<10} {}{:<10} {}".format(
                        param['type'],
                        ' ' if param['optional'] else '*',
                        name,
                        ('- ' + param['description']) if 'description' in param else '',
                        ))

                print('')

def cmd_webapi_call(args):
    try:
        params = {k: (json.loads(v) if v[0:1] == '[' else v) for k, v in args.params}
    except Exception as exp:
        _LOG.error("Error parsing params: %s", str(exp))
        return 1

    if args.method == 'GET':
        apicall = webapi.get
    else:
        apicall = webapi.post

    for reserved in ('key', 'format', 'raw', 'http_timeout', 'apihost', 'https'):
        params.pop(reserved, None)

    params.setdefault('key', args.apikey if args.apikey else None)

    if args.format !='text':
        params['format'] = 'json' if args.format == 'json_line' else args.format
        params['raw'] = True

    try:
        resp = apicall(*args.endpoint.split('.', 1), params=params)
    except Exception as exp:
        _LOG.error("%s failed: %s", args.endpoint, str(exp))
        if getattr(exp, 'response', None):
            _LOG.error("Response body: %s", exp.response.text)
        return 1

    if args.format == 'json':
        json.dump(json.loads(resp), sys.stdout, indent=4, sort_keys=True)
        print('')
    else:
        print(resp)
