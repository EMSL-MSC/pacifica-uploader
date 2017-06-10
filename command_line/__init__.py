#! /usr/bin/env python
"""A command line module that provides a front end for the uploader"""
import sys
import time
import os.path
import tempfile
from glob import glob
from optparse import OptionParser
from getpass import getpass
import datetime
import stat

from home import tasks
from home import session_data
from home import instrument_server
from home import QueryMetadata

from home import file_tools

# pylint: disable=unused-argument
def _parser_add_group(option, opt, value, parser):
    """
    Callback to add a key value pair to metadata
    """
    pass
# pylint: enable=unused-argument

def _add_file_cb(option, opt, value, parser):
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
        value = os.path.abspath(os.path.join(parser.values.work_dir, value))
    file_glob = glob(value)

    # If the file doesn't exist, or the wildcards don't match any files, the
    # glob will be empty
    if len(file_glob) == 0:
        parser.error("File argument resolved to 0 existing files: %s" % value)

    # Each entry in the file list is a tuple of the file's absolute path and
    # the relative file name
    files = []
    for file_name in file_glob:
        if file_name[:1] != '/':
            file_name = os.path.abspath(os.path.join(
                parser.values.work_dir, file_name))

        files.append(file_name)

    # Add the new file names to the parser's file name list
    parser.values.file_list.extend(files)


def _add_directory(option, opt, value, parser):
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

    _add_file_cb(option, opt, value, parser)


def add_usage(parser):
    """
    Adds a custom usage description string for this module to an OptionParser
    """
    parser.set_usage(
        "usage: %prog [options] [-c DIR1 -f FILE1 -f FILE2 -c DIR2 -f FILE3]...")

def add_options(parser):
    """
    Adds custom command line options for this module to an OptionParser
    """

    # Set the directory in which to work
    parser.add_option('-c', '--cwd', type='string', action='store',
                      dest='work_dir', default='',
                      help="Change the uploader's working directory to DIR", metavar='DIR')

    # Set the directory in which to bundle
    parser.add_option('-t', '--tar', type='string', action='store', dest='tar_dir', default='',
                      help="Set the uploader's tar directory to DIR", metavar='DIR')

    # Create a tar file with the bundler, then wrap that tar file in a second
    # tar file for upload
    parser.add_option('-r', '--tartar', type='string', action='store',
                      dest='tartar', default='False',
                      help="Upload the file list as a single tar file", metavar='TARTAR')

    # Set the instrument to use
    parser.add_option('-i', '--instrument', type='string', action='store',
                      dest='instrument', default='',
                      help="Set used instrument to INST", metavar='INST')

    # Set the name of the proposal
    parser.add_option('-p', '--proposal', type='string', action='store',
                      dest='proposal', default='',
                      help="Set the Proposal number number to PNUM", metavar='PNUM')

    # Add a file to the list to be bundled
    parser.add_option('-f', '--file', type='string', action='callback',
                      callback=_add_file_cb,
                      dest='file_list', default=[],
                      help="Add the file FILE to the list to be bundled", metavar='FILE')

    # Add a file to the list to be bundled
    parser.add_option('-d', '--directory', type='string', action='callback',
                      callback=_add_directory,
                      dest='file_list', default=[],
                      help="Add the file or directory FILE to the list to be bundled",
                      metavar='DIRECTORY')

    # Upload the bundle as user
    parser.add_option('-u', '--user', type='string', action='store',
                      dest='user', default='',
                      help="Upload as the username USER", metavar='USER')

    # Upload the bundle as user
    parser.add_option('-o', '--userOfRecord', type='string', action='store',
                      dest='userOfRecord', default='',
                      help="Upload as the user of record name USEROR", metavar='USEROR')


def check_options(parser):
    """
    Performs custom option checks for this module given an OptionParser
    """

    if parser.values.tar_dir == 'NONE':
        parser.values.tar_dir = parser.values.work_dir

    current_time = datetime.datetime.now().strftime("%m.%d.%Y.%H.%M.%S")
    parser.values.bundle_name = os.path.join(
        parser.values.tar_dir, current_time + ".tar")


def upload_from_options(parser):
    """
    Upload files based upon command line options supecified in an OptionParser
    """

    # don't clean tar directory
    tasks.CLEAN_TAR = False

    # populate metadata.  Command line arguments override hard-coded config file arguments
    metadata = QueryMetadata.QueryMetadata(configuration.ingest_server)

    node = metadata.get_node('logon')
    if parser.values.user == '':
        parser.values.user = node.value
    else:
        node.value = parser.values.user

    node = metadata.get_node('EmslUserOfRecord')
    if parser.values.userOfRecord == '':
        parser.values.userOfRecord = node.value
    else:
        node.value = parser.values.user

    node = metadata.get_node('instrument')
    if parser.values.instrument == '':
        parser.values.instrument = node.value
    else:
        node.value = parser.values.instrument

    node = metadata.get_node('ProposalByInstrument')
    if parser.values.proposal == '':
        parser.values.proposal = node.value
    else:
        node.value = parser.values.proposal

    # defaults for missing command line args
     # build archive path
    configuration = instrument_server.UploaderConfiguration()
    configuration.initialize_settings()

    # populate the session so that we are running the same process as the
    # django uploader
    session = session_data.SessionState()
    session.proposal_id = parser.values.proposal
    session.config = configuration
    session.get_archive_tree(None)

    # get rid of redundant file paths
    session.files.filter_selected_list(parser.values.file_list)

    session.files.data_dir = parser.values.work_dir
    if session.files.data_dir == '':
        session.files.data_dir = configuration.data_dir

    # add a final separator
    session.files.common_path = os.path.join(parser.values.work_dir, '')

    tartar = False
    if parser.values.tartar == 'True':
        tartar = True

    # get the file tuples (local name, archive name) to bundle
    tuples = session.files.get_bundle_files(parser.values.file_list)

    # pylint: disable=unexpected-keyword-arg
    tasks.upload_files(ingest_server=configuration.ingest_server,
                 bundle_name=parser.values.bundle_name,
                 file_list=tuples,
                 bundle_size=session.files.bundle_size,
                 meta_list=metadata.meta_list,
                 auth=configuration.auth,
                 tartar=tartar)
    # pylint: enable=unexpected-keyword-arg


def main():
    """
    uploads files from the command line
    """
    try:
        print 'MyEmsl Uploader, Version 1.0.0'

        parser = OptionParser()
        add_usage(parser)
        add_options(parser)
        parser.parse_args()
        check_options(parser)
        upload_from_options(parser)
    # pylint: disable=broad-except
    except Exception as err:
        print >> sys.stderr, "CLU dieded: %s" % err
    # pylint: enable=broad-except


if __name__ == '__main__':
    main()
