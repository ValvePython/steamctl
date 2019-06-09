
import logging
import gevent.socket
from gevent.pool import Pool
from gevent.queue import Queue
from steam import game_servers as gs
gs.socket = gevent.socket


# HELPERS
_LOG = logging.getLogger(__name__)

def parse_host(text):
    host, port = text.split(':', 1)
    return host, int(port)

def get_info_short(host, port):
    shost = host + ':' + str(port)
    try:
        data = gs.a2s_info((host, port), timeout=1)
    except Exception as exp:
        return "{:<21} | Error: {}".format(shost, str(exp))
    else:
        return "{shost:<21} | {name:<63} | {game} | {players:>2}/{max_players:>2} | {map:<20} | {_ping:>4.0f} ms".format(
                    shost=shost,
                    **data,
                    )

def format_duration(seconds):
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if hours and minutes:
        return "{:.0f}h {:.0f}m {:.0f}s".format(hours, minutes, seconds)
    elif minutes:
        return "{:.0f}m {:.0f}s".format(minutes, seconds)
    else:
        return "{:.0f}s".format(seconds)

# COMMANDS

def cmd_hlmaster_query(args):
    task_pool = Pool(40)
    results = Queue()

    def run_query(args):
        try:
            for ip, port in gs.query_master(args.filter, max_servers=args.num_servers):
                if args.ip_only:
                    print("%s:%s" % (ip, port))
                else:
                    results.put(task_pool.spawn(get_info_short, ip, port))
        except Exception as exp:
            _LOG.error("query_master: Error: %s", str(exp))

        results.put(StopIteration)

    task_pool.spawn(run_query, args)

    for result in results:
        print(result.get())

def cmd_hlmaster_info(args):
    host, port = parse_host(args.server)

    flags = [args.info, args.players, args.rules].count(True)

    if args.info or flags == 0:
        if flags > 1:
            print('--- {:-<60}'.format("Server Info "))

        if args.short:
            print(get_info_short(host, port))
        else:
            try:
                data = gs.a2s_info((host, port))
            except Exception as exp:
                print("Error: {}".format(exp))
            else:
                for pair in sorted(data.items()):
                    print("{} = {}".format(*pair))

    if args.players:
        if flags > 1:
            print('--- {:-<60}'.format("Players "))

        try:
            plist = gs.a2s_players((host, port))
        except Exception as exp:
            print("Error: {}".format(exp))
        else:
            pad_name = 30
            pad_score = 0
            pad_duration = 0

            for player in plist:
                pad_name = max(pad_name, len(player['name']))
                pad_score = max(pad_score, len(str(player['score'])))
                pad_duration = max(pad_duration, len(format_duration(player['duration'])))

            for player in plist:
                print("{} | {} | {}".format(
                    player['name'].ljust(pad_name),
                    str(player['score']).rjust(pad_score),
                    format_duration(player['duration']).rjust(pad_duration),
                    ))

    if args.rules:
        if flags > 1:
            print('--- {:-<60}'.format("Rules "))

        try:
            rules = gs.a2s_rules((host, port))
        except Exception as exp:
            print("Error: {}".format(exp))
        else:
            for rule in rules.items():
                print("{} = {}".format(*rule))
