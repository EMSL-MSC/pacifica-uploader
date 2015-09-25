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

from uploader import get_info

from home import file_tools
from home.file_tools import FileManager
from home.instrument_server import InstrumentConfiguration

class SessionState(object):
    """
    meta data about for a session
    """

    user = ''
    user_full_name = ''
    password = ''

    current_user = None
    current_time = ''

    proposal_friendly = ''
    proposal_id = ''
    proposal_list = []

    proposal_user = ''
    proposal_users = []

    files = FileManager()
    config = None

    last_touched_time = None

    is_uploading = False

    #Todo: mesh the meta lists for session and server
    # meta data values
    meta_list = []

    # process that handles bundling and uploading
    bundle_process = None

    bundle_filepath = ''

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

    def load_proposal(self, proposal):
        """
        split the proposal id from the friendly concatenated string
        to get the currently selected proposal id
        """
        self.proposal_friendly = proposal

        # split the proposal string into ID and description
        split = self.proposal_friendly.split()
        self.proposal_id = split[0]

    def load_proposal_user(self, proposal_user):
        """
        get the selected proposal string from the post
        """
        self.proposal_user = proposal_user

    def populate_user_info(self, configuration):
        """
        parses user information from a json struct
        """

        self.config = configuration

        # get the user's info from EUS
        info = get_info(protocol='https',
                        server=self.config.server_path,
                        user=self.user,
                        password=self.password,
                        info_type='userinfo')

        #with open ('aslipton.json', 'r') as myfile:
        #    info=myfile.read()
        try:
            info = json.loads(info)
        except Exception:
            return 'Unable to parse user information'

        # print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

        first_name = info['first_name']
        if not first_name:
            return 'Unable to parse user name'
        last_name = info['last_name']
        if not last_name:
            return 'Unable to parse user name'

        self.user_full_name = '%s (%s %s)' % (self.user, first_name, last_name)

        instruments = info['instruments']
        if not instruments:
            return 'User is not valid for this instrument'

        try:
            valid_instrument = False
            for inst_id, inst_block in instruments.iteritems():
                if not inst_id:
                    continue
                if not inst_block:
                    continue
                inst_name = inst_block.get('instrument_name')
                if not inst_name:
                    inst_name = 'unnamed'

                instrument_short_name = inst_block.get('name_short')
                if not instrument_short_name:
                    instrument_short_name = 'no short name'

                # ToDo: get this information at the instrument level, not the user level
                if self.config.instrument == inst_id:
                    self.config.instrument_friendly = inst_name
                    self.config.instrument_short_name = instrument_short_name
                    valid_instrument = True
                    break

            if not valid_instrument:
                return 'User is not valid for this instrument'
        except Exception:
            return 'Unable to parse user instruments'

        """
        need to filter proposals based on the existing instrument 
        if there is no valid proposal for the user for this instrument
        throw an error
        """
        props = info['proposals']
        if not props:
            return 'user has no proposals'

        self.proposal_list = []
        for prop_id, prop_block in props.iteritems():

            if not prop_id:
                continue

            if not prop_block:
                continue

            title = prop_block.get('title')
            # if the title is missing we've established that it isn't in the db
            # so skip it
            if not title:
                continue

            prop_str = prop_id + "  " + title

            # list only proposals valid for this instrument
            instruments = prop_block.get('instruments')
            if not instruments:
                continue

            try:
                for inst_id in instruments:
                    if not inst_id:
                        continue
                    if self.config.instrument == str(inst_id):
                        if prop_str not in self.proposal_list:
                            self.proposal_list.append(prop_str)
            except Exception:
                return 'No valid proposals for this user on this instrument'

        if not self.proposal_list:
            return 'No valid proposals for this user on this instrument'

        #self.proposal_list.sort(key=lambda x: int(x.split(' ')[0]), reverse=True)
        self.proposal_list.sort(reverse=True)

        # initialize the proposal to the first in the list
        self.load_proposal(self.proposal_list[0])

        self.populate_proposal_users(self.proposal_id)

    def populate_proposal_users(self, proposal_id):
        """
        parses user for a proposal and instrument from a json struct
        """

        self.proposal_users = []
        json_list = []

        # get the user's info from EUS
        info = get_info(protocol='https',
                        server=self.config.server_path,
                        user=self.user,
                        password=self.password,
                        info_type='proposalinfo/' + proposal_id)

        try:
            info = json.loads(info)
        except Exception:
            return 'Unable to parse proposal user information'

        # print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

        members = info['members']
        # is this an error?
        if not members:
            self.proposal_users.append('No users for this proposal')
            return

        for member in members.iteritems():
            member_id = member[1]
            first_name = member_id['first_name']
            if not first_name:
                first_name = "?"
            last_name = member_id['last_name']
            if not last_name:
                last_name = '?'
            name = first_name + " " + last_name

            self.proposal_users.append(name)

            # put in format to be used by select2
            json_list.append({'id':name, 'text':name})

        return json_list

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

    def get_archive_tree(self):
        """
        returns a nested structure that can be used to populate fancytree
        """
        nodes = ['Proposal ' + self.proposal_id,
                 self.config.instrument_short_name,
                 datetime.datetime.now().strftime("%Y.%m.%d")]

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
