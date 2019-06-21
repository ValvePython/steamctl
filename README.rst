|pypi| |license|

Take control of Steam from your terminal

Requires Python ``3.4+``.

Install
-------

.. code:: bash

    pip install steamctl

Install directly from ``github``:

.. code:: bash

    pip install git+https://github.com/ValvePython/steamctl#egg=steamctl


Help print
----------


.. code:: text

    $ steamctl --help
    usage: steamctl [-h] [--version] [-l {quiet,info,debug}] <command> ...

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      -l {quiet,info,debug}, --log_level {quiet,info,debug}
                            Set logging level

    List of commands:

      <command>
        authenticator       Manage Steam authenticators
        hlmaster            Query master server and server information
        steamid             Parse SteamID representations
        webapi              Access to WebAPI
        workshop            Search and download workshop items

    Tab Completion

        Additional steps are needed to activate bash tab completion.
        See https://argcomplete.readthedocs.io/en/latest/#global-completion

        To enable globally run:
            activate-global-python-argcomplete

        To enable for the current session run:
            eval "$(register-python-argcomplete steamctl)"

        The above code can be added to .bashrc to persist between sessions for the user.


.. |pypi| image:: https://img.shields.io/pypi/v/steamctl.svg?style=flat&label=stable
    :target: https://pypi.org/project/steamctl/
    :alt: Latest version released on PyPi

.. |license| image:: https://img.shields.io/pypi/l/steamctl.svg?style=flat&label=license
    :target: https://pypi.org/project/steamctl/
    :alt: MIT License
