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
import json
import traceback

from home import tasks
from home import session_data
from home import instrument_server
from home import QueryMetadata
from home import task_comm
from home import tar_man

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

    # specify a path to the directory containing the configuration file
    # if this path is not specified, the uploader will look in the drive where the process is run from
    parser.add_option('-l', '--configdir', type='string', action='store',
                      dest='config_dir', default='',
                      help='Change the path to the configuration file to CONFIG', metavar='CONFIG')

    # Set the directory in which to work
    parser.add_option('-w', '--workdir', type='string', action='store',
                      dest='work_dir', default='',
                      help='Change the uploader working directory to DIR', metavar='DIR')

    # Set the directory in which to bundle
    parser.add_option('-t', '--tar', type='string', action='store', dest='tar_dir', default='',
                      help='Set the uploader tar directory to DIR', metavar='DIR')

    # Create a tar file with the bundler, then wrap that tar file in a second
    # tar file for upload
    parser.add_option('-r', '--tartar', type='string', action='store',
                      dest='tartar', default='False',
                      help='Upload the file list as a single tar file', metavar='TARTAR')

    # Set the instrument to use
    parser.add_option('-i', '--instrument', type='string', action='store',
                      dest='instrument', default='',
                      help='Set used instrument to INST', metavar='INST')

    # Set the name of the proposal
    parser.add_option('-p', '--proposal', type='string', action='store',
                      dest='proposal', default='',
                      help='Set the Proposal number number to PNUM', metavar='PNUM')

    # Add a file to the list to be bundled
    parser.add_option('-f', '--file', type='string', action='callback',
                      callback=_add_file_cb,
                      dest='file_list', default=[],
                      help='Add the file FILE to the list to be bundled', metavar='FILE')

    # Add a file to the list to be bundled
    parser.add_option('-d', '--directory', type='string', action='callback',
                      callback=_add_directory,
                      dest='file_list', default=[],
                      help='Add the file or directory FILE to the list to be bundled',
                      metavar='DIRECTORY')

    # Upload the bundle as user
    parser.add_option('-u', '--user', type='string', action='store',
                      dest='user', default='',
                      help='Upload as the username USER', metavar='USER')

    # User of Record (person the upload is done for)
    parser.add_option('-o', '--userOfRecord', type='string', action='store',
                      dest='userOfRecord', default='',
                      help='Upload as the user of record name USEROR', metavar='USEROR')

    # "auth": {"cert": ["auth/intermediate/certs/d3e889.cert.pem",
    #                   "auth/intermediate/private/d3e889-nopassword.key.pem"
    # ]},

    # auth cert
    parser.add_option('-c', '--cert', type='string', action='store',
                      dest='certification', default='',
                      help='authorization certification AC', metavar='AC')

    # auth key
    parser.add_option('-k', '--key', type='string', action='store',
                      dest='auth_key', default='',
                      help='authorization key AK', metavar='AK')

    # verify auth
    parser.add_option('-v', '--verify', type='string', action='store',
                      dest='verify', default='True',
                      help='verify V', metavar='V')


def check_options(parser, config, metadata):
    """
    Performs custom option checks for this module given an OptionParser
    """

    if parser.values.tar_dir == 'NONE':
        parser.values.tar_dir = parser.values.work_dir

    auth = '{\"cert\": []}'

    if os.path.isfile(parser.values.certification) and os.path.isfile(parser.values.auth_key):

        auth = '{\"cert\":  [\"%s\", \"%s\"]}' % (parser.values.certification, parser.values.auth_key)

    config.auth = json.loads(auth)
    metadata.auth = json.loads(auth)

    verify = 'True'
    if parser.values.verify == 'True':
        verify = True
    elif parser.values.verify == 'False':
        verify = False
    else:  # must be a filename
        verify = parser.values.verify
        if not os.path.isfile(verify):
            raise (Exception('verify path not found:  ' + verify))

    parser.values.verify = verify
    config.verify = verify
    metadata.verify = verify

    current_time = datetime.datetime.now().strftime("%m.%d.%Y.%H.%M.%S")
    parser.values.bundle_name = os.path.join(
        parser.values.tar_dir, current_time + ".tar")


