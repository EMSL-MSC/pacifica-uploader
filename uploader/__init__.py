#! /usr/bin/env python
"""
An Uploader module that uses PycURL to transfer data
"""

import os
import sys
import requests
from home.task_comm import task_error, TaskComm
import logging
from django.conf import settings

fmt = getattr(settings, 'LOG_FORMAT', None)
lvl = getattr(settings, 'LOG_LEVEL', logging.DEBUG)

logging.basicConfig(format=fmt, level=lvl)
logging.debug("Logging started on %s for %s" % (logging.root.name, logging.getLevelName(lvl)))


class Uploader(object):
    """Class to send a single bundled file to the Ingest service."""

    fileobj = None
    bundle_name = None
    ingest_server = None
    percent_uploaded = 0
    total_uploaded = 0
    total_size = 0
    auth = {}
    verify = True

    def __init__(self, bundle_name='', ingest_server='', auth={}, verify=True):
        """Constructor for FileIngester class."""
        self.ingest_server = ingest_server
        self.bundle_name = bundle_name
        self.total_size = os.path.getsize(bundle_name)
        self.auth = auth
        self.verify = verify

        TaskComm.set_state("PROGRESS", 'Uploader Initialized')

    def read(self, size):
        """Read wrapper for requests that calculates the hashcode inline."""
        buf = self.fileobj.read(size)

        # running total
        self.total_uploaded += size

        percent = 100.0 * float(self.total_uploaded) / float(self.total_size)
        if percent > 100.0:
            percent = 100.0

        if percent - self.percent_uploaded > 5:
            status = 'upload percent complete: ' + str(int(percent))
            TaskComm.set_state("PROGRESS", status)
            self.percent_uploaded = percent

        return buf

    def upload_bundle(self):
        """Upload a file from inside a tar file."""

        bundle_path = os.path.abspath(self.bundle_name)
        self.fileobj = open(bundle_path, 'rb')
        size_str = str(self.total_size)
        self.fileobj.seek(0)

        # adding unique data string to hopefully avoid cache issues
        #url = self.ingest_server + '/upload?name=' + self.bundle_name
        # dave changed the ingest api, it aint like that 
        url = self.ingest_server + '/upload'

        headers = {}
        headers['Content-Type'] = 'application/octet-stream'
        headers['Content-Length'] = size_str

        TaskComm.set_state("PROGRESS", 'Uploader Request')

        status = requests.post(url, headers=headers, data=self, verify=self.verify, **self.auth)

        TaskComm.set_state("PROGRESS", 'Uploader End Request')

        self.fileobj.close()

        return status.content

def main():
    """
    placeholder
    """

    print >> sys.stderr, "empty main"

if __name__ == '__main__':
    main()
