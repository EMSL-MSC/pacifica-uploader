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
            
    @note: The file_list is a list of tuples formatted as [ (file_path, file_arcname) ... ]
    """

    # Try to expand the value argument using wildcards.
    if value[:1] != '/':
        value = os.path.abspath( os.path.join( parser.values.work_dir, value ) )
    file_glob = glob( value )
    
    # If the file doesn't exist, or the wildcards don't match any files, the glob will be empty
    if len( file_glob ) == 0:
        parser.error( "File argument resolved to 0 existing files: %s" % value )
                
    # Each entry in the file list is a tuple of the file's absolute path and the relative file name
    file_tuples = []
    abspath = os.path.abspath( parser.values.work_dir )
    for file_name in file_glob:
        if file_name[:1] != '/':
            file_name = os.path.abspath( os.path.join( parser.values.work_dir, file_name ) )
        altname = None
        lap = len( abspath )
        if file_name == abspath:
            altname = ""
        elif file_name[:lap+1] == "%s/" %(abspath):
            altname = file_name[lap+1:]
        file_tuples.append( ( file_name, altname ) )
        logger.debug( "Abspath = %s" %( abspath ) )
        logger.debug( "Adding file %s as %s" %( file_name, altname ) )
                       
    # If the glob has only one entry and an arcname argument was supplied, use it
    if len( file_glob ) == 1 and parser.values.alt_name != None:
        file_tuples[0] = ( file_tuples[0][0], parser.values.alt_name )
        
    # No matter what happens, the alt name is cleared
    parser.values.alt_name = None
    
    # Add the new file names to the parser's file name list
    parser.values.file_list.extend( file_tuples )


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
                       help="Change the bundler's working directory to DIR", metavar='DIR' )

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
    parser.values.bundle_name = os.path.join(parser.values.work_dir, current_time + ".tar")

    parser.values.password = getpass( "Enter Password:" )



def upload_from_options( parser ):
    """
    Upload files based upon command line options supecified in an OptionParser
    """


    tasks.upload_files( bundle_name=parser.values.bundle_name,
                        instrument_name=parser.values.instrument,
                        proposal=parser.values.proposal,
                        file_list=parser.values.file_list,
                        bundle_size=0,
                        groups=parser.values.groups,
                        server=parser.values.server,
                        user=parser.values.user,
                        password=parser.values.password)


def main():
    try:
        parser = OptionParser()
        add_usage( parser )
        add_options( parser )
        parser.parse_args()
        check_options( parser )
        upload_from_options( parser )

    except Exception as err:
        print >> sys.stderr, "CLU dieded: %s" % err.msg


if __name__ == '__main__':
    main()
