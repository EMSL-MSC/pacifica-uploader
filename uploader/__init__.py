#! /usr/bin/env python
"""
An Uploader module that uses PycURL to transfer data
"""

import os
import sys
import requests
from home.task_comm import task_error, TaskComm


class Uploader(object):
    """Class to send a single bundled file to the Ingest service."""

    fileobj = None
    bundle_name = None
    ingest_server = None
    percent_uploaded = 0
    total_uploaded = 0
    total_size = 0


    def __init__(self, bundle_name='', ingest_server=''):
        """Constructor for FileIngester class."""
        self.ingest_server = ingest_server
        self.bundle_name = bundle_name
        self.total_size = os.path.getsize(bundle_name)

    def read(self, size):
        """Read wrapper for requests that calculates the hashcode inline."""
        buf = self.fileobj.read(size)

        # running total
        self.total_uploaded += size

        percent = 100.0 * float(self.total_uploaded) / float(self.total_size)
        if percent > 100.0:
            percent = 100.0

        if percent - self.percent_uploaded > 5:
            status = {
                'Status': "upload percent complete: " + str(int(percent))}
            TaskComm.task_state("PROGRESS", status)
            self.percent_uploaded = percent

        return buf

    def upload_bundle(self):
        """Upload a file from inside a tar file."""

        bundle_path = os.path.abspath(self.bundle_name)
        self.fileobj = open(bundle_path, 'rb')
        size_str = str(self.total_size)
        self.fileobj.seek(0)
        url = self.ingest_server + '/upload'

        headers = {}
        headers['Content-Type'] = 'application/octet-stream'
        headers['Content-Length'] = size_str

        status = requests.post(url, data=self, headers=headers)
        self.fileobj.close()

        return status.content

def job_status(job_list=None):
    """
    checks the status of existing job
    tbd
    """
    job_list = []
    return job_list


def main():
    """
    placeholder
    """

    print >> sys.stderr, "empty main"

if __name__ == '__main__':
    main()
