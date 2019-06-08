from __future__ import print_function

import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()

import sys
import logging
from steamctl import __appname__
from steamctl.argparser import generate_parser, nested_print_usage
import steamctl.commands.steamid
import steamctl.commands.hlmaster

_LOG = logging.getLogger(__appname__)

def main():
    parser, subparsers = generate_parser()
    args, unknown_args = parser.parse_known_args()

    if args.log_level != 'quiet':
        logging.basicConfig(
            format='[%(levelname)s] %(name)s: %(message)s',
            level=getattr(logging, args.log_level.upper())
            )

    _LOG.debug("Parsed args: %s", vars(args))

    if unknown_args:
        _LOG.debug("Unknown args: %s", unknown_args)
        nested_print_usage(parser, args)
        print("%s: unrecognized arguments: %s" % (parser.prog, ' '.join(unknown_args)), file=sys.stderr)
        sys.exit(1)

    rcode = args._cmd_func(args=args)

    if rcode is not None:
        sys.exit(rcode)

if __name__ == '__main__':
    main()
