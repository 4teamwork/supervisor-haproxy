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
        self.maxDiff = None
        self.haproxy_control.refuse_connection = True
        self.assertEqual(
            {'stdout': 'RESULT 4\nFAIL',
             'stderr': ('2016-09-14T11:20:30'
                        ' Received PROCESS_STATE_EXITED (from RUNNING)'
                        ' for instance2,'
                        ' sending MAINT for plone04/plone0402.\n'
                        "ERROR: error(61, 'Connection refused')\n")},
            self.run_listener(
                'eventname:PROCESS_STATE_EXITED',
                'expected:1 processname:instance2 groupname:bar'
                ' from_state:RUNNING pid:1',
                programs=[INSTANCE1, INSTANCE2]))
        self.assertEqual([], self.haproxy_control.calls)

    def test_ignore_TICK_60_event(self):
        self.assertEqual(
            {'stdout': 'RESULT 2\nOK',
             'stderr': ''},
            self.run_listener(
                'eventname:TICK_60',
                'when:1201063880'))
        self.assertEqual([], self.haproxy_control.calls)

    def run_listener(self, header, body, programs=None):
        listener = HaProxyEventListener(programs or [],
                                        haproxy_control=self.haproxy_control)

        header = '{} len:{}\n'.format(header, len(body))
        listener.stdin = StringIO(header + body)
        listener.stdout = StringIO()
        listener.stderr = StringIO()
        listener.runforever(test=True)
        listener.stdout.seek(0)
        listener.stderr.seek(0)

        self.assertEquals('READY\n', listener.stdout.read(6))
        return {'stdout': listener.stdout.read(),
                'stderr': listener.stderr.read()}
