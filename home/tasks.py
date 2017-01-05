"""
Celery tasks to be run in the background
"""


from __future__ import absolute_import
from celery import shared_task

from uploader import upload
from uploader import job_status

from bundler import bundle

from home import tar_man

import os

import json

from home.task_comm import task_error, task_state

CLEAN_TAR = True


def clean_target_directory(target_dir=''):
    """
    deletes local files that have made it to the archive
    """

    # remove old files that were not uploaded
    tar_man.remove_orphans(target_dir)

    # get job list from file
    jobs = tar_man.job_list(target_dir)

    if not jobs:
        return

    # fake job list
    #jobs = ['2001066', '2001067','2001068']

    # get jobs state from database
    jobs_state = job_status(job_list=jobs)

    # fake job state
    # jobs_state = '[{?20001066? : {?state_name?:?Received?, ?state?:?1"}},
    #            {?20001067? : {?state_name?:?Available?, ?state?:?5"}},
    #            {?20001068? : {?state_name?:?Available?, ?state?:?5"}}]'
    if jobs_state:
        err_str = tar_man.clean_tar_directory(target_dir, jobs_state)
        return err_str
    else:
        return 'unable to fetch job status'


@shared_task
def ping():
    """
    check to see if the celery task process is started.
    """
    print "Pinged!"
    task_state('PING', "Background process is alive")

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

    target_dir = os.path.dirname(bundle_name)
    if not os.path.isdir(target_dir):
        task_state('ERROR', 'Bundle directory does not exist')
        return 'Upload Failed'

    task_state("PROGRESS", "Cleaning previous uploads")

    # clean tar directory
    # if CLEAN_TAR:
    #    err_str = clean_target_directory(target_dir)
    #    if err_str:
    #        task_state('PROGRESS', err_str)

    # initial state pushed through celery
    task_state("PROGRESS", "Starting Bundle/Upload Process")

    bundle(bundle_name=bundle_name,
           file_list=file_list,
           meta_list=meta_list,
           bundle_size=bundle_size)

    task_state("PROGRESS", "Completed Bundling")

    if tartar:
        # create the file tuple list of 1 file
        dir = os.path.dirname(bundle_name)
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

    task_state("PROGRESS", "Starting Upload")

    result = upload(bundle_name=bundle_name, ingest_server=ingest_server)

    if not result:
        task_state('FAILURE', "Uploader dieded. We don't know why it did")

    try:
        status = json.loads(result)
    except Exception, ex:
        task_state('FAILURE', ex.message)
        return 'Upload Failed'

    if status['state'] != 'OK':
        task_state('FAILURE', result)
        return 'Upload Failed'

    try:
        print "rename"
        tar_man.rename_tar_file(target_dir, bundle_name, status['job_id'])
        task_state('DONE', result)
        return result
    except Exception, ex:
        task_state('FAILURE', ex.message +' Unable to rename ' + bundle_name)
        return 'Rename Failed'
