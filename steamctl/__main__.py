# PYTHON_ARGCOMPLETE_OK
from __future__ import print_function

import sys
import logging
import pkgutil
import importlib
import argcomplete

import steamctl.commands
from steamctl import __appname__
from steamctl.argparser import generate_parser, nested_print_usage

_LOG = logging.getLogger(__appname__)

def main():
    # setup login config, before loading subparsers
    parser = generate_parser(pre=True)
    args, _ = parser.parse_known_args()

    logging.basicConfig(
        format='[%(levelname)s] %(name)s: %(message)s' if args.log_level == 'debug' else '[%(levelname)s] %(message)s',
        level=100 if args.log_level == 'quiet' else getattr(logging, args.log_level.upper())
        )

    # load subcommands
    for _, modname, ispkg in pkgutil.iter_modules(steamctl.commands.__path__):
        if ispkg:
            try:
                importlib.import_module('steamctl.commands.' + modname)
            except ImportError as exp:
                _LOG.error(str(exp))

    # reload parser, and enable auto completion
    parser = generate_parser()
    argcomplete.autocomplete(parser)
    args, unknown_args = parser.parse_known_args()

    if unknown_args:
        _LOG.debug("Unknown args: %s", unknown_args)
        nested_print_usage(parser, args)
        print("%s: unrecognized arguments: %s" % (parser.prog, ' '.join(unknown_args)), file=sys.stderr)
        sys.exit(1)

    # process subcommand
    cmd_func = args._cmd_func

    # attempt to load submodule where the subcommand is located
    if isinstance(cmd_func, str):
        from importlib import import_module
        subpkg, func = cmd_func.split(':', 1)
        cmd_func = getattr(import_module(subpkg), func)

    _LOG.debug("Parsed args: %s", vars(args))

    # execute subcommand
    if cmd_func:
        try:
            rcode = cmd_func(args=args)
        except KeyboardInterrupt:
            _LOG.debug('Interrupted with KeyboardInterrupt')
            rcode = 1
        except Exception as exp:
            from steam.exceptions import SteamError

            if isinstance(exp, SteamError):
                if args.log_level == 'debug':
                    _LOG.exception(exp)
                else:
                    _LOG.error(str(exp))

                rcode = 1

            # unhandled exceptions
            else:
                raise
    else:
        _LOG.debug('_cmd_func attribute is missing')
        rcode = 1

    # ensure that we always output an appropriet return code
    if rcode is not None:
        sys.exit(rcode)

if __name__ == '__main__':
    main()
