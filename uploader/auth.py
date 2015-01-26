'''
Created on Oct 10, 2014

@author: D3E889
'''
#!/usr/bin/python

import pycurl

import StringIO

#url = "https://dev1.my.emsl.pnl.gov/myemsl/cgi-bin/preallocate"
url = "https://dev1.my.emsl.pnl.gov"
username = "d3e889"
password = ""

# Set the user name and password for the queries.  Equivalent to --user cli option
pycurl_userpwd = "%s:%s" % ( username, password )

# Set the URL for the curl query.
pyURL = url + "/myemsl/cgi-bin/preallocate"
pyURL = url + "/myemsl/testauth"

# Enable basic http authentification
pycurl_httpauth = pycurl.HTTPAUTH_ANY

"""
odata = StringIO.StringIO()
curl = pycurl.Curl()

curl.setopt(pycurl.URL, pyURL)
curl.setopt(pycurl.WRITEFUNCTION, odata.write)

# these are optional though helpful
curl.setopt(pycurl.FOLLOWLOCATION, 1)
curl.setopt( pycurl.UNRESTRICTED_AUTH, 1 )
curl.setopt(pycurl.MAXREDIRS, 5)

#dfh added
curl.setopt(pycurl.SSL_VERIFYPEER, 0)   
curl.setopt(pycurl.SSL_VERIFYHOST, 0)

#dfh commented
#c.setopt(pycurl.SSL_VERIFYHOST, 2)
curl.setopt(pycurl.USERPWD, pycurl_userpwd)
curl.setopt(pycurl.HTTPAUTH, pycurl_httpauth)

curl.setopt(pycurl.COOKIEFILE, "cookie.txt")
curl.setopt(pycurl.COOKIEJAR, "cookie.txt")

curl.setopt( pycurl.SSL_VERIFYPEER, False )
curl.setopt( pycurl.VERBOSE, True )

curl.setopt(pycurl.HTTPGET, 1)

curl.perform()
http_code = curl.getinfo(pycurl.HTTP_CODE)
if http_code / 100 != 2:
  print "Bad Stuff Happened"

odata.seek(0)
print odata.read()
"""

try:
    odata = StringIO.StringIO()
    curl = pycurl.Curl()

    curl.setopt(pycurl.URL, pyURL)
    curl.setopt(pycurl.WRITEFUNCTION, odata.write)

    # these are optional though helpful
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt( pycurl.UNRESTRICTED_AUTH, 1 )
    curl.setopt(pycurl.MAXREDIRS, 5)

    #dfh added
    curl.setopt(pycurl.SSL_VERIFYPEER, 0)   
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)

    #dfh commented
    #c.setopt(pycurl.SSL_VERIFYHOST, 2)
    
    curl.setopt(pycurl.USERPWD, pycurl_userpwd)
    curl.setopt(pycurl.HTTPAUTH, pycurl_httpauth)

    curl.setopt(pycurl.COOKIEFILE, "cookie.txt")
    curl.setopt(pycurl.COOKIEJAR, "cookie.txt")

    curl.setopt( pycurl.SSL_VERIFYPEER, False )
    curl.setopt( pycurl.VERBOSE, True )

    curl.setopt(pycurl.HTTPGET, 1)

    curl.perform()
    http_code = curl.getinfo(pycurl.HTTP_CODE)
    if http_code / 100 != 2:
        print "Bad Stuff Happened"

    odata.seek(0)
    print odata.read()

except AttributeError:
    print "Bad Stuff Happened"
