#! /usr/bin/env python
"""
An Uploader module that uses PycURL to transfer data
"""
#pylint: disable=no-member
#justification: because pylint doesn't get pycurl

#pylint: disable=unused-argument
#justification: pycurl callback

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

from uploader.PycurlSession import PycurlSession

from time import sleep

from home.task_comm import task_error, task_state


def pycurl_session(protocol='https',
                   server='dev2.my.emsl.pnl.gov',
                   user='',
                   password=':'):
    """
    Uploads a bundle of files via cURL to a specified server

    :Parameters:
        protocol
            The communication protocol
        server
            The server
        user
            The user name on the destination server to use
        password
            The password to use for the selected user on the destination server
    """

    # @todo: get cURL to use protocol as a guide for authentication type
    url = '%s://%s' % (protocol, server)

    print >> sys.stderr, 'Server URL: %s' % url
    print >> sys.stderr, 'User: %s' % user

    server = ''
    location = ''

    # Set the user name and password for the queries.  Equivalent to --user cli
    # option
    pycurl_userpwd = '%s:%s' % (user, password)

    # Enable basic http authentication
    #pycurl_httpauth = pycurl.HTTPAUTH_ANY
    pycurl_httpauth = pycurl.HTTPAUTH_BASIC

    # Set verbose mode in cURL
    pycurl_verbose = True

    # make cookie file specific to user
    cookie_jar = '%s_%s' % (user, 'cookies.txt')

    if os.path.exists(cookie_jar):
        print "deleting " + cookie_jar
        os.remove(cookie_jar)

    print >> sys.stderr, 'cookie jar: %s' % cookie_jar
    print >> sys.stderr, 'Performing cURL preallocation'

    #odata = StringIO()
    odata = sys.stderr

    # Create the PycURL object
    curl = pycurl.Curl()
    curl.setopt(pycurl.WRITEFUNCTION, odata.write)
    curl.setopt(pycurl.USERPWD, pycurl_userpwd.encode('utf-8'))
    curl.setopt(pycurl.HTTPAUTH, pycurl_httpauth)
    """
    curl.setopt( pycurl.SSL_VERIFYPEER, pycurl_ssl_verifypeer )
    curl.setopt( pycurl.SSL_VERIFYHOST, pycurl_ssl_verifypeer )
    """
    curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)

    curl.setopt(pycurl.VERBOSE, pycurl_verbose)
    curl.setopt(pycurl.COOKIEJAR, cookie_jar.encode('utf-8'))
    curl.setopt(pycurl.COOKIEFILE, cookie_jar.encode('utf-8'))
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.UNRESTRICTED_AUTH, 1)

    retval = PycurlSession()
    retval.curl = curl
    retval.url = url
    retval.server = server
    retval.location = location

    return retval

#def xxxget_info(protocol='https',
#             server='dev2.my.emsl.pnl.gov',
#             user='',
#             password=':',
#             info_type='userinfo'):

#    """
#    gets the user info from the EUS database mirror on the backend server
#    """

#    session = pycurl_session(protocol, server, user, password)

#    curl = session.curl

#    pyurl = session.url + '/myemsl/' + info_type
#    curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
#    odata = StringIO()
#    curl.setopt(pycurl.WRITEFUNCTION, odata.write)

#    curl.perform()

#    # Verify that authentication was successful
#    curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
#    if curl_http_code / 100 == 4:
#        return False
#    else:
#        odata.seek(0)
#        reply = odata.read()
#        # print reply
#        return reply


#def xxxtest_authorization(protocol='https',
#                       server='',
#                       user='',
#                       password=':'):

#    """
#    Validates the user as a MyEMSL user
#    """
#    try:
#        session = pycurl_session(protocol, server, user, password)

#        curl = session.curl

#        pyurl = session.url + "/myemsl/testauth"
#        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
#        odata = StringIO()
#        curl.setopt(pycurl.WRITEFUNCTION, odata.write)

#        curl.perform()

#        # Verify that authentication was successful
#        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
#        if curl_http_code / 100 == 4:
#            return 'User or Password is incorrect'
#        else:
#            odata.seek(0)
#            reply = odata.read()
#            print reply
#            if "ok" in reply:
#                return None
#    except pycurl.error:
#        return curl.errstr()
#    except:
#        return "Unknown error during authorization"

def job_status(authorization=None, job_list=[]):

    """
    checks the status of existing job
    """

    curl = authorization.get_auth_token()

    #session = pycurl_session(protocol, server, user, password)

    #curl = session.curl

    ## cookie!!!
    #pyurl = session.url + "/myemsl/testauth"
    #curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
    #odata = StringIO()
    #curl.setopt(pycurl.WRITEFUNCTION, odata.write)

    #curl.perform()

    pyurl = session.url + '/myemsl/status/index.php/status/job_status'
    curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
    odata = StringIO()

    curl.setopt(pycurl.WRITEFUNCTION, odata.write)
    curl.setopt(pycurl.POST, 1)

    data = json.dumps(job_list)
    curl.setopt(pycurl.POSTFIELDS, data)

    curl.perform()

    # Verify that authentication was successful
    curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
    if curl_http_code / 100 == 4:
        return False
    else:
        odata.seek(0)
        reply = odata.read()
        print reply
        return reply

    return ''

class TrackPercent(object):
    """
    yay, module level global that pylint doesn't bitch about
    used to track percent uploaded between Curl callbacks
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
                meta_dict={'Status': "upload percent complete: " + str(int(percent))}
                task_state("PROGRESS", meta_dict)
                TrackPercent.percent = percent

        except Exception, e:
            raise task_error("Error during callback: " + e.message)

def upload(bundle_name='', authorization=None):
    """
    Uploads a bundle of files via cURL to a specified server

    :Parameters:
        bundle_name
            The name of the bundle file to upload.
    """
    status = None

    bundle_path = os.path.abspath(bundle_name)

    files = {'file': (open(bundle_path, 'rb'), 'application/octet-stream')}
    f = open(bundle_path, 'rb')
    headers = {'content-type': 'application/octet-stream'}
    url = 'http://127.0.0.1:8066/upload'

    r = requests.post(url, headers=headers, data=f)

    return status


def main():
    """
    placeholder
    """

    print >> sys.stderr, "empty main"

if __name__ == '__main__':
    main()
