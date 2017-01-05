# pylint: disable=too-many-return-statements
# justification: argument with style

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
    run_without_celery = True

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

    def initialize_settings(self):
        """
        if the system hasn't been initialized, do so
        """
        try:
            if not self.initialized:  # first time through, initialize

                configuration = read_config_file()

                self.target_dir = configuration['target']
                if self.target_dir == '':
                    return 'Configuration: Missing target directory'

                if not os.path.isdir(self.target_dir):
                    return 'Configuration: target directory unmounted'

                self.policy_server = configuration['policyServer']
                if self.policy_server == '':
                    return 'Configuration: Missing policy server path'

                self.ingest_server = configuration['ingestServer']
                if self.ingest_server == '':
                    return 'Configuration: Missing ingest server path'

                self.timeout = int(configuration['timeout'])
                if self.timeout == '':
                    return 'Configuration: Missing timeout'

                try:
                    use_celery = configuration['use_celery']
                    task_comm.USE_CELERY = (use_celery == 'True')
                except Exception:
                    task_comm.USE_CELERY = True

                root_dir = os.path.normpath(configuration['dataRoot'])
                if root_dir == '':
                    return 'Configuration: Missing root directory'

                if root_dir.endswith("\\"):
                    root_dir = root_dir[:-1]

                if not os.path.isdir(root_dir):
                    return 'Configuration: root directory unmounted'

                self.data_dir = root_dir

            else:
                return ''
        except Exception, err:
            print err
            return 'Configuration Error'

        return ''

    def update_free_space(self):
        """
        update the amount of free space currently available
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
