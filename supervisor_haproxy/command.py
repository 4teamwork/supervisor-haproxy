from supervisor_haproxy.event_listener import HaProxyEventListener
import argparse
import re


def socket(value):
    if not re.match(r'^tcp://[^:]+:\d+$', value):
        raise argparse.ArgumentTypeError(
            'Invalid socket {!r}, must be of form "tcp://127.0.0.1:9902"'.format(
                value))
    return value


def program_info(value):
    match = re.match(r'^([^:]+):([^/]+)/(.*)$', value)
    if not match:
        raise argparse.ArgumentTypeError(
            'Invalid program {!r}. Must be of form'
            ' "supervisorProgram:HaProxyBackend/HaProxyServer",'
            ' e.g. "instance2:plone04/plone0402"'.format(value))

    return dict(zip(('supervisor_program', 'haproxy_backend', 'haproxy_server'),
                    match.groups()))


def main():
    parser = argparse.ArgumentParser(
        description=('Supervisor event listener for updating HaProxy'
                     ' servers on supervisor program status changes.'),
        epilog=('>> %(prog)s tcp://localhost:8800 instance1:plone04/plone0401'))

    parser.add_argument(
        'haproxy_socket',
        metavar='SOCKET',
        type=socket,
        help=(u'The haproxy stats socket (required).'
              u' Only TCP sockets (AF_INET) are supported at the moment, e.g.:'
              u' tcp://localhost:8800'))

    parser.add_argument(
        'programs',
        type=program_info,
        metavar='PROGRAMS',
        nargs='+',
        help=(u'Mapping of the supervisor programs to the haproxy'
              ' backend and server configuration.'
              ' Multiple programs may be configured at once.'
              ' Must be of form "supervisorProgram:HaProxyBackend/HaProxyServer",'
              ' e.g. "instance2:plone04/plone0402"'))

    args = parser.parse_args()
    HaProxyEventListener(**vars(args)).runforever()
