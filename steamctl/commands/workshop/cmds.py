import json
import logging
from steam import webapi
from steam.enums import EResult
from steamctl.utils.web import make_requests_session
from steamctl.utils.format import print_table, fmt_size
from steamctl.commands.webapi import get_webapi_key

webapi._make_requests_session = make_requests_session

_LOG = logging.getLogger(__name__)


def check_apikey(args):
    apikey = args.apikey or get_webapi_key()

    if not apikey:
        _LOG.error("No WebAPI key set. See: steamctl webapi -h")
        return 1  #error

    return apikey


def cmd_workshop_search(args):
    apikey = check_apikey(args)

    maxpages, _ = divmod(args.numresults, 100)
    firstpage = True

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
                                 )['response'].get('publishedfiledetails', [])

            if not results:
                if firstpage:
                    _LOG.error("No results found")
                    return 1  # error
                else:
                    break

            firstpage = False

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

def cmd_workshop_info(args):
    apikey = check_apikey(args)

    params = {
        'key': apikey,
        'publishedfileids': [args.id],
        'includetags': 1,
        'includeadditionalpreviews': 1,
        'includechildren': 1,
        'includekvtags': 1,
        'includevotes': 1,
        'includeforsaledata': 1,
        'includemetadata': 1,
        'return_playtime_stats': 1,
        'strip_description_bbcode': 1,
        }

    try:
        result = webapi.get('IPublishedFileService', 'GetDetails',
                             params=params,
                             )['response']['publishedfiledetails'][0]
    except Exception as exp:
        _LOG.error("Query failed: %s", str(exp))
        if getattr(exp, 'response', None):
            _LOG.error("Response body: %s", exp.response.text)
        return 1  # error

    if result['result'] != EResult.OK:
        _LOG.error("Query result: %r", EResult(result['result']))
        return 1 # error

    print(json.dumps(result, indent=2))


def webapi_sub_helper(args, cmd):
    apikey = check_apikey(args)

    subscribe = not cmd.startswith('un')

    if cmd.endswith('subscribe'):
        list_type = 1
    elif cmd.endswith('favorite'):
        list_type = 2

    try:
        workshop_items = webapi.get('IPublishedFileService', 'GetDetails',
                                    params={
                                        'key': apikey,
                                        'publishedfileids': list(set(args.workshop_ids)),
                                        'includetags': 0,
                                        'includeadditionalpreviews': 0,
                                        'includechildren': 0,
                                        'includekvtags': 0,
                                        'includevotes': 0,
                                        'includeforsaledata': 0,
                                        'includemetadata': 0,
                                        'return_playtime_stats': 0,
                                        'strip_description_bbcode': 0,
                                    },
                                    )['response']['publishedfiledetails']
    except Exception as exp:
        _LOG.debug("webapi request failed: %s", str(exp))
        _LOG.error("Failed fetching workshop details")
        return 1 # error


    has_error = False

    for item in workshop_items:
        title = item['title']
        workshop_id = item['publishedfileid']

        if item['result'] != EResult.OK:
            _LOG.error("Error for %s: %s", workshop_id, EResult(item['result']))
            continue

        try:
            result = webapi.post('IPublishedFileService', 'Subscribe' if subscribe else "Unsubscribe",
                                 params={
                                    'key': apikey,
                                    'publishedfileid': workshop_id,
                                    'list_type': list_type,
                                    'notify_client': 1,
                                 },
                                 )
        except Exception as exp:
            _LOG.debug("webapi request failed: %s", str(exp))
            _LOG.error("%s failed for %s - %s", cmd.capitalize(), workshop_id, title)
            has_error = True
        else:
            _LOG.info("%sd %s - %s", cmd.capitalize(), workshop_id, title)

    if has_error:
        return 1 # error

def cmd_workshop_subscribe(args):
    return webapi_sub_helper(args, 'subscribe')

def cmd_workshop_unsubscribe(args):
    return webapi_sub_helper(args, 'unsubscribe')

def cmd_workshop_favorite(args):
    return webapi_sub_helper(args, 'favorite')

def cmd_workshop_unfavorite(args):
    return webapi_sub_helper(args, 'unfavorite')
