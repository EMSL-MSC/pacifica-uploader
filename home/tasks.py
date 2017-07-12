"""
Celery tasks to be run in the background
"""
from __future__ import absolute_import
import os
import sys
import traceback
import json

from celery import shared_task
from uploader import Uploader
from bundler import bundle
from home.tar_man import rename_tar_file
from home.task_comm import TaskComm, task_error

CLEAN_TAR = True


def job_status():
    """
    checks the status of existing job
    tbd
    """
    return []


# tag to show this def as a celery task
@shared_task
def ping():
    """
    check to see if the celery task process is started.
    """
    print "Pinged!"
    TaskComm.set_state('PING', "Background process is alive")


# pylint: disable=too-many-arguments
# justification: this is the single point of entry to background processing

# pylint: disable=broad-except
# justification: we want to report and log any error at the highest level


# tag to show this def as a celery task
@shared_task
def upload_files(ingest_server='',
                 bundle_name='',
                 file_list=None,
                 bundle_size=0,
                 meta_list=None,
                 auth=None,
                 tartar=False):
    """
    task created on a separate Celery process to bundle and upload in the background
    status and errors are pushed by celery to the main server through RabbitMQ
    """
    # one big-ass exception handler for upload.
    try:

        target_dir = os.path.dirname(bundle_name)
        if not os.path.isdir(target_dir):
            task_error('Bundle directory does not exist')
            return

        TaskComm.set_state("PROGRESS", "Cleaning previous uploads")

        # clean tar directory
        #if CLEAN_TAR:
        #   clean_target_directory(target_dir)

        # initial state pushed through celery
        TaskComm.set_state("PROGRESS", "Starting Bundle/Upload Process")

        bundle(bundle_name=bundle_name,
               file_list=file_list,               meta_list=meta_list,
               bundle_size=bundle_size)

        TaskComm.set_state("PROGRESS", "Completed Bundling")

        if tartar:
            # create the file tuple list of 1 file
            fname = os.path.basename(bundle_name)

            file_tuples = []
            file_tuples.append((bundle_name, fname))

            bundle_size = os.path.getsize(bundle_name)

            # dual extension indicates tartar
            bundle_name += '.tar'

            bundle(bundle_name=bundle_name,
                   file_list=file_tuples,
                   meta_list=meta_list,
                   bundle_size=bundle_size)

        TaskComm.set_state("PROGRESS", "Starting Uploady: " + str(bundle_name) + ": " + ingest_server + ": " + str(auth))

        uploader = Uploader(bundle_name, ingest_server, auth)

        TaskComm.set_state("PROGRESS", "Uploader Initialized")

        result = uploader.upload_bundle()

        TaskComm.set_state("PROGRESS", "Finished Upload")

        status = json.loads(result)

        TaskComm.set_state("PROGRESS", "Rename Tar File")

        rename_tar_file(target_dir, bundle_name, status['job_id'])

        print status

        if TaskComm.USE_CELERY:
            #set job ID here
            print 'exit with deliberate error'
            print result
            raise StandardError(result)
        else:
            TaskComm.set_state("DONE", result)

    except StandardError, error:
        raise error

    except Exception, ex:
        print >> sys.stderr, "Exception in upload_files:"
        print >> sys.stderr, '-'*60
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, '-'*60

        task_error('tasks: upload_files :' + str(ex.message))
        print 'Task exception: ' + str(ex.message)

        raise ex
