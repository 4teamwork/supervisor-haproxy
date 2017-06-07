from datetime import datetime
from datetime import timedelta
from supervisor import childutils
from supervisor_haproxy.exceptions import HaProxyConnectionRefused
from supervisor_haproxy.haproxy_control import HaProxyControl
from supervisor_haproxy.haproxy_control import STATUS_DRAIN
from supervisor_haproxy.haproxy_control import STATUS_MAINT
from supervisor_haproxy.haproxy_control import STATUS_READY
import sys


MAX_CONSECUTIVE_CONNECTION_REFUSED = 4
SKIP_TIMEOUT_AFTER_CONNECTION_REFUSED = timedelta(seconds=60)


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
        self.consecutive_refused_connections = 0
        self.skip_until = None

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

        if self.skip_until is not None:
            if self.skip_until < datetime.now():
                self.consecutive_refused_connections = 0
                self.skip_until = None
                self.log('WARNING: resuming event handling.')

            else:
                self.log('WARNING: skipping event handling because too many'
                         ' connections were refused previously.')
                return self.ok()

        try:
            self.haproxy_control.set_server_status(
                program_info['haproxy_backend'],
                program_info['haproxy_server'],
                action)

        except HaProxyConnectionRefused, exc:
            self.consecutive_refused_connections += 1
            if MAX_CONSECUTIVE_CONNECTION_REFUSED \
               >= self.consecutive_refused_connections:
                self.log('ERROR: connection to HaProxy stats socket refused')
                return self.fail()

            self.log('WARNING: too many connections were refused,'
                     ' therefore this and all future events will be'
                     ' skipped unhandled for the next {} seconds.'.format(
                         SKIP_TIMEOUT_AFTER_CONNECTION_REFUSED.seconds))
            self.skip_until = datetime.now() \
                              + SKIP_TIMEOUT_AFTER_CONNECTION_REFUSED
            return self.ok()

        except Exception, exc:
            self.log('ERROR: {!r}'.format(exc))
            return self.fail()

        self.consecutive_refused_connections = 0
        return self.ok()

    def ok(self):
        childutils.listener.ok(self.stdout)

    def fail(self):
        childutils.listener.fail(self.stdout)

    def log(self, msg):
        self.stderr.write(msg.rstrip('\n') + '\n')
