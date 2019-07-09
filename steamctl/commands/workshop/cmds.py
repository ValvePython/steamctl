import logging
from steam import webapi
from steam.enums import EResult
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import print_table, fmt_size
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

_LOG = logging.getLogger(__name__)

def cmd_workshop_search(args):
    apikey = args.apikey or get_webapi_key()

    if not apikey:
        _LOG.error("No WebAPI key set. See: steamctl webapi -h")
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

            if item.get('file_url'):
                dl = 'URL'
            elif item.get('hcontent_file'):
                dl = 'SP'
            else:
                dl = ''

            return [
                item['publishedfileid'],
                item['title'].strip(),
                names.get(item['creator'], ''),
                str(item['consumer_appid']),
                item['app_name'],
                '{:,d}'.format(item['views']),
                '{:,d}'.format(item['favorited']),
                fmt_size(size) if size else '',
                dl,
                ', '.join(map(lambda x: x['tag'], item.get('tags', [])))
                ]

        for item in results:
            if item['result'] == EResult.OK:
                if args.downloable and not (item.get('file_url') or item.get('hcontent_file')):
                    continue
                rows.append(make_row(item))

    print_table(rows,
                ['ID', 'Title', 'Creator', 'AppID', 'App Name', '>Views', '>Favs', '>Size', 'DL', 'Tags'],
                )
