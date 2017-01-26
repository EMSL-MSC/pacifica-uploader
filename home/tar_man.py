"""
manages the tar directory to keep it from overflowing
"""

import os
import time
import json


def job_list_from_dir(directory):
    """
    gets a list of jobs based on the files in the tar directory
    """
    dir_files = os.listdir(directory)
    jobs = []

    for fpath in dir_files:
        if '_uploaded.tar' in fpath:
            job = fpath.replace('_uploaded.tar', '')
            jobs.append(job.encode('utf-8'))

    return jobs


def remove_tar_file(directory, job_id):
    """
    remove a tar file from the tar directory based on job id
    """
    fname = str(job_id) + '_uploaded.tar'

    full_path = os.path.join(directory, fname)

    # remove from directory
    if os.path.isfile(full_path):
        os.remove(full_path)


def rename_tar_file(directory, old_name, job_id):
    """
    rename tar files with a job id so that we can start tracking status in the archive
    """
    new_name = str(job_id) + '_uploaded.tar'
    new_name = os.path.join(directory, new_name)

    print old_name
    print new_name

    if os.path.isfile(old_name):
        os.rename(old_name, new_name)

# pylint: disable=unused-argument
def job_status(job_list=None):
    """
    checks the status of existing job
    tbd
    """
    return []
# pylint: enable=unused-argument


def remove_orphans(directory):
    """
    gets rid of turds left by cancelled uploads
    """
    dir_files = os.listdir(directory)

    # compare the files to the contents of the directory
    for fpath in dir_files:
        # if a file is in the directory but not uploaded, remove it if it is out of date
        # kludge in place to remove things that never progress in the database
        # if not '_uploaded.tar' in fpath:
        full_path = os.path.join(directory, fpath)
        # remove from directory
        if os.path.isfile(full_path):
            timestamp = os.path.getmtime(full_path)
            current = time.time()
            if current - timestamp > 86400:  # a day in seconds
                os.remove(full_path)


def clean_target_directory(target_dir=''):
    """
    deletes local files that have made it to the archive
    """

    # remove old files that were not uploaded
    remove_orphans(target_dir)

    # get job list from file
    jobs = job_list_from_dir(target_dir)

    if not jobs:
        return

    # get jobs state from database
    jobs_state = job_status(job_list=jobs)

    if not jobs_state:
        return

    info = json.loads(jobs_state)

    for job in jobs:
        try:
            job_state = info[job]
            if job_state is not None:
                state_index = job_state['state']
                val = int(state_index)
                if val > 4:
                    remove_tar_file(target_dir, job)
        # pylint: disable=broad-except
        except Exception:
            remove_tar_file(target_dir, job)
        # pylint: enable=broad-except
