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
from home.instrument_server import MetaData
from home.instrument_server import InstrumentConfiguration

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

    # user info in a dictionary, used to refresh lists on user interaction
    user_inf = ''

    proposal_friendly = ''
    proposal_id = ''
    proposal_list = []

    is_analytical = False

    instrument = ''
    instrument_friendly = ''
    instrument_short_name = ''
    instrument_list = []

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

    def load_meta_list(self):
        """
        create a copy of the list of metadata entries to pass to upload page
        this needs to be done on an individual session base so that we can have
        user specific metadata settings
        """
        self.meta_list = []
        for meta in self.config.meta_list:
            meta_entry = MetaData()
            meta_entry.name = meta.name
            meta_entry.label = meta.label
            meta_entry.value = ''
            self.meta_list.append(meta_entry)

    def set_session_root(self, filepath):
        self.files.data_dir = filepath

    def restore_session_root(self):
        self.files.data_dir = self.config.data_dir

    def concatenated_instrument(self):
        """
        concatenate the instrument id with the description
        """
        return self.instrument + " " + self.instrument_friendly

    def deconcatenated_instrument(self, concat_str):
        """
        split the instrument string into ID and description
        """
        split = concat_str.split(' ', 1)
        self.instrument = split[0]
        self.instrument_friendly = split[1]


    def populate_by_instrument(self):
        """
        parses user information from a json struct based on a selected instrument id
        """

        instruments = self.user_info['instruments']
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

                if self.instrument == inst_id:
                    self.instrument_friendly = inst_name
                    self.instrument_short_name = instrument_short_name
                    self.instrument_list = []
                    self.instrument_list.append(self.concatenated_instrument)
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
        props = self.user_info['proposals']
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
                    if self.instrument == str(inst_id):
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


    def populate_by_proposal(self):
        """
        parses user information from a json struct based on proposal
        """

        props = self.user_info['proposals']
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

            self.proposal_list.append(prop_str)

        if not self.proposal_list:
            return 'No valid proposals for this user'

        self.proposal_list.sort(reverse=True)

        # initialize the proposal to the first in the list
        self.load_proposal(self.proposal_list[0])

        self.populate_proposal_users(self.proposal_id)

        self.populate_proposal_instruments(self.proposal_id)

    def instrument_names (self, id):
        """
        get the names for the instrument id
        """
        
        # id is getting cast to integer and I don't know why
        str_id = str(id)
        u_id = unicode(str_id)

        instruments = self.user_info['instruments']

        try:
            for inst_id, inst_block in instruments.iteritems():
                if not inst_id:
                    continue
                if not inst_block:
                    continue
                

                if u_id == inst_id:
                    inst_name = inst_block.get('instrument_name')
                    if not inst_name:
                        inst_name = 'unnamed'

                    instrument_short_name = inst_block.get('name_short')
                    if not instrument_short_name:
                        instrument_short_name = 'no short name'
                    return (inst_name, instrument_short_name)

            return ('missing', 'missing')

        except Exception:
            return ('error', 'error')

    def populate_proposal_instruments (self, proposal_id):
        """
        populate the instrument list for the selected proposal
        """
        props = self.user_info['proposals']
        if not props:
            return 'user has no proposals'

        for prop_id, prop_block in props.iteritems():

            if not prop_id:
                continue

            if not prop_block:
                continue

            if self.proposal_id != prop_id:
                continue

            # list only proposals valid for this instrument
            instruments = prop_block.get('instruments')
            if not instruments:
                return 'user has no proposals'

            try:
                self.instrument_list = []
                json_list = []
                searched = []

                for inst_id in instruments:
                    if not inst_id:
                        continue

                    # instrument list has massive amounts of dupes
                    if (inst_id in searched):
                        continue

                    searched.append(inst_id)

                    inst_name, instrument_short_name = self.instrument_names(inst_id)
                    if (inst_name is not 'missing' and inst_name is not 'error'):
                        self.instrument_friendly = inst_name
                        self.instrument_short_name = instrument_short_name
                        name = self.concatenated_instrument()
                        self.instrument_list.append(name)

                         # put in format to be used by select2
                        json_list.append({'id':name, 'text':name})
            except Exception:
                return 'No valid instruments for this user on this proposal'

           

        if not json_list:
            name = 'No instruments for this proposal'
            self.instrument_list.append(name)
            json_list.append({'id':name, 'text':name})

        json_list.sort()
        self.instrument_list.sort()
        return json_list

    def populate_user_info(self, configuration):
        """
        parses user information from a json struct
        """

        self.config = configuration
        self.instrument = configuration.instrument

        # set the original root directory to the default
        self.restore_session_root()

        try:
            self.load_meta_list()
        except Exception:
            return 'Unable to copy metadata'

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

        self.user_info = info

        if (configuration.mode == 'instrument'):
            self.is_analytical = False
            return self.populate_by_instrument()
        else:
            self.is_analytical = True
            return self.populate_by_proposal()
            

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
            json_list.append({'id':name, 'text':name})
            return json_list

        for member in members.iteritems():
            member_id = member[1]
            first_name = member_id['first_name']
            if not first_name:
                first_name = "?"
            last_name = member_id['last_name']
            if not last_name:
                last_name = '?'
            name = last_name + ", " + first_name

            self.proposal_users.append(name)
            # put in format to be used by select2
            json_list.append({'id':name, 'text':name})

        if not json_list:
            name = 'No users for this proposal'
            self.proposal_users.append(name)
            json_list.append({'id':name, 'text':name})

        json_list.sort()
        self.proposal_users.sort()
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
        currently empty
        """
        nodes = [
                'Proposal ' + self.proposal_id,
                self.instrument_short_name]
                 #datetime.datetime.now().strftime("%Y.%m.%d")

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
