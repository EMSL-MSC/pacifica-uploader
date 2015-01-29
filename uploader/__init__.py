#! /usr/bin/env python
"""
An Uploader module that uses PycURL to transfer data
"""

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

from Session import Session

from time import sleep

from celery import current_task

class UploaderError(Exception):
    """
    A special exception class especially for the uploader module
    """

    def __init__(self, msg, outage=False):
        """
        Initializes an Uploader_Error

        @param msg: A custom message packaged with the exception
        """
        self.msg = msg
        self.outage = outage

    def __str__(self):
        """
        Produces a string representation of an Uploader_Error
        """
        if self.outage:
            return "Outage: %s" % self.msg

        current_task.update_state(state='FAILURE', meta={'info': self.msg})
        return "Uploader failed: %s" % self.msg

def pycurl_session(protocol='https',
                   server='dev1.my.emsl.pnl.gov',
                   user='',
                   insecure=False,
                   password=':',
                   negotiate=False,
                   verbose=False):
    """
    Uploads a bundle of files via cURL to a specified server

    :Parameters:
        protocol
            The communication protocol
        server
            The server
        user
            The user name on the destination server to use
        insecure
            Use insecure authentication ( don't verify the destination server )
        password
            The password to use for the selected user on the destination server
        negotiate
            Use Kerberos5 negotiation to authenticate
        verbose
            Print lots and lots of status information
    """

    # @todo: get cURL to use protocol as a guide for authentication type
    url = '%s://%s' % (protocol, server)

    if verbose:
        print >> sys.stderr, 'Server URL: %s' % url
        print >> sys.stderr, 'User: %s' % user

    server = ''
    location = ''

    # Set the user name and password for the queries.  Equivalent to --user cli
    # option
    pycurl_userpwd = "%s:%s" % (user, password)

    # Enable basic http authentication
    #pycurl_httpauth = pycurl.HTTPAUTH_ANY
    pycurl_httpauth = pycurl.HTTPAUTH_BASIC

    # Enable Kerberos5 GssNegotiation for authentication.  Equivalent to
    # --negotiate cli option
    # we don't negotiate with terrorists
    #if negotiate:
    #    pycurl_httpauth = pycurl.HTTPAUTH_GSSNEGOTIATE

    # Set SSL verification mode.  If insecure == true, this is equivalent to
    # the --insecure cli option
    #pycurl_ssl_verifypeer = not insecure

    # Set verbose mode in cURL
    pycurl_verbose = verbose

    #cookie_file = tempfile.NamedTemporaryFile()
    #cookie_jar = cookie_file.name

    cookie_file = "cookies.txt"
    cookie_jar = "cookies.txt"

    if os.path.exists(cookie_file):
        print "deleting " + cookie_file
        os.remove(cookie_file)

    if verbose:
        print >> sys.stderr, 'cookie file: %s' % cookie_file
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

    retval = Session()
    retval.curl = curl
    retval.url = url
    retval.server = server
    retval.location = location

    return retval

def user_info(protocol='https',
              server='dev1.my.emsl.pnl.gov',
              user='',
              insecure=False,
              password=':',
              negotiate=False,
              verbose=False):

    session = pycurl_session(protocol, server, user, insecure, password, negotiate, verbose)

    curl = session.curl

    pyurl = session.url + "/myemsl/userinfo"
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
        print reply
        return reply

def test_authorization(protocol='https',
                       server='',
                       user='',
                       insecure=False,
                       password=':',
                       negotiate=False,
                       verbose=False):

    session = pycurl_session(protocol, server, user, insecure, password, negotiate, verbose)

    curl = session.curl

    pyurl = session.url + "/myemsl/testauth"
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
        print reply
        if "ok" in reply:
            print "True"
            return True

    return False

def progress(download_t, download_d, upload_t, upload_d):
    sleep(1)
    print "Total to download", download_t
    print "Total downloaded", download_d
    print "Total to upload", upload_t
    print "Total uploaded", upload_d

