
import logging

_LOG = logging.getLogger(__name__)

def cmd_steamid(args):
    from steam.steamid import SteamID

    if args.s_input.startswith('http'):
        _LOG.debug("Input is URL. Making online request to resolve SteamID")
        s = SteamID.from_url(args.s_input) or SteamID()
    else:
        s = SteamID(args.s_input)

    lines = [
    "SteamID: {s.as_64}",
    "Account ID: {s.as_32}",
    "Type: {s.type} ({stype})",
    "Universe: {s.universe} ({suniverse})",
    "Instance: {s.instance}",
    "Steam2: {s.as_steam2}",
    "Steam2Legacy: {s.as_steam2_zero}",
    "Steam3: {s.as_steam3}",
    ]

    if s.community_url:
        lines += ["Community URL: {s.community_url}"]

    if s.invite_url:
        lines += ["Invite URL: {s.invite_url}"]

    lines += ["Valid: {is_valid}"]

    print("\n".join(lines).format(s=s,
                                  stype=str(s.type),
                                  suniverse=str(s.universe),
                                  is_valid=str(s.is_valid()),
                                  ))
