#! /usr/bin/env python
"""
A command line module that provides a front end for the uploader
"""

import sys
import stat
import time
import os.path
import tempfile
from glob import glob
from optparse import OptionParser
from getpass import getpass
import datetime

from home import tasks
from home import session_data
from home import instrument_server

def _add_file_cb( option, opt, value, parser ):
    """
    A Callback function for an OptionParser that adds a file into the file list
    
    :Parameters:
        option
        opt
        value
            The filename that was passed to this callback
        parser
            The OptionParser that calls the callback
    """

    # Try to expand the value argument using wildcards.
    if value[:1] != '/':
        value = os.path.abspath( os.path.join( parser.values.work_dir, value ) )
    file_glob = glob( value )
    
    # If the file doesn't exist, or the wildcards don't match any files, the glob will be empty
    if len( file_glob ) == 0:
        parser.error( "File argument resolved to 0 existing files: %s" % value )
                
    # Each entry in the file list is a tuple of the file's absolute path and the relative file name
    files = []
    abspath = os.path.abspath( parser.values.work_dir )
    for file_name in file_glob:
        if file_name[:1] != '/':
            file_name = os.path.abspath( os.path.join( parser.values.work_dir, file_name ) )
        
        files.append( file_name )
    
    # Add the new file names to the parser's file name list
    parser.values.file_list.extend( files )


def add_usage( parser ):
    """
    Adds a custom usage description string for this module to an OptionParser
    """
    parser.set_usage( "usage: %prog [options] [-c DIR1 -f FILE1 -f FILE2 -c DIR2 -f FILE3]..." )

def _parser_add_group(option, opt, value, parser):
    (type, name) = value.split('=',1)
    parser.groups[type] = name

def add_options( parser ):
    """
    Adds custom command line options for this module to an OptionParser
    """
    parser.groups = {}

    # Upload the bundle to the specified server
    parser.add_option( '-s', '--server', type='string', action='store', dest='server',
                       default='ingest.my.emsl.pnl.gov',
                       help="Set the upload server to SERVER", metavar='SERVER' )

    # Set the directory in which to work
    parser.add_option( '-c', '--cwd', type='string', action='store', dest='work_dir', default=os.getcwd(),
                       help="Change the uploader's working directory to DIR", metavar='DIR' )

    # Set the directory in which to bundle
    parser.add_option( '-t', '--tar', type='string', action='store', dest='tar_dir', default=os.getcwd(),
                       help="Set the uploader's tar directory to DIR", metavar='DIR' )

    # Set the instrument to use
    parser.add_option( '-i', '--instrument', type='string', action='store', dest='instrument', default='',
                       help="Set used instrument to INST", metavar='INST' )

    # Set the name of the proposal
    parser.add_option( '-p', '--proposal', type='string', action='store', dest='proposal', default='',
                       help="Set the Proposal number number to PNUM", metavar='PNUM' )

    # Set the group-type/names
    parser.add_option( '-g', '--group', type='string', action='callback', callback=_parser_add_group,
                       help="Make files a member of the specified type=name group", metavar='T=N' )

    # Add a file to the list to be bundled
    parser.add_option( '-f', '--file', type='string', action='callback', callback=_add_file_cb,
                       dest='file_list', default=[],
                       help="Add the file or directory FILE to the list to be bundled", metavar='FILE' )

        # Upload the bundle as user
    parser.add_option( '-u', '--user', type='string', action='store', dest='user', default='',
                       help="Upload as the username USER", metavar='USER' )


def check_options( parser, bundle_name_optional=True ):
    """
    Performs custom option checks for this module given an OptionParser
    """
    current_time = datetime.datetime.now().strftime("%m.%d.%Y.%H.%M.%S")
    parser.values.bundle_name = os.path.join(parser.values.tar_dir, current_time + ".tar")

    parser.values.password = getpass( "Enter Password:" )



def upload_from_options( parser ):
    """
    Upload files based upon command line options supecified in an OptionParser
    """

    # don't clean tar directory
    tasks.CLEAN_TAR = False

    # populate the session so that we are running the same process as the django uploader
    session = session_data.SessionState()

    # get rid of redundant file paths
    filtered = session.files.filter_selected_list(parser.values.file_list)

    session.files.data_dir = parser.values.work_dir
    # add a final separator
    session.files.common_path = os.path.join(parser.values.work_dir, '')

    # build archive path
    configuration = instrument_server.InstrumentConfiguration()
    configuration.instrument_short_name = parser.values.instrument
    session.proposal_id = parser.values.proposal
    session.config = configuration
    session.get_archive_tree()

    # get the file tuples (local name, archive name) to bundle
    tuples = session.files.get_bundle_files(parser.values.file_list)

    tasks.upload_files( bundle_name=parser.values.bundle_name,
                        instrument_name=parser.values.instrument,
                        proposal=parser.values.proposal,
                        file_list=tuples,
                        bundle_size=session.files.bundle_size,
                        groups=parser.groups,
                        server=parser.values.server,
                        user=parser.values.user,
                        password=parser.values.password)


def main():
    try:
        print 'MyEmsl Uploader, Version 1.0.0'

        parser = OptionParser()
        add_usage( parser )
        add_options( parser )
        parser.parse_args()
        check_options( parser )
        upload_from_options( parser )

    except Exception as err:
        print >> sys.stderr, "CLU dieded: %s" % err


if __name__ == '__main__':
    main()
