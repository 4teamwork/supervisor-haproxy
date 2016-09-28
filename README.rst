supervisor-haproxy
==================

``supervisor-haproxy`` is a supervisor event listener for notifying HaProxy
when the status of programs change.

By actively notifying HaProxy we can avoid that HaProxy sends requests to
servers which are down or will be down shortly for maintenance.

The event listener listens to supervisors ``PROCESS_STATE`` events and sends
status updates to HaProxy via an admin-level stats socket.


Configuration
-------------

When the egg ``supervisor-haproxy`` is installed, the supervisor event listener
is created as console script ``supervisor-haproxy``.
It needs to be configured in the supervisor configuration and requires the
haproxy stats socket and the program infos in order to work correctly.

The program infos have the form ``supervisorProgram:HaProxyBackend/HaProxyServer``,
for example ``instance2:plone04/plone0402`` and tell the event listener which
program in supervisor is which backend server in haproxy.

First configure a stats socket in the **haproxy config**:

.. code::

   global
       stats socket ipv4@127.0.0.1:8800 level admin

then configure the supervisor haproxy event listener in the **supervisor config**:

.. code:: ini

    [eventlistener:HaProxy]
    command = .../bin/supervisor-haproxy tcp://localhost:8800 instance1:plone01/plone0101 instance2:plone01/plone0102
    events = PROCESS_STATE
    process_name=HaProxy

Example using buildout for configuring supervisor:

.. code:: ini

    [supervisor]
    plugins +=
        supervisor-haproxy
    eventlisteners +=
        HaProxy PROCESS_STATE ${buildout:bin-directory}/supervisor-haproxy [tcp://localhost:8800 instance1:plone01/plone0101 instance2:plone01/plone0102]



Development / Tests
-------------------

The tests can be ran using `tox <https://tox.readthedocs.io/en/latest/>`_.
After installing ``tox`` and cloning the repository with git you can just run the
``tox`` command in the checkout for running the standard tests.

The standard tests do not test the communication with haproxy.
For that you need to setup a haproxy with `docker <https://www.docker.com/>`_:

Running haproxy with docker:

.. code:: bash

    $ cd supervisor-haproxy
    $ ./run-docker

In another terminal you can then run the tests against haproxy:

.. code:: bash

    $ virutalenv .
    $ ./bin/pip install -e .
    $ ./bin/python test_haproxy_control.py



Links
-----

- Github: https://github.com/4teamwork/supervisor-haproxy
- Issues: https://github.com/4teamwork/supervisor-haproxy/issue
- Pypi: http://pypi.python.org/pypi/supervisor-haproxy


Copyright
---------

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``supervisor-haproxy`` is licensed under GNU General Public License, version 2.