def get_user_id(metadata, node, network_id):
    try:
        node.value = network_id
        query = metadata.build_query(node)
        print query
        users = metadata.get_list(query)
        element = users[0]
        id = element['_id']
        node.value = id
    except Exception, err:
        print 'failed to get Pacifica id for network id ' + network_id
        raise (err)

    return True


def upload_from_options(parser):
    """
    Upload files based upon command line options supecified in an OptionParser
    """
    configdir = parser.values.config_dir

    # defaults for missing command line args
    configuration = instrument_server.UploaderConfiguration()
    configuration.initialize_settings(configdir)

    # populate metadata.  Command line arguments override hard-coded config file arguments
    metadata = QueryMetadata.QueryMetadata(configuration.policy_server)
    metadata.load_meta(configdir)

    check_options(parser, configuration, metadata)

    # don't clean tar directory
    tar_man.CLEAN_TAR = False

    # typically the user of record is picked from a list based on proposal
    # here, we fetch a specific user from the User table
    node = metadata.get_node('EmslUserOfRecord')
    if parser.values.userOfRecord == '':
        network_user = node.value
    else:
        network_user = parser.values.userOfRecord

    user_record = metadata.get_Pacifica_user(network_user)
    node.value = user_record['person_id']

    node = metadata.get_node('logon')
    if parser.values.user == '':
        network_user = node.value
    else:
        network_user = parser.values.user

    user_record = metadata.get_Pacifica_user(network_user)
    node.value = user_record['person_id']

    node = metadata.get_node('instrumentByID')
    if parser.values.instrument == '':
        parser.values.instrument = node.value
    else:
        node.value = parser.values.instrument

    node = metadata.get_node('ProposalByInstrument')
    if parser.values.proposal == '':
        parser.values.proposal = node.value
    else:
        node.value = parser.values.proposal

    # populate so that we are running the same process as the
    # django uploader

    file_manager = file_tools.FileManager()

    # get rid of redundant file paths
    files = file_manager.filter_selected_list(parser.values.file_list)

    file_manager.data_dir = parser.values.work_dir
    if file_manager.data_dir == '':
        file_manager.data_dir = configuration.data_dir

    # add a final separator
    file_manager.common_path = os.path.join(parser.values.work_dir, '')

    tartar = False
    if parser.values.tartar == 'True':
        tartar = True

    # get the file tuples (local name, archive name) to bundle
    tuples = file_manager.get_bundle_files(files)

    meta_list = metadata.create_meta_upload_list()

    # let the task know to simply update and print the state
    task_comm.TaskComm.USE_CELERY = False

    # pylint: disable=unexpected-keyword-arg
    tasks.upload_files(ingest_server=configuration.ingest_server,
                       bundle_name=parser.values.bundle_name,
                       file_list=tuples,
                       bundle_size=file_manager.bundle_size,
                       meta_list=meta_list,
                       auth=configuration.auth,
                       verify=parser.values.verify,
                       tartar=tartar)
    # pylint: enable=unexpected-keyword-arg


def main():
    """
    uploads files from the command line
    """
    try:
        print 'MyEmsl Uploader, Version 1.0.1'

        parser = OptionParser()
        add_usage(parser)
        add_options(parser)
        parser.parse_args()
        upload_from_options(parser)
    # pylint: disable=broad-except

        state, info = task_comm.TaskComm.get_state()
        print '%s:  %s' % (state, info)

    except Exception as err:
        print >> sys.stderr, 'Command Line Uploader error: %s: %s' % (err, traceback.format_exc())
    # pylint: enable=broad-except


if __name__ == '__main__':
    main()
