
import logging
import sys
import json
from steam import webapi
from steamctl.utils.storage import UserDataFile, UserCacheFile
from steamctl.utils.web import make_requests_session
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

LOG = logging.getLogger(__name__)

def cmd_webapi_set(args):
    keyfile = UserDataFile('apikey.txt')

    if args.key:
        keyfile.write_text(args.key)

    if keyfile.exists():
        print("Current key:", keyfile.read_text())
    else:
        print("Current key: NOT SET")

def cmd_webapi_clear(args):
    UserDataFile('apikey.txt').remove()

def cmd_webapi_list(args):
    params = {}
    params.setdefault('key', args.apikey or get_webapi_key())

    if args.format !='text':
        params['format'] = 'json' if args.format == 'json_line' else args.format
        params['raw'] = True

    try:
        resp = webapi.get('ISteamWebAPIUtil', 'GetSupportedAPIList', params=params)

        if args.format == 'text':
            interfaces = resp['apilist']['interfaces']
            UserCacheFile('webapi_interfaces.json').write_json(interfaces)
    except Exception as exp:
        LOG.error("GetSupportedAPIList failed: %s", str(exp))
        if getattr(exp, 'response', None):
            LOG.error("Response body: %s", exp.response.text)
        return 1  # error

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
    # load key=value pairs. Stuff thats start with [ is a list, so parse as json
    try:
        params = {k: (json.loads(v) if v[0:1] == '[' else v) for k, v in args.params}
    except Exception as exp:
        LOG.error("Error parsing params: %s", str(exp))
        return 1  # error

    apicall = webapi.get
    version = args.version or 1

    if args.method == 'POST':
        apicall = webapi.post

    webapi_map = {}

    # load cache webapi_interfaces if available
    for interface in (UserCacheFile('webapi_interfaces.json').read_json() or {}):
        for method in interface['methods']:
            key = "{}.{}".format(interface['name'], method['name'])

            if key not in webapi_map or webapi_map[key][1] < method['version']:
                webapi_map[key] = method['httpmethod'], method['version']

    # if --method or --version are unset, take them the cache
    # This will the call POST if needed with specifying explicity
    # This will prever the highest version of a method
    if args.endpoint in webapi_map:
        if args.method is None:
            if webapi_map[args.endpoint][0] == 'POST':
                apicall = webapi.post
        if args.version is None:
            version = webapi_map[args.endpoint][1]

    # drop reserved words. these have special meaning for steam.webapi
    for reserved in ('key', 'format', 'raw', 'http_timeout', 'apihost', 'https'):
        params.pop(reserved, None)

    # load key if available
    params.setdefault('key', args.apikey or get_webapi_key())

    if args.format !='text':
        params['format'] = 'json' if args.format == 'json_line' else args.format
        params['raw'] = True

    try:
        interface, method = args.endpoint.split('.', 1)
        resp = apicall(interface, method, version,  params=params)
    except Exception as exp:
        LOG.error("%s failed: %s", args.endpoint, str(exp))
        if getattr(exp, 'response', None):
            LOG.error("Response body: %s", exp.response.text)
        return 1  # error

    # by default we print json, other formats are shown as returned from api
    if args.format == 'json':
        json.dump(json.loads(resp.rstrip('\n\t\x00 ')), sys.stdout, indent=4, sort_keys=True)
        print('')
    else:
        print(resp)
