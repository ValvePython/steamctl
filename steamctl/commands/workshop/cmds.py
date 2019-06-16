
import os
import logging
from io import open
from tqdm import tqdm
from steam import webapi
from steam.enums import EResult
from steamctl.utils.storage import ensure_dir, sanitizerelpath
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import print_table, fmt_size
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

_LOG = logging.getLogger(__name__)

def cmd_workshop_search(args):
    apikey = args.apikey or get_webapi_key()

    if not apikey:
        _LOG.error("WebAPI is required. Set one with: steamctl webapi set-key YOURKEY")
        return 1  #error

    maxpages, _ = divmod(args.numresults, 100)

    rows = []
    names = {}

    for page in range(max(maxpages, 1)):
        params = {
            'key': apikey,
            'search_text': ' '.join(args.search_text),
            'numperpage': min(args.numresults, 100),
            'page': page + 1,
            'return_details': True,
            'return_tags': True,
            'query_type': 9,
            'days': 5,
            }

        if args.appid:
            params['appid'] = args.appid
        if args.tag:
            params['requiredtags'] = args.tag
        if args.match_all_tags:
            params['match_all_tags'] = True

        try:
            results = webapi.get('IPublishedFileService', 'QueryFiles',
                                 params=params,
                                 )['response']['publishedfiledetails']

            users =  webapi.get('ISteamUser', 'GetPlayerSummaries', 2,
                                params={
                                    'key': apikey,
                                    'steamids': ','.join(set((a['creator']
                                                              for a in results
                                                              if (a['result'] == EResult.OK
                                                                  and a['creator'] not in names)
                                                              )))
                                    },
                                )['response']['players']
        except Exception as exp:
            _LOG.error("Query failed: %s", str(exp))
            if getattr(exp, 'response', None):
                _LOG.error("Response body: %s", exp.response.text)
            return 1  # error

        names.update({user['steamid']: user['personaname'].strip() for user in users})

        def make_row(item):
            size = int(item.get('file_size', 0))

            return [
                item['publishedfileid'],
                item['title'].strip(),
                names.get(item['creator'], ''),
                str(item['consumer_appid']),
                item['app_name'],
                '{:,d}'.format(item['views']),
                '{:,d}'.format(item['favorited']),
                fmt_size(size) if size else '',
                'x' if (item.get('file_url') or item.get('hcontent_file')) else ' ',
                ', '.join(map(lambda x: x['tag'], item.get('tags', [])))
                ]

        for item in results:
            if item['result'] == EResult.OK:
                if args.downloable and not (item.get('file_url') or item.get('hcontent_file')):
                    continue
                rows.append(make_row(item))

    print_table(rows,
                ['ID', 'Title', 'Creator', 'AppID', 'App Name', '>Views', '>Favs', '>Size', 'D', 'Tags'],
                )

def cmd_workshop_download(args):
    apikey = args.apikey or get_webapi_key()

    if not apikey:
        _LOG.error("WebAPI is required. Set one with: steamctl webapi set-key YOURKEY")
        return 1  #error

    params = {
        'key': apikey,
        'publishedfileids': [args.id],
        }


    try:
        pubfile = webapi.get('IPublishedFileService', 'GetDetails',
                             params=params,
                             )['response']['publishedfiledetails'][0]
    except Exception as exp:
        _LOG.error("Query failed: %s", str(exp))
        if getattr(exp, 'response', None):
            _LOG.error("Response body: %s", exp.response.text)
        return 1  # error

    if pubfile['result'] != EResult.OK:
        _LOG.error("Error accessing %s: %r", pubfile['publishedfileid'], EResult(pubfile['result']))
        return 1  # error

    if pubfile.get('file_url'):
        return download_via_url(args, pubfile)
    elif pubfile.get('hcontent_file'):
        return download_via_steampipe(args, pubfile)
    else:
        _LOG.error("This workshop file is not downloable")
        return 1


def download_via_url(args, pubfile):
    sess = make_requests_session()
    fstream = sess.get(pubfile['file_url'], stream=True)
    total_size = int(pubfile['file_size'])

    relpath = sanitizerelpath(pubfile['filename'])

    if args.no_directories:
        relpath = os.path.basename(relpath)

    relpath = os.path.join(args.output, relpath)

    filepath = os.path.abspath(relpath)
    ensure_dir(filepath)

    with open(filepath, 'wb') as fp:
        if not args.no_progress:
            pbar = tqdm(total=total_size, unit='B', unit_scale=True)
        else:
            class FakePbar(object):
                def write(self, s):
                    print(s)
                def update(self, n):
                    pass
            pbar = FakePbar()

        pbar.write('Downloading to {} ({})'.format(
            relpath,
            fmt_size(total_size),
            ))

        for chunk in iter(lambda: fstream.raw.read(1024*512), b''):
            fp.write(chunk)
            pbar.update(len(chunk))

def download_via_steampipe(args, pubfile):
    _LOG.error("Not available yet")
    return 1
