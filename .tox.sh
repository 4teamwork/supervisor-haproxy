#!/usr/bin/env bash

export HAPROXY_STATS_SOCKET=${PORT1:-9901}

docker build -t supervisor-haproxy/haproxy . || exit 1
container=`docker run -d -p$HAPROXY_STATS_SOCKET:8001 supervisor-haproxy/haproxy` || exit 1

python setup.py test -q
result=$?

docker rm -f $container
exit $1
