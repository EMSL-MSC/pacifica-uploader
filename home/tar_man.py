import json
import datetime

#operating system and platform
import os
import platform

class tar_management(object):
    """manages the state of the tar directory"""

    def write_tar_state(self, dict = None):
        """
        writes the tar state from a dictionary to Json file
        """
        fname = 'tar_state.JSON'
        with open(fname, 'wb') as outfile:
            json.dump(dict, outfile)


    def read_tar_state(self):
        """
        reads the tar state file into a dictionary
        """
        # if file does not exist, return an empty dictionary
        fname = 'tar_state.JSON'
        dict = {}

        if not os.path.isfile(fname):
            return dict
        else:
            with open(fname) as infile:
                dict = json.load(infile)

        return dict

    def parse_job(self, url):
        """
        parse job id from status url, ex:
        https://dev1.my.emsl.pnl.gov/myemsl/cgi-bin/status/2000796
        """
        list = url.split('/')
        job_id = list[-1]
        if (job_id):
            return job_id
        else:
            return ''


    def add_tar(self, file = '', job = ''):
        # read the state file
        dict = self.read_tar_state()

        # add the new record
        dict[job] = file

        #write the state file
        self.write_tar_state(dict)

    def remove_tar_file(self, job_id):
        # read the state file
        dict = self.read_tar_state()

        if not dict[job_id]:
            return

        fname = dict[job_id]

        # remove from directory
        if (os.path.isfile(fname)):
            os.remove(fname)

        #remove from dictionary
        del dict[job_id]

        #write the state file
        self.write_tar_state(dict)

    def remove_orphans(self):
        # read the state file
        dict = self.read_tar_state()
        if not dict:
            return

        job_files = dict.values()
        if not job_files:
            return

        path = job_files[0]
        if not path:
            return

        dir = os.path.dirname(path)
        dir_files = os.listdir(dir)

        # compare the files to the contents of the directory
        for file in dir_files:
            # if a file is in the directory but not the tar state, remove it
            full_path = os.path.join (dir, file)
            if not full_path in job_files:
                # remove from directory
                if (os.path.isfile(full_path)):
                    os.remove(full_path)

    def job_list(self):
        # read the state
        dict = self.read_tar_state()

        jobs = dict.viewkeys()
        job_list = []
        for job in jobs:
            job_list.append (job.encode('utf-8'))

        return job_list

    def clean_tar_directory(self, tar_dir, jobs_state):
        
        try:
            # read the state
            dict = self.read_tar_state()

            ##jobs_state = '[{?20001066? : {?state_name?:?Received?, ?state?:?1"}},{?20001067? : {?state_name?:?Available?, ?state?:?5"}},{?20001068? : {?state_name?:?Available?, ?state?:?5"}}]'
            info = json.loads(jobs_state)

            jobs = dict.keys()
            for job in jobs:
                try:
                    job_state = info[job]
                    if job_state is not None:
                        state_index = job_state['state']
                        val = int(state_index)
                        if val > 4:
                            self.remove_tar_file(job)
                except Exception:
                    self.remove_tar_file(job)

            self.remove_orphans()
        except:
            return 'clean tar failed'

    def __init__(self):
        pass
