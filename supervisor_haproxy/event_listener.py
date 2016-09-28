from datetime import datetime
from supervisor import childutils
from supervisor_haproxy.haproxy_control import HaProxyControl
from supervisor_haproxy.haproxy_control import STATUS_DRAIN
from supervisor_haproxy.haproxy_control import STATUS_MAINT
from supervisor_haproxy.haproxy_control import STATUS_READY
import sys


class HaProxyEventListener(object):

    STATE_ACTIONS = {
        'PROCESS_STATE_STARTING': STATUS_MAINT,
        'PROCESS_STATE_RUNNING': STATUS_READY,
        'PROCESS_STATE_BACKOFF': STATUS_MAINT,
        'PROCESS_STATE_STOPPING': STATUS_DRAIN,
        'PROCESS_STATE_EXITED': STATUS_MAINT,
        'PROCESS_STATE_STOPPED':STATUS_MAINT,
        'PROCESS_STATE_FATAL': STATUS_MAINT,
        'PROCESS_STATE_UNKNOWN': STATUS_MAINT,
    }

    def __init__(self, programs, haproxy_socket=None, haproxy_control=None):
        self.haproxy_control = haproxy_control or HaProxyControl(haproxy_socket)
        self.programs = {program['supervisor_program']: program
                         for program in programs}
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.running = False

    def runforever(self, test=False):
        while True:
            self.handle(*childutils.listener.wait(self.stdin, self.stdout))
            if test:
                return

    def handle(self, headers, payload):
        event = headers.get('eventname')
        action = self.STATE_ACTIONS.get(event, None)
        if action is None:
            # Event is not supported.
            return self.ok()

        data = childutils.get_headers(payload)
        program_info = self.programs.get(data.get('processname'), None)
        if program_info is None:
            # We are not watching this program.
            return self.ok()

        self.log('{date} Received {event} (from {from_state})'
                 ' for {supervisor_program},'
                 ' sending {action} for '
                 '{haproxy_backend}/{haproxy_server}.\n'.format(
                     date=datetime.now().isoformat(),
                     event=event,
                     from_state=data.get('from_state', '?'),
                     action=action,
                     **program_info))

        try:
            self.haproxy_control.set_server_status(
                program_info['haproxy_backend'],
                program_info['haproxy_server'],
                action)
        except Exception, exc:
            self.log('ERROR: {!r}'.format(exc))
            return self.fail()

        return self.ok()

    def ok(self):
        childutils.listener.ok(self.stdout)

    def fail(self):
        childutils.listener.fail(self.stdout)

    def log(self, msg):
        self.stderr.write(msg.rstrip('\n') + '\n')
