
import sys

def versions_report(output=sys.stdout):
    from builtins import print
    from functools import partial

    print = partial(print, file=output)

    # steamctl version
    from steamctl import __version__, __appname__
    print("{}: {}".format(__appname__, __version__))

    # dependecy versions
    print("\nDependencies:")

    import pkg_resources

    installed_pkgs = {pkg.project_name.lower(): pkg.version for pkg in pkg_resources.working_set}

    for dep in [
                'steam',
                'appdirs',
                'argcomplete',
                'tqdm',
                'arrow',
                'pyqrcode',
                'beautifulsoup4',
                'vpk',
                'vdf',
                'gevent-eventemitter',
                'gevent',
                'greenlet',
                'pyyaml',
                'pycryptodomex',
                'protobuf',
                ]:
        print("{:>20}:".format(dep), installed_pkgs.get(dep.lower(), "Not Installed"))

    # python runtime
    print("\nPython runtime:")
    print("          executable:", sys.executable)
    print("             version:", sys.version.replace('\n', ''))
    print("            platform:", sys.platform)

    # system info
    import platform

    print("\nSystem info:")
    print("              system:", platform.system())
    print("             machine:", platform.machine())
    print("             release:", platform.release())
    print("             version:", platform.version())
