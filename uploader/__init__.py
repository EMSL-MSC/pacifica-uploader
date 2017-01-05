#! /usr/bin/env python
"""
An Uploader module that uses PycURL to transfer data
"""
# pylint: disable=no-member
# justification: because pylint doesn't get pycurl

# pylint: disable=unused-argument
# justification: pycurl callback

import os
import sys
import re
import stat
from optparse import OptionParser
import pycurl
import tempfile
import bundler
from getpass import getpass
from StringIO import StringIO

import requests

from home.Authorization import Authorization

import json

from time import sleep

from home.task_comm import task_error, task_state


def job_status(authorization=None, job_list=None):
    """
    checks the status of existing job
    tbd
    """

    return True


class TrackPercent(object):
    """
    yay, module level global that pylint doesn't bitch about
    used to track percent uploaded
    """
    percent = 0


def progress(_download_t, _download_d, upload_t, upload_d):
    """
    gets the progress of the current pycurl upload
    """
    if upload_t > 0:
        try:
            percent = 100.0 * float(upload_d) / float(upload_t)

            if percent - TrackPercent.percent > 5:
                meta_dict = {
                    'Status': "upload percent complete: " + str(int(percent))}
                task_state("PROGRESS", meta_dict)
                TrackPercent.percent = percent

        except Exception, ex:
            raise task_error('Error during callback: '+ ex.message)


def upload(bundle_name='', ingest_server=''):
    """
    Uploads a bundle of files via cURL to a specified server

    :Parameters:
        bundle_name
            The name of the bundle file to upload.
    """
    status = None

    bundle_path = os.path.abspath(bundle_name)

    files = {'file': (open(bundle_path, 'rb'), 'application/octet-stream')}
    bundle = open(bundle_path, 'rb')
    headers = {'content-type': 'application/octet-stream'}
    url = ingest_server + '/upload'

    status = requests.post(url, headers=headers, data=bundle)

    return status.content


def main():
    """
    placeholder
    """

    print >> sys.stderr, "empty main"

if __name__ == '__main__':
    main()
