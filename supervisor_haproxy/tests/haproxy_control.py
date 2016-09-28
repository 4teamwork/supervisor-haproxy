from supervisor_haproxy.haproxy_control import STATUS_DRAIN
from supervisor_haproxy.haproxy_control import STATUS_MAINT
from supervisor_haproxy.haproxy_control import STATUS_READY
import socket


class HaProxyControlMock(object):

    def __init__(self):
        self.calls = []
        self.refuse_connection = False

    def popcalls(self):
        calls = self.calls[:]
        self.calls[:] = []
        return calls

    def get_server_status(self, backend, server_name):
        raise NotImplementedError()

    def set_server_status(self, backend, server_name, state):
        if self.refuse_connection:
            raise socket.error(61, 'Connection refused')

        valid_states = (STATUS_READY, STATUS_DRAIN, STATUS_MAINT)
        if state not in valid_states:
            raise ValueError('State must be one of {!r}, got {!r}'.format(
                valid_states, state))

        return self.calls.append(
            ('set_server_status', backend, server_name, state))
