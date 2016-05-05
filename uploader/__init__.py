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

def get_info(protocol='https',
             server='dev2.my.emsl.pnl.gov',
             user='',
             password=':',
             info_type='userinfo'):

    """
    gets the user info from the EUS database mirror on the backend server
    """

    session = pycurl_session(protocol, server, user, password)

    curl = session.curl

    pyurl = session.url + '/myemsl/' + info_type
    curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
    odata = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, odata.write)

    curl.perform()

    # Verify that authentication was successful
    curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
    if curl_http_code / 100 == 4:
        return False
    else:
        odata.seek(0)
        reply = odata.read()
        # print reply
        return reply


def test_authorization(protocol='https',
                       server='',
                       user='',
                       password=':'):

    """
    Validates the user as a MyEMSL user
    """
    try:
        session = pycurl_session(protocol, server, user, password)

        curl = session.curl

        pyurl = session.url + "/myemsl/testauth"
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
        odata = StringIO()
        curl.setopt(pycurl.WRITEFUNCTION, odata.write)

        curl.perform()

        # Verify that authentication was successful
        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code / 100 == 4:
            return 'User or Password is incorrect'
        else:
            odata.seek(0)
            reply = odata.read()
            print reply
            if "ok" in reply:
                return None
    except pycurl.error:
        return curl.errstr()
    except:
        return "Unknown error during authorization"

def job_status(protocol='https',
               server='',
               user='',
               password=':',
               job_list=[]):

    """
    Validates the user as a MyEMSL user
    """

    session = pycurl_session(protocol, server, user, password)

    curl = session.curl

    # cookie!!!
    pyurl = session.url + "/myemsl/testauth"
    curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
    odata = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, odata.write)

    curl.perform()

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

def upload(bundle_name='',
           protocol='https',
           server='',
           user='',
           password=''):
    """
    Uploads a bundle of files via cURL to a specified server

    :Parameters:
        bundle_name
            The name of the bundle file to upload.
        protocol
            The communication protocol to use for the upload
        server
            The server to which the bundle should be uploaded
        user
            The user name on the destination server to use for the upload
        password
            The password to use for the selected user on the destination server
    @note This function assumes a bundle has been created already and is ready to upload
    """
    status = None

    bundle_path = os.path.abspath(bundle_name)
    if not os.path.exists(bundle_path):
        raise task_error("The target bundle does not exist:\n    %s" % bundle_path)

    # @todo: get cURL to use protocol as a guide for authentication type
    url = '%s://%s' % (protocol, server)

    print >> sys.stderr, 'Server URL: %s' % url
    print >> sys.stderr, 'File: %s' % bundle_path
    print >> sys.stderr, 'User: %s' % user

    server = ''
    location = ''

    #gets a session to be used for the entire upload
    session = pycurl_session(protocol, server, user, password)

    curl = session.curl
    odata = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, odata.write)

    #**************************************************
    # Pre-allocate with cURL
    task_state('UPLOAD', 'Performing cURL preallocation *status*')

    try:
        # Set the URL for the curl query.
        pyurl = url + "/myemsl/cgi-bin/preallocate"
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))

        curl.perform()
        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code / 100 == 4:
            raise task_error("Authentication failed with code %i" % curl_http_code)
        else:
            odata.seek(0)
            print odata.read()

        print "code"
        print curl_http_code

        if curl_http_code == 503:
            odata.seek(0)
            raise task_error(odata.read(), outage=True)

        # Make sure that cURL was able to get server and location data
        try:
            server = re.search(r'Server: ([\w\.-]*)', odata.getvalue()).group(1)
            location = re.search(r'Location: ([\w\./-@]*)', odata.getvalue()).group(1)
        except:
            odata.seek(0)
            raise task_error("Error on server:  " + odata.read(), outage=True)

        if server == '' or location == '':
            raise task_error("Got invalid server and/or location information from server")

    except pycurl.error:
        raise task_error("cURL operations failed for preallocation:\n    %s" % curl.errstr())

    except Exception, e:
        raise task_error("Error during preallocation: " + e.message)


    #*********************************************************************

    #************************************************************************
    #Uploading

    # Set the URL with the server data fetched via cURL
    url = '%s://%s' % (protocol, server)

    print >> sys.stderr, 'Fetched Server: %s' % server
    print >> sys.stderr, 'Fetched Location: %s' % location
    print >> sys.stderr, 'New Server URL: %s' % url

    # Upload bundle with cURL
    task_state('UPLOAD', 'Peforming cURL upload of bundle of %s' % bundle_path)

    try:
        # Set the URL for the curl query.
        pyurl = url + location
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))

        curl.setopt(pycurl.PUT, 1)
        curl.setopt(pycurl.UPLOAD, 1)

        # Set the input callback function to read from the bundle file
        bundlefd = open(bundle_path, 'rb')
        curl.setopt(pycurl.READFUNCTION, bundlefd.read)

        size = os.lstat(bundle_path)[stat.ST_SIZE]
        curl.setopt(pycurl.INFILESIZE_LARGE, size)

        TrackPercent.percent = 0
        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, progress)
        curl.perform()

        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code == 503:
            odata.seek(0)
            raise task_error(odata.read(), outage=True)

    except pycurl.error:
        raise task_error("cURL operations failed during upload: %s" % curl.errstr())

    except IOError:
        raise task_error("Couldn't read from bundle file")

    #************************************************************************

    #************************************************************************
    # Finalize the upload
    task_state('UPLOAD', 'Peforming cURL finalization of upload')

    try:
        #turn off upload
        curl.setopt(pycurl.PUT, 0)
        curl.setopt(pycurl.UPLOAD, 0)

        # Set the URL for the curl query.
        pyurl = url + "/myemsl/cgi-bin/finish" + location
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))

        print 'calling ' + pyurl

        curl.perform()

        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code == 503:
            odata.seek(0)
            raise task_error(odata.read(), outage=True)

        print "curl_http_code " + str(curl_http_code)

        print  odata.getvalue()

        if re.search(r'Error', odata.getvalue()) is not None:
            raise task_error(odata.getvalue())

        if re.search(r'Accepted', odata.getvalue()) == None:
            raise task_error("Upload was not accepted")

        status = re.search(r'Status: (.*)', odata.getvalue()).group(1)
        print "status " + status

    except pycurl.error:
        raise task_error("cURL operations failed for finalization:\n    %s" % curl.errstr())
    except Exception, err:
        raise task_error('finalization error:  ' + pyurl + ':  ' + err.message)
        #raise task_error("Unknown error during finalization:\n")

    try:
        # Set the URL for the curl query.
        task_state('UPLOAD', 'Logging out')
        pyurl = url + "/myemsl/logout"
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))

        curl.perform()

    except pycurl.error:
        raise task_error("cURL operations failed for logout:\n    %s" % curl.errstr())
    except:
        raise task_error("Unknown error on logout:\n    %s" % curl.errstr())

    #************************************************************************

    return status


def main():
    """
    placeholder
    """

    print >> sys.stderr, "empty main"

if __name__ == '__main__':
    main()
