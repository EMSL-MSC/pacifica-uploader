#!/bin/bash -xe

sed 's/${BACKEND_PORT_80_TCP_ADDR}/'${BACKEND_PORT_80_TCP_ADDR}'/;'\
's/${BACKEND_PORT_80_TCP_PORT}/'${BACKEND_PORT_80_TCP_PORT}'/;' \
    /etc/nginx/conf.d/mysite.template > /etc/nginx/conf.d/default.conf
nginx -g 'daemon off;'