def upload(bundle_name='',
           protocol='https',
           server='',
           user='',
           insecure=False,
           password='',
           negotiate=False,
           verbose=False):
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
        insecure
            Use insecure authentication ( don't verify the destination server )
        password
            The password to use for the selected user on the destination server
        negotiate
            Use Kerberos5 negotiation to authenticate the upload
        verbose
            Print lots and lots of status information for the upload

    @note This function assumes a bundle has been created already and is ready to upload
    """
    status = None

    bundle_path = os.path.abspath(bundle_name)
    if not os.path.exists(bundle_path):
        raise UploaderError("The target bundle does not exist:\n    %s" % bundle_path)
        return None

    # @todo: get cURL to use protocol as a guide for authentication type
    url = '%s://%s' % (protocol, server)

    # If user isn't supplied, use the currently logged in user
    #if user == '':
    #    user = os.getlogin()

    if verbose:
        print >> sys.stderr, 'Server URL: %s' % url
        print >> sys.stderr, 'File: %s' % bundle_path
        print >> sys.stderr, 'User: %s' % user

    server = ''
    location = ''

    #gets a session to be used for the entire upload
    session = pycurl_session(protocol, server, user, insecure, password, negotiate, verbose)

    curl = session.curl
    odata = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, odata.write)

    #**************************************************
    # Pre-allocate with cURL
    if verbose:
        print >> sys.stderr, 'Performing cURL preallocation'
    try:
        # Set the URL for the curl query.
        pyurl = url + "/myemsl/cgi-bin/preallocate"
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))

        curl.perform()

        successful
        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code / 100 == 4:
            raise UploaderError("Authentication failed with code %i" % curl_http_code)
            return None
        else:
            odata.seek(0)
            print odata.read()

        if curl_http_code == 503:
            odata.seek(0)
            raise UploaderError(odata.read(), outage=True)
            return None

        # Make sure that cURL was able to get server and location data
        server = re.search(r'Server: ([\w\.-]*)', odata.getvalue()).group(1)
        location = re.search(r'Location: ([\w\./-@]*)', odata.getvalue()).group(1)

    except pycurl.error:
        raise UploaderError("cURL operations failed for preallocation:\n    %s" % curl.errstr())
        return None

    except:
        raise UploaderError("Backend appears to be tits up")
        return None

    if server == '' or location == '':
        raise UploaderError("Got invalid server and/or location information from server")
        return None

    #*********************************************************************

    #************************************************************************
    #Uploading

    # Set the URL with the server data fetched via cURL
    url = '%s://%s' % (protocol, server)

    if verbose:
        print >> sys.stderr, 'Fetched Server: %s' % server
        print >> sys.stderr, 'Fetched Location: %s' % location
        print >> sys.stderr, 'New Server URL: %s' % url

        # Upload bundle with cURL
        print >> sys.stderr, 'Peforming cURL upload of bundle of %s' % bundle_path

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

        #curl.setopt(pycurl.NOPROGRESS, 0)
        #curl.setopt(pycurl.PROGRESSFUNCTION, progress)
        curl.perform()

        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code == 503:
            odata.seek(0)
            raise UploaderError(odata.read(), outage=True)
            return None

    except pycurl.error:
        raise UploaderError("cURL operations failed during upload:\n    %s" % curl.errstr())
        return None

    except IOError:
        raise UploaderError("Couldn't read from bundle file")
        return None

    #************************************************************************

    #************************************************************************
    # Finalize the upload
    if verbose:
        print >> sys.stderr, 'Peforming cURL finalization of upload'

    try:
        #turn off upload
        curl.setopt(pycurl.PUT, 0)
        curl.setopt(pycurl.UPLOAD, 0)

        # Set the URL for the curl query.
        pyurl = url + "/myemsl/cgi-bin/finish" + location
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))
        #curl.setopt( pycurl.URL, url + "/myemsl/cgi-bin/finish" + location )
        curl.perform()

        curl_http_code = curl.getinfo(pycurl.HTTP_CODE)
        if curl_http_code == 503:
            odata.seek(0)
            raise UploaderError(odata.read(), outage=True)
            return None

        print "curl_http_code " + str(curl_http_code)
        print pyurl

        status = re.search(r'Status: (.*)', odata.getvalue()).group(1)
        # Make sure that the upload was accepted
        if re.search(r'Accepted', odata.getvalue()) == None:
            raise UploaderError("Upload was not accepted")
            return None

    except pycurl.error:
        raise UploaderError("cURL operations failed for finalization:\n    %s" % curl.errstr())
        return None
    except:
        raise UploaderError("The Uploader 'as buggered off before finalization:\n")
        return None

    try:
        # Set the URL for the curl query.
        pyurl = url + "/myemsl/logout"
        curl.setopt(pycurl.URL, pyurl.encode('utf-8'))

        curl.perform()



    except pycurl.error:
        raise UploaderError("cURL operations failed for finalization:\n    %s" % curl.errstr())
        return None

    # dfh fix this when tempfile permissions are fixed
    #cookie_file.close()

    #************************************************************************

    return status


def main():
    print >> sys.stderr, "empty main"

if __name__ == '__main__':
    main()
