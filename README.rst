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


Command list
-------------


.. code:: text

        authenticator       Manage Steam authenticators
        hlmaster            Query master server and server information
        steamid             Parse SteamID representations
        webapi              Access to WebAPI
        workshop            Search and download workshop items

Previews
--------

``steamctl hlmaster``

.. image:: https://asciinema.org/a/253275.png
    :target: https://asciinema.org/a/253275
    :alt: preview: steamctl hlmaster

``steamctl workshop``

.. image:: https://asciinema.org/a/253277.png
    :target: https://asciinema.org/a/253277
    :alt: preview: steamctl workshop
    
    
 
.. |pypi| image:: https://img.shields.io/pypi/v/steamctl.svg?style=flat&label=stable
    :target: https://pypi.org/project/steamctl/
    :alt: Latest version released on PyPi

.. |license| image:: https://img.shields.io/pypi/l/steamctl.svg?style=flat&label=license
    :target: https://pypi.org/project/steamctl/
    :alt: MIT License
