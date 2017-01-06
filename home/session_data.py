# pylint: disable=too-many-return-statements
# justification: argument with style

"""
maintains the state of a user session
"""

import os
import time

from home.file_tools import FileManager


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
        """
        resets time out
        """
        self.last_touched_time = time.time()

    def is_timed_out(self):
        """
        returns whether the session is timed out
        """
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
        """
        explicitly sets the root data dir
        """
        self.files.data_dir = filepath

    def restore_session_root(self):
        """
        restores the original root data dir
        """
        self.files.data_dir = self.config.data_dir

    def cleanup_session(self):
        """
        resets a session to a clean state
        """
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
        """

        newlist = sorted(meta.meta_list, key=lambda x: x.directory_order)

        nodes = []
        for node in newlist:
            if node.directory_order is not None:
                display = meta.get_display(node)
                nodes.append(display)

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
                    "data": ""}
            children.append(node)
            children = node['children']
            lastnode = node

            # concatenate the archive path
            archive_path = os.path.join(archive_path, node_name)

        self.files.archive_path = archive_path

        return tree, lastnode
