from contextlib import contextmanager
import csv
import socket


STATUS_DOWN = 'DOWN'
STATUS_DRAIN = 'DRAIN'
STATUS_FAILED = 'FAILED'
STATUS_MAINT = 'MAINT'
STATUS_READY = 'READY'
STATUS_STOPPED = 'STOPPED'
STATUS_UP = 'UP'


class HaProxyControl(object):
    """The purpose of HaProxyControl is to enable and disable haproxy backends as
    well as reporting their status.
    The communication with HaProxy is through a stats socket with admin level.

    Example haproxy configuration:

        global
           stats socket ipv4@0.0.0.0:9902 level admin

    Connect with:

        >>> control = HaProxyControl('tcp://127.0.0.1:9902')
        >>> control.get_server_status('plone01', 'plone0102')
        'UP'

    """

    def __init__(self, haproxy_socket):
        self._sock = None
        if haproxy_socket.startswith('tcp://'):
            self.sock_family = socket.AF_INET
            host, port = haproxy_socket[len('tcp://'):].split(':')
            self.sock_address = host, int(port)
        else:
            raise ValueError('haproxy_socket unsupported {!r}'.format(
                haproxy_socket))

    def get_server_status(self, backend, server_name):
        for line in self.get_stat():
            if line['svname'] == server_name and line['pxname'] == backend:
                return line['status'].split()[0]

    def set_server_status(self, backend, server_name, state):
        valid_states = (STATUS_READY, STATUS_DRAIN, STATUS_MAINT)
        if state not in valid_states:
            raise ValueError('State must be one of {!r}, got {!r}'.format(
                valid_states, state))

        return self.command('set server {}/{} state {}'.format(
            backend, server_name, state.lower()))

    def get_stat(self):
        data = self.command('show stat').lstrip('# ')
        return list(csv.DictReader(data.splitlines()))

    def command(self, cmd):
        with self.connect() as sock:
            sock.send(cmd.rstrip() + '\n')
            return sock.recv(4096)

    @contextmanager
    def connect(self):
        sock = socket.socket(self.sock_family, socket.SOCK_STREAM)
        sock.connect(self.sock_address)
        try:
            yield sock
        finally:
            sock.close()
