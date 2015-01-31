'''
Created on Oct 30, 2014

@author: D3E889
'''
import pycurl

class Session(object):
    '''
    classdocs
    '''
    curl = None
    url = ''
    server = ''
    location = ''

    def __init__(self):
        '''
        Constructor
        '''
        self.curl = pycurl.Curl()
