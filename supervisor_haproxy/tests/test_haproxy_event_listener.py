from freezegun import freeze_time
from StringIO import StringIO
from supervisor_haproxy.event_listener import HaProxyEventListener
from supervisor_haproxy.tests.haproxy_control import HaProxyControlMock
from unittest2 import TestCase


INSTANCE1 = {'supervisor_program': 'instance1',
             'haproxy_backend': 'plone04',
             'haproxy_server': 'plone0401'}

INSTANCE2 = {'supervisor_program': 'instance2',
             'haproxy_backend': 'plone04',
             'haproxy_server': 'plone0402'}


class TestHaProxyEventListener(TestCase):

    def setUp(self):
        self.haproxy_control = HaProxyControlMock()
        self.event_listener = None
        self.maxDiff = None

    @freeze_time('2016-09-14 10:45:30')
    def test_receive_PROCESS_STATE_EXITED(self):
        self.assertEqual(
            {'stdout': 'RESULT 2\nOK',
             'stderr': ('2016-09-14T10:45:30'
                        ' Received PROCESS_STATE_EXITED (from RUNNING)'
                        ' for instance2,'
                        ' sending MAINT for plone04/plone0402.\n')},
            self.run_listener(
                'eventname:PROCESS_STATE_EXITED',
                'expected:1 processname:instance2 groupname:bar'
                ' from_state:RUNNING pid:1',
                programs=[INSTANCE1, INSTANCE2]))
        self.assertEqual(
            [('set_server_status', 'plone04', 'plone0402', 'MAINT')],
            self.haproxy_control.calls)

    def test_receive_PROCESS_STATE_EXITED_for_unwatched_process(self):
        self.assertEqual(
            {'stdout': 'RESULT 2\nOK',
             'stderr': ''},
            self.run_listener(
                'eventname:PROCESS_STATE_EXITED',
                'expected:1 processname:instance2 groupname:bar'
                ' from_state:RUNNING pid:1',
                programs=[INSTANCE1]))
        self.assertEqual([], self.haproxy_control.calls)

    def test_startup_procedure(self):
        def trigger(eventname):
            result = self.run_listener(
                'eventname:{}'.format(eventname),
                'expected:1 processname:instance1 groupname:bar pid:1',
                programs=[INSTANCE1])
            self.assertEqual('RESULT 2\nOK', result['stdout'])

        trigger('PROCESS_STATE_STARTING')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'MAINT')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_BACKOFF')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'MAINT')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_STARTING')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'MAINT')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_RUNNING')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'READY')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_STOPPING')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'DRAIN')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_STOPPED')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'MAINT')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_STARTING')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'MAINT')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_RUNNING')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'READY')],
                         self.haproxy_control.popcalls())

        trigger('PROCESS_STATE_EXITED')
        self.assertEqual([('set_server_status', 'plone04', 'plone0401', 'MAINT')],
                         self.haproxy_control.popcalls())

    @freeze_time('2016-09-14 11:20:30')
    def test_fail_when_haproxy_control_cannot_connect(self):
        self.haproxy_control.refuse_connection = True
        self.assertEqual(
            {'stdout': 'RESULT 4\nFAIL',
             'stderr': ('2016-09-14T11:20:30'
                        ' Received PROCESS_STATE_EXITED (from RUNNING)'
                        ' for instance2,'
                        ' sending MAINT for plone04/plone0402.\n'
                        "ERROR: connection to HaProxy stats socket refused\n")},
            self.run_listener(
                'eventname:PROCESS_STATE_EXITED',
                'expected:1 processname:instance2 groupname:bar'
                ' from_state:RUNNING pid:1',
                programs=[INSTANCE1, INSTANCE2]))
        self.assertEqual([], self.haproxy_control.calls)

    def test_retry_on_failure_then_skip_events(self):
        # When HaProxy is not reachable, events would stack up and generate
        # high load because the events are never resolved.
        # But it could happen that a single connection cannot be established,
        # because of network issues or a restarting service or another reason.

        # In order to avoid high load the event listener returns FAIL for the
        # first few failing events, so that the main supervisor process will
        # requeue them.
        # If all events are failing, the event listener is set into skpping
        # state for some time, where it always returns OK and drops all events,
        # in order to protect from high load.
        self.haproxy_control.refuse_connection = True

        log_receive = (' Received PROCESS_STATE_EXITED (from RUNNING)'
                       ' for instance2,'
                       ' sending MAINT for plone04/plone0402.\n')

        failure = {
            'stdout': 'RESULT 4\nFAIL',
            'stderr': (log_receive +
                       'ERROR: connection to HaProxy stats socket refused\n')}

        skip_start = {
            'stdout': 'RESULT 2\nOK',
            'stderr': (log_receive +
                       'WARNING: too many connections were refused, therefore'
                       ' this and all future events will be skipped unhandled'
                       ' for the next 60 seconds.\n')}

        skip_continue = {
            'stdout': 'RESULT 2\nOK',
            'stderr': (log_receive +
                       'WARNING: skipping event handling because too many'
                       ' connections were refused previously.\n')}

        failure_resume = {
            'stdout': 'RESULT 4\nFAIL',
            'stderr': (log_receive +
                       'WARNING: resuming event handling.\n'
                       'ERROR: connection to HaProxy stats socket refused\n')}

        def run_listener():
            result = self.run_listener(
                'eventname:PROCESS_STATE_EXITED',
                'expected:1 processname:instance2 groupname:bar'
                ' from_state:RUNNING pid:1',
                programs=[INSTANCE1, INSTANCE2])
            # remove timestamp so that assertions get easier
            result['stderr'] = result['stderr'][19:]
            return result

        with freeze_time('2016-01-01 01:00:00'):
            self.assertEqual(failure, run_listener())
            self.assertEqual(failure, run_listener())
            self.assertEqual(failure, run_listener())
            self.assertEqual(failure, run_listener())
            # after 4 failures skip events for one minute ..
            self.assertEqual(skip_start, run_listener())
            self.assertEqual(skip_continue, run_listener())

        # .. then start trying to connect again
        with freeze_time('2016-01-01 01:01:01'):
            self.assertEqual(failure_resume, run_listener())
            self.assertEqual(failure, run_listener())
            self.assertEqual(failure, run_listener())
            self.assertEqual(failure, run_listener())
            self.assertEqual(skip_start, run_listener())
            self.assertEqual(skip_continue, run_listener())

    def test_ignore_TICK_60_event(self):
        self.assertEqual(
            {'stdout': 'RESULT 2\nOK',
             'stderr': ''},
            self.run_listener(
                'eventname:TICK_60',
                'when:1201063880'))
        self.assertEqual([], self.haproxy_control.calls)

    def run_listener(self, header, body, programs=None):
        if self.event_listener is None:
            self.event_listener = HaProxyEventListener(
                programs or [],
                haproxy_control=self.haproxy_control)

        header = '{} len:{}\n'.format(header, len(body))
        self.event_listener.stdin = StringIO(header + body)
        self.event_listener.stdout = StringIO()
        self.event_listener.stderr = StringIO()
        self.event_listener.runforever(test=True)
        self.event_listener.stdout.seek(0)
        self.event_listener.stderr.seek(0)

        self.assertEquals('READY\n', self.event_listener.stdout.read(6))
        return {'stdout': self.event_listener.stdout.read(),
                'stderr': self.event_listener.stderr.read()}
