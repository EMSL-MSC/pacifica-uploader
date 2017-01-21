
"""
Celery tasks to be run in the background
"""


from __future__ import absolute_import
from celery import shared_task

from uploader import Uploader
from bundler import bundle

from home.tar_man import rename_tar_file, clean_target_directory

import os

import json

from home.task_comm import TaskComm, task_error

CLEAN_TAR = True


def job_status(job_list=None):
    """
    checks the status of existing job
    tbd
    """
    job_list = []
    return job_list


# tag to show this def as a celery task
@shared_task
def ping():
    """
    check to see if the celery task process is started.
    """
    print "Pinged!"
    TaskComm.task_state('PING', "Background process is alive")


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
                 tartar=False):
    """
    task created on a separate Celery process to bundle and upload in the background
    status and errors are pushed by celery to the main server through RabbitMQ
    """
    # one big-ass exception handler for upload.
    try:

        target_dir = os.path.dirname(bundle_name)
        if not os.path.isdir(target_dir):
            TaskComm.task_state('ERROR', 'Bundle directory does not exist')
            return 'Upload Failed'

        TaskComm.task_state("PROGRESS", "Cleaning previous uploads")

        # clean tar directory
        #if CLEAN_TAR:
        #   clean_target_directory(target_dir)

        # initial state pushed through celery
        TaskComm.task_state("PROGRESS", "Starting Bundle/Upload Process")

        bundle(bundle_name=bundle_name,
               file_list=file_list,
               meta_list=meta_list,
               bundle_size=bundle_size)

        TaskComm.task_state("PROGRESS", "Completed Bundling")

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

        TaskComm.task_state("PROGRESS", "Starting Upload")

        uploader = Uploader(bundle_name, ingest_server)
        result = uploader.upload_bundle()

        # invalid json returned
        try:
            status = json.loads(result)
        except ValueError, ex:
            task_error(ex.message + ': ' + result)
            return

        try:
            if status['state'] != 'OK':
                task_error(result)
                return
        except KeyError, ex:
            task_error('missing state returned ' + ex.message)

        print "rename"
        rename_tar_file(target_dir, bundle_name, status['job_id'])
        TaskComm.task_state('DONE', result)
        return

    except Exception, ex:
        task_error('tasks: upload_files :' + ex.message)
        return
