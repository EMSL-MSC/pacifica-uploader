#operating system and platform
import os
import platform
import json
import time

class tar_management(object):
    """manages the state of the tar directory"""

    def parse_job(self, url):
        """
        parse job id from status url, ex:
        https://dev2.my.emsl.pnl.gov/myemsl/cgi-bin/status/2000796
        """
        list = url.split('/')
        job_id = list[-1]
        if job_id:
            return job_id
        else:
            return ''

    def remove_tar_file(self, dir, job_id):

        fname = job_id + '_uploaded.tar'

        full_path = os.path.join(dir, fname)

        # remove from directory
        if os.path.isfile(full_path):
            os.remove(full_path)

    def rename_tar_file(self, dir, old_name, job_id):

        new_name = job_id + '_uploaded.tar'
        new_name = os.path.join(dir, new_name)

        print old_name
        print new_name

        if os.path.isfile(old_name):
            os.rename(old_name, new_name)

    def remove_orphans(self, dir):

        dir_files = os.listdir(dir)

        # compare the files to the contents of the directory
        for file in dir_files:
            # if a file is in the directory but not uploaded, remove it if it is out of date
            full_path = os.path.join(dir, file)
            if not '_uploaded.tar' in file:
                # remove from directory
                if os.path.isfile(full_path):
                    timestamp = os.path.getmtime(full_path)
                    current = time.time()
                    if current - timestamp > 86400: # a day in seconds
                        os.remove(full_path)

    def job_list(self, dir):

        dir_files = os.listdir(dir)
        jobs = []

        for file in dir_files:
            if '_uploaded.tar' in file:
                job = file.replace('_uploaded.tar', '')
                jobs.append(job.encode('utf-8'))

        return jobs

    def clean_tar_directory(self, dir, jobs_state):

        try:

            jobs = self.job_list(dir)

            ##jobs_state = '[{?20001066? : {?state_name?:?Received?, ?state?:?1"}},{?20001067? : {?state_name?:?Available?, ?state?:?5"}},{?20001068? : {?state_name?:?Available?, ?state?:?5"}}]'
            info = json.loads(jobs_state)

            for job in jobs:
                try:
                    job_state = info[job]
                    if job_state is not None:
                        state_index = job_state['state']
                        val = int(state_index)
                        if val > 4:
                            self.remove_tar_file(dir, job)
                except Exception:
                    self.remove_tar_file(dir, job)

        except:
            return 'clean tar failed'

    def __init__(self):
        pass
