#pylint: disable=too-many-return-statements
# justification: argument with style

"""
maintains the state of a user session
"""

import json
import psutil
import os
import datetime
import time

from home import file_tools
from home.file_tools import FileManager
from home.instrument_server import UploaderConfiguration
from home.QueryMetadata import QueryMetadata

class SessionState(object):
    """
    meta data about for a session
    """
    celery_is_alive = False

    user = ''
    user_full_name = ''
    password = ''

    current_user = None
    current_time = ''

    files = FileManager()
    config = None

    last_touched_time = None

    is_uploading = False
    is_logged_in = False

    # process that handles bundling and uploading
    bundle_process = None

    bundle_filepath = ''

    def __init__(self):
        """
        constructor for session_data class
        """

    def touch(self):
        self.last_touched_time = time.time()

    def is_timed_out(self):

        if self.is_uploading:
            return False

        if not self.last_touched_time:
            return False

        now = time.time()
        elapsed = now - self.last_touched_time

        timeout = self.config.timeout * 60

        if elapsed > timeout:
            return True
        else:
            return False

    def set_session_root(self, filepath):
        self.files.data_dir = filepath

    def restore_session_root(self):
        self.files.data_dir = self.config.data_dir


    def cleanup_session(self):
        """
        resets a session to a clean state
        """
        self.proposal_id = None
        self.proposal_list = []
        self.proposal_users = []
        self.user = ''
        self.password = ''
        self.user_full_name = ''
        self.cleanup_upload()

    def cleanup_upload(self):
        """
        resets a session to a clean state
        """
        self.bundle_process = None
        self.current_time = None
        self.files.cleanup_files()

    def validate_space_available(self):
        """
        check the bundle size agains space available
        """

        self.config.update_free_space()

        if self.files.bundle_size == 0:
            return True
        return self.files.bundle_size < self.config.free_space

    def get_archive_tree(self, meta):
        """
        returns a nested structure that can be used to populate fancytree
        currently empty
        """
        nodes = [
                'Proposal placeholder',
                'instrument placeholder']


        tree = []
        children = tree
        lastnode = {}
        archive_path = ''

        for node_name in nodes:
            node = {"title": node_name,
                    "key": 1,
                    "folder": True,
                    "expanded": True,
                    "children": [],
                    "data":""}
            children.append(node)
            children = node['children']
            lastnode = node

            # concatenate the archive path
            archive_path = os.path.join(archive_path, node_name)

        self.files.archive_path = archive_path

        return tree, lastnode
