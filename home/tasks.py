
"""
Celery tasks to be run in the background
"""


from __future__ import absolute_import
from celery import shared_task

from uploader import upload
from bundler import bundle

from home import tar_man

import os

import json

from home.task_comm import TaskComm, task_error

CLEAN_TAR = True

def clean_target_directory(target_dir=''):
    """
    deletes local files that have made it to the archive
    """

    # remove old files that were not uploaded
    tar_man.remove_orphans(target_dir)

    # needs to be rewritten
    return 'unimplemented'

    ## get job list from file
    #jobs = tar_man.job_list(target_dir)

    #if not jobs:
    #    return
    ## get jobs state from database
    #jobs_state = job_status(job_list=jobs)

    #if jobs_state:
    #    err_str = tar_man.clean_tar_directory(target_dir, jobs_state)
    #    return err_str
    #else:
    #    return 'unable to fetch job status'


@shared_task
def ping():
    """
    check to see if the celery task process is started.
    """
    print "Pinged!"
    TaskComm.task_state('PING', "Background process is alive")

# tag to show this def as a celery task

# pylint: disable=too-many-arguments
# justification: perfect amount of arguments

# pylint: disable=broad-except
# justification: we want to report and log any error at the highest level

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
    try:
        target_dir = os.path.dirname(bundle_name)
        if not os.path.isdir(target_dir):
            TaskComm.task_state('ERROR', 'Bundle directory does not exist')
            return 'Upload Failed'

        TaskComm.task_state("PROGRESS", "Cleaning previous uploads")

        # clean tar directory
        # if CLEAN_TAR:
        #    err_str = clean_target_directory(target_dir)
        #    if err_str:
        #        TaskComm.task_state('PROGRESS', err_str)

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

        result = upload(bundle_name=bundle_name, ingest_server=ingest_server)

        if not result:
            TaskComm.task_state('FAILURE', "Uploader dieded. We don't know why it did")

        status = json.loads(result)

        if status['state'] != 'OK':
            TaskComm.task_state('FAILURE', result)
            return False

        print "rename"
        tar_man.rename_tar_file(target_dir, bundle_name, status['job_id'])
        TaskComm.task_state('DONE', result)
        return True
    except Exception, ex:
        task_error('tasks: upload_files :' + ex.message)
        return False
