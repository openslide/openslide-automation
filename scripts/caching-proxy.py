#!/usr/bin/python
#
# caching-proxy - Simplistic HTTP proxy that caches in an S3 bucket
#
# Copyright (c) 2014 Benjamin Gilbert
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

import boto
from boto.exception import S3ResponseError
from cStringIO import StringIO
from datetime import datetime, timedelta
import errno
import os
import random
import re
import requests
import socket
import subprocess
import sys
import threading
from wsgiref.simple_server import make_server, WSGIRequestHandler

BUCKET_NAME = 'openslide-build-cache'
BUFSIZE = 5 << 20
UNCACHEABLE_TYPES = set([
    'text/html',
    'text/plain',
    'text/css',
    'text/javascript',
    'application/javascript',
    'application/json',
])
NO_PROXY = (
    '.amazonaws.com',
)

# GC settings
GC_PROBABILITY = 0.05
UPLOAD_GRACE_TIME = timedelta(days=1)
OBJECT_MIN_LIFETIME = timedelta(days=90)
IMMORTAL_OBJECT_RE = re.compile('/openslide-testdata/')


class RequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def key_to_user(key):
    while True:
        buf = key.read(BUFSIZE)
        if not buf:
            break
        yield buf


def request_to_key_and_user(r, upload):
    try:
        for i, buf in enumerate(r.iter_content(BUFSIZE), 1):
            upload.upload_part_from_file(StringIO(buf), i)
            yield buf
    except:
        upload.cancel_upload()
        raise
    else:
        upload.complete_upload()


def proxy_app(environ, start_response):
    # Sanity checks
    if environ['REQUEST_METHOD'] != 'GET':
        start_response('501 Failed', [('Content-Type', 'text/plain')])
        return ["Proxy can't handle request"]

    # Connect to S3
    bucket = boto.connect_s3().get_bucket(BUCKET_NAME, validate=False)

    # Try cache lookup
    url = environ['PATH_INFO']
    query_string = environ.get('QUERY_STRING')
    if query_string:
        url += '?' + query_string
    key = bucket.new_key(url)
    try:
        key.open()
    except S3ResponseError:
        # Failed; start download
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        content_type = r.headers['Content-Type']
        content_length = r.headers['Content-Length']

        # Don't cache HTML/CSS/JavaScript
        if content_type.lower() in UNCACHEABLE_TYPES:
            print 'proxy: Returning uncacheable %s' % url
            start_response('200 OK', [
                ('Content-Type', content_type),
                ('Content-Length', content_length),
            ])
            return r.iter_content(BUFSIZE)

        # Start upload
        headers = {
            'Content-Type': content_type,
        }
        upload = bucket.initiate_multipart_upload(url, headers=headers,
                reduced_redundancy=True)

        # Return to client
        print 'proxy: Returning and caching %s' % url
        start_response('200 OK', [
            ('Content-Type', content_type),
            ('Content-Length', content_length),
        ])
        return request_to_key_and_user(r, upload)
    else:
        # Success; return to client
        print 'proxy: Returning %s from cache' % url
        start_response('200 OK', [
            ('Content-Type', key.content_type),
            ('Content-Length', str(key.size)),
        ])
        return key_to_user(key)


def to_age(stamp):
    stamp = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%S.000Z')
    return datetime.utcnow() - stamp


def cleanup():
    print 'proxy: Performing cleanup'
    bucket = boto.connect_s3().get_bucket(BUCKET_NAME, validate=False)

    # Delete stale multipart uploads
    for upload in bucket.list_multipart_uploads():
        if to_age(upload.initiated) > UPLOAD_GRACE_TIME:
            upload.cancel_upload()

    # Delete all mortal objects older than min lifetime
    delete = []
    for key in bucket.list():
        if IMMORTAL_OBJECT_RE.search(key.name):
            continue
        if to_age(key.last_modified) > OBJECT_MIN_LIFETIME:
            print 'proxy: Deleting %s' % key.name
            delete.append(key)
    if delete:
        bucket.delete_keys(delete)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print 'Usage: %s <command> [args]'
        sys.exit(1)

    while True:
        host = '127.0.0.1'
        port = random.randint(49152, 65535)
        url = 'http://%s:%d/' % (host, port)
        try:
            server = make_server(host, port, proxy_app,
                    handler_class=RequestHandler)
            break
        except socket.error, e:
            if e.errno == errno.EADDRINUSE:
                continue
            else:
                raise

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    env = dict(os.environ)
    no_proxy = os.environ.get('no_proxy') or []
    if no_proxy:
        no_proxy = no_proxy.split(',')
    no_proxy.extend(NO_PROXY)
    env['no_proxy'] = ','.join(no_proxy)
    env['http_proxy'] = url
    env['HTTP_PROXY'] = url
    # HTTPS, FTP not supported
    ret = subprocess.call(sys.argv[1:], env=env, close_fds=True)

    if random.random() < GC_PROBABILITY:
        cleanup()

    sys.exit(ret)
