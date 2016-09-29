from supervisor_haproxy.haproxy_control import HaProxyControl
from supervisor_haproxy.haproxy_control import STATUS_DRAIN
from supervisor_haproxy.haproxy_control import STATUS_MAINT
from supervisor_haproxy.haproxy_control import STATUS_READY
from supervisor_haproxy.haproxy_control import STATUS_UP
import unittest


class TestHaProxyControl(unittest.TestCase):
    """This test requires an actual haproxy server, configured with
    the config in docs/haproxy.cfg.
    It makes sure that the HaProxyControl actually does the job.
    """

    def setUp(self):
        self.control = HaProxyControl('tcp://127.0.0.1:9902')
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def cleanup(self):
        if self.control.get_server_status('A', 'A1') != STATUS_UP:
            self.control.set_server_status('A', 'A1', STATUS_READY)

    def test_set_to_drain(self):
        self.assertEqual(STATUS_UP, self.control.get_server_status('A', 'A1'))
        self.control.set_server_status('A', 'A1', STATUS_DRAIN)
        self.assertEqual(STATUS_DRAIN, self.control.get_server_status('A', 'A1'))

    def test_set_to_maint(self):
        self.assertEqual(STATUS_UP, self.control.get_server_status('A', 'A1'))
        self.control.set_server_status('A', 'A1', STATUS_MAINT)
        self.assertEqual(STATUS_MAINT, self.control.get_server_status('A', 'A1'))

    def test_set_to_ready(self):
        self.control.set_server_status('A', 'A1', STATUS_MAINT)
        self.assertEqual(STATUS_MAINT, self.control.get_server_status('A', 'A1'))
        self.control.set_server_status('A', 'A1', STATUS_READY)
        self.assertEqual(STATUS_UP, self.control.get_server_status('A', 'A1'))


if __name__ == '__main__':
    unittest.main()
