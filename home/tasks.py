"""
Celery tasks to be run in the background
"""


from __future__ import absolute_import
from celery import shared_task, current_task
import sys

from bundler import bundle
from uploader import upload
from uploader import job_status

from home import tar_man

import os
import json

def clean_target_directory(target_dir = '', server='', user='', password=''):
    """
    deletes local files that have made it to the archive
    """
    tm = tar_man.tar_management()
    
    # get job list from file
    jobs = tm.job_list()

    if not jobs:
        return

    # fake job list
    #jobs = ['2001066', '2001067','2001068']

    # get jobs state from database
    jobs_state = job_status(protocol="https",
                                    server=server,
                                    user=user,
                                    password=password,
                                    job_list=jobs)

    # fake job state
    #jobs_state = '[{?20001066? : {?state_name?:?Received?, ?state?:?1"}},{?20001067? : {?state_name?:?Available?, ?state?:?5"}},{?20001068? : {?state_name?:?Available?, ?state?:?5"}}]'

    tm.clean_tar_directory(target_dir, jobs_state)


#tag to show this def as a celery task
@shared_task
def upload_files(bundle_name='',
                 instrument_name='',
                 proposal='',
                 file_list=None,
                 bundle_size=1,
                 groups=None,
                 server='',
                 user='',
                 password=''):
    """
    task created on a separate Celery process to bundle and upload in the background
    status and errors are pushed by celery to the main server through RabbitMQ
    """

    #clean tar directory
    target_dir = os.path.dirname(bundle_name)
    clean_target_directory(target_dir, server, user, password)

    # initial state pushed through celery
    current_task.update_state("PROGRESS", meta={'Status': "Starting Bundle/Upload Process"})

    bundle(bundle_name=bundle_name,
           instrument_name=instrument_name,
           proposal=proposal,
           file_list=file_list,
           groups=groups,
           bundle_size=bundle_size)

    current_task.update_state(state="PROGRESS", meta={'Status': "Starting Upload"})

    res = upload(bundle_name=bundle_name,
                 protocol="https",
                 server=server,
                 user=user,
                 password=password)

    if res is None:
        current_task.update_state("FAILURE", \
            meta={'Status': "Uploader dieded. We don't know whyitded"})

    print >> sys.stderr, "upload completed"

    current_task.update_state("PROGRESS", meta={'Status': "Completing Upload Process"})

    if "http" in res:
        print >> sys.stderr, "Status Page: {0}".format(res)
        current_task.update_state(state='SUCCESS', meta={'url': res})
        return res
    else:
        current_task.update_state("FAILURE", meta={'Status': "No URL"})
        return "Upload Failed"
