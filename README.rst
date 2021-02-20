| |pypi| |pypipy| |license|
| |sonar_maintainability| |sonar_reliability| |sonar_security|

steamctl
--------

``steamctl`` is an opensource CLI utility smiliar to ``steamcmd``. It provies access to a number of Steam features and data from the command line. While it is possible to download apps and conntent from Steam, `steamctl` is not a game launcher. 

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

    apps
    |- list             List owned apps
    \- product_info     Show product info about an app

    assistant           Helpful automation
    |- idle-games         Idle up to 32 games for game time
    |- idle-cards         Automatic idling for game cards
    \- discovery-queue    Explore a single discovery queue

    authenticator       Manage Steam authenticators
    |- add                Add authentictor to a Steam account
    |- remove             Remove an authenticator
    |- list               List all authenticators
    |- status             Query Steam Guard status for account
    |- code               Generate auth code
    \- qrcode             Generate QR code

    cloud               Manage Steam Cloud files (e.g. save files, settings, etc)
    |- list               List files for app
    \- download           Download files for app

    depot               List and download from Steam depots
    |- info               View info about a depot(s)
    |- list               List files from depot(s)
    |- download           Download depot files
    \- diff               Compare files between manifest(s) and filesystem

    hlmaster            Query master server and server information
    |- query              Query HL Master for servers
    \- info               Query info from a goldsrc or source server

    steamid             Parse SteamID representations

    ugc                 Info and download of user generated content
    |- info               Get details for UGC
    \- download           Download UGC

    webapi              Access to WebAPI
    |- set-key            Set WebAPI key
    |- clear-key          Remove saved key
    |- list               List all available WebAPI endpoints
    \- call               Call WebAPI endpoint

    workshop            Search and download workshop items
    |- search             Search the workshop
    |- info               Get all details for a workshop item
    |- download           Download a workshop item
    |- subscribe          Subscribe to workshop items
    |- unsubscribe        Unsubscribe to workshop items
    |- favorite           Favourite workshop items
    \- unfavorite         Unfavourite workshop items

Previews
--------

``steamctl authenticator`` (No root required, and transferable token. Steamapp, steamctl, and aegis, with the same token)

.. image:: https://raw.githubusercontent.com/ValvePython/steamctl/master/preview_authenticator.jpg
    :alt: preview: steamctl authenticator

(video) ``steamctl depot``

.. image:: https://asciinema.org/a/323966.png
    :target: https://asciinema.org/a/323966
    :alt: asciinema preview: steamctl depot

(video) ``steamctl workshop``

.. image:: https://asciinema.org/a/253277.png
    :target: https://asciinema.org/a/253277
    :alt: asciinema preview: steamctl workshop

(video) ``steamctl webapi``

.. image:: https://asciinema.org/a/323976.png
    :target: https://asciinema.org/a/323976
    :alt: asciinema preview: steamctl workshop

(video) ``steamctl hlmaster``

.. image:: https://asciinema.org/a/253275.png
    :target: https://asciinema.org/a/253275
    :alt: asciinema preview: steamctl hlmaster



.. |pypi| image:: https://img.shields.io/pypi/v/steamctl.svg?style=flat&label=latest
    :target: https://pypi.org/project/steamctl/
    :alt: Latest version released on PyPi

.. |pypipy| image:: https://img.shields.io/pypi/pyversions/steamctl.svg?label=%20&logo=python&logoColor=white
    :alt: PyPI - Python Version

.. |license| image:: https://img.shields.io/pypi/l/steamctl.svg?style=flat&label=license
    :target: https://pypi.org/project/steamctl/
    :alt: MIT License

.. |sonar_maintainability| image:: https://sonarcloud.io/api/project_badges/measure?project=ValvePython_steamctl&metric=sqale_rating
    :target: https://sonarcloud.io/dashboard?id=ValvePython_steamctl
    :alt: SonarCloud Rating

.. |sonar_reliability| image:: https://sonarcloud.io/api/project_badges/measure?project=ValvePython_steamctl&metric=reliability_rating
    :target: https://sonarcloud.io/dashboard?id=ValvePython_steamctl
    :alt: SonarCloud Rating

.. |sonar_security| image:: https://sonarcloud.io/api/project_badges/measure?project=ValvePython_steamctl&metric=security_rating
    :target: https://sonarcloud.io/dashboard?id=ValvePython_steamctl
    :alt: SonarCloud Rating
