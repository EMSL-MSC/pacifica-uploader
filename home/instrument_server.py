"""
Configuration specific to an instrument
"""

import json
import psutil

import os

from home import file_tools

from home import task_comm


class UploaderConfiguration(object):
    """
    meta data about for a session
    """

    initialized = False

    instrument = ''

    policy_server = ''
    ingest_server = ''
    target_dir = ''
    data_dir = ''
    timeout = 30

    # free disk space
    free_space = 0
    free_size_str = ''

    @staticmethod
    def set_if_there(config, key, obj, attr, err_list):
        """ assigns config values """
        if key in config:
            setattr(obj, attr, config[key])
        else:
            err_list.append('Missing ' + key)

    def initialize_settings(self):
        """
        if the system hasn't been initialized, do so
        """
        err_list = []

        if not self.initialized:  # first time through, initialize

            configuration = read_config_file()

            self.set_if_there(configuration, 'target', self, 'target_dir', err_list)

            if not os.path.isdir(self.target_dir):
                err_list.append('target directory unmounted')

            self.set_if_there(configuration, 'policyServer', self, 'policy_server', err_list)

            self.set_if_there(configuration, 'ingestServer', self, 'ingest_server', err_list)

            self.set_if_there(configuration, 'timeout', self, 'timeout', err_list)

            if 'use_celery' in configuration:
                task_comm.USE_CELERY = (configuration['use_celery'] == 'True')
            else:
                task_comm.USE_CELERY = True

            self.set_if_there(configuration, 'dataRoot', self, 'data_dir', err_list)

            self.data_dir = os.path.normpath(self.data_dir)

            if self.data_dir.endswith("\\"):
                self.data_dir = self.data_dir[:-1]

            if not os.path.isdir(self.data_dir):
                err_list.append('root directory unmounted')

        err_str = json.dumps(err_list)

        return err_str


    def update_free_space(self):
        """
        update the amount of free space currently available
        this should go in file_tools
        """
        # get the disk usage
        space = psutil.disk_usage(self.target_dir)

        # give ourselves a cushion for other processes
        self.free_space = int(.9 * space.free)

        self.free_size_str = file_tools.size_string(self.free_space)


def read_config_file():
    """
    read the configuration file
    """
    config_file = 'UploaderConfig.json'

    with open(config_file, 'r') as config:
        configuration = json.load(config)

    return configuration
