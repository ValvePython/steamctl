
from steamctl import __appname__, __version__
from types import FunctionType
from collections import OrderedDict
import argparse
import argcomplete

epilog = """\
Tab Completion

    Additional steps are needed to activate bash tab completion.
    See https://argcomplete.readthedocs.io/en/latest/#global-completion

    To enable globally run:
        activate-global-python-argcomplete

    To enable for the current session run:
        eval "$(register-python-argcomplete steamctl)"

    The above code can be added to .bashrc to persist between sessions for the user.
    """

_subcommands = OrderedDict()

def register_command(command, **kwargs):
    if isinstance(command, FunctionType):
        raise ValueError("Subcommand name not specified")
    if command in _subcommands:
        raise ValueError("There is already a subcommand registered with name: {}".format(command))

    def func_wrap(func):
        _subcommands[command] = func, kwargs

    return func_wrap

def generate_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
        )
    parser.prog = __appname__

    def print_help(*args, **kwargs):
        parser.print_help()

    parser.add_argument('--version', action='version', version="{} {}".format(__appname__, __version__))
    parser.add_argument('-l', '--log_level', choices=['quiet','info','debug'], default='info', help='Set logging level')
    parser.set_defaults(_cmd_func=print_help)

    subparsers = parser.add_subparsers(
                            metavar='<command>',
                            dest='command',
                            title='List of commands',
                            description='',
                            )

    for subcommand, (func, kwargs) in sorted(_subcommands.items(), key=lambda x: x[0]):
        # lets description and epilog maintain identation
        kwargs.setdefault('formatter_class', argparse.RawDescriptionHelpFormatter)

        if '{prog}' in kwargs.get('epilog', ''):
            kwargs['epilog'] = kwargs['epilog'].format(prog=parser.prog)

        sp = subparsers.add_parser(subcommand, **kwargs)
        func(sp)

    return parser


def nested_print_usage(parser, args):
    parser.print_usage()

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            if getattr(args, action.dest):
                nested_print_usage(action.choices[getattr(args, action.dest)], args)
