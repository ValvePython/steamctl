|pypi| |pypipy| |license|

Take control of Steam from your terminal

Install
-------

.. code:: bash

    pip install steamctl

Install directly from ``github``:

.. code:: bash

    pip install git+https://github.com/ValvePython/steamctl#egg=steamctl


Command list
-------------


.. code:: text

    authenticator       Manage Steam authenticators
    |- add                Add authentictor to a Steam account
    |- remove             Remove an authenticator
    |- list               List all authenticators
    |- code               Generate auth code
    \- qrcode             Generate QR code

    depot               List and download from Steam depots
    |- info               View info about a depot(s)
    |- list               List files from depot(s)
    \- download           Download depot files

    hlmaster            Query master server and server information
    |- query              Query HL Master for servers
    \- info               Query info from a goldsrc or source server

    steamid             Parse SteamID representations

    webapi              Access to WebAPI
    |- set-key            Set WebAPI key
    |- clear-key          Remove saved key
    |- list               List all available WebAPI endpoints
    \- call               Call WebAPI endpoint

    workshop            Search and download workshop items
    |- search             Search the workshop
    |- info               Get all details for a workshop item
    \- download           Download a workshop item

Previews
--------

``steamctl authenticator`` (no root required)

.. image:: https://raw.githubusercontent.com/ValvePython/steamctl/master/preview_authenticator.jpg
    :alt: preview: steamctl authenticator

``steamctl hlmaster``

.. image:: https://asciinema.org/a/253275.png
    :target: https://asciinema.org/a/253275
    :alt: preview: steamctl hlmaster

``steamctl workshop``

.. image:: https://asciinema.org/a/253277.png
    :target: https://asciinema.org/a/253277
    :alt: preview: steamctl workshop


.. |pypi| image:: https://img.shields.io/pypi/v/steamctl.svg?style=flat&label=latest
    :target: https://pypi.org/project/steamctl/
    :alt: Latest version released on PyPi

.. |pypipy| image:: https://img.shields.io/pypi/pyversions/steamctl.svg?label=%20&logo=python&logoColor=white
    :alt: PyPI - Python Version

.. |license| image:: https://img.shields.io/pypi/l/steamctl.svg?style=flat&label=license
    :target: https://pypi.org/project/steamctl/
    :alt: MIT License
