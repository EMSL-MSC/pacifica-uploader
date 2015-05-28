import json


from uploader import get_info

from file_tools import file_manager


class session_state(object):
    """description of class"""
    """
    meta data about for a session
    """
    server_path = ''

    user = ''
    user_full_name = ''
    password = ''

    current_user = None

    current_time = ''
    instrument = ''
    instrument_friendly = ''
    proposal_friendly = ''
    proposal_id = ''

    #selected_dirs = []
    #selected_files = []
    #dir_sizes = []
    #file_sizes = []
    #directory_history = []

    files = file_manager()

    # meta data values
    meta_list = []

    # proposals
    proposal_list = []
    proposal_users = []

    # process that handles bundling and uploading
    bundle_process = None

    bundle_filepath = ''
    # size of the current bundle
    bundle_size = 0
    bundle_size_str = ''
    free_size_str = ''

    # free disk space
    free_space = 0

    def load_proposal (self, proposal):
        self.proposal_friendly = proposal

        # split the proposal string into ID and description
        split = self.proposal_friendly.split()
        self.proposal_id = split[0]

    def load_request_proposal (self, request):
        # get the selected proposal string from the post
        proposal = request.POST.get("proposal")
        self.load_proposal(proposal)

    def concatenated_instrument(self):
        """
        concatenate the instrument id with the description
        """
        return self.instrument + " " + self.instrument_friendly

    def clear_upload_lists(self):
        """
        clears the directory and file lists
        """
        self.selected_files = []
        self.selected_dirs = []

    def populate_user_info(self):
        """
        parses user information from a json struct
        """
        # get the user's info from EUS
        info = get_info(protocol="https",
            server=self.server_path,
            user=self.user,
            password=self.password,
            info_type = 'userinfo')

        try:
            info = json.loads(info)
        except Exception:
            return 'Unable to parse user information'

        # print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

        first_name = info["first_name"]
        if not first_name:
            return 'Unable to parse user name'
        last_name = info["last_name"]
        if not last_name:
            return 'Unable to parse user name'

        self.user_full_name = '%s (%s %s)' % (self.user, first_name, last_name)

        instruments = info["instruments"]

        try:
            valid_instrument = False
            for inst_id, inst_block in instruments.iteritems():
                inst_name = inst_block.get("instrument_name")
                inst_str = inst_id + "  " + inst_name
                if self.instrument == inst_id:
                    self.instrument_friendly = inst_name
                    valid_instrument = True

                #print inst_str
                #print ""

            if not valid_instrument:
                return 'User is not valid for this instrument'
        except Exception:
            return 'Unable to parse user instruments'

        """
        need to filter proposals based on the existing instrument 
        if there is no valid proposal for the user for this instrument
        throw an error
        """
        #print "props"
        props = info["proposals"]
        self.proposal_list = []
        for prop_id, prop_block in props.iteritems():
            title = prop_block.get("title")
            prop_str = prop_id + "  " + title

            # list only proposals valid for this instrument
            instruments = prop_block.get("instruments")

            try:
                if instruments is not None and len(instruments) > 0:
                    for inst_id in instruments: # eh.  inst_id is a list of 1 element.
                        if self.instrument == str(inst_id):
                            if prop_str not in self.proposal_list:
                                self.proposal_list.append(prop_str)
            except Exception, err:
                return 'No valid proposals for this user on this instrument'

        if len(self.proposal_list) == 0:
            return 'No valid proposals for this user on this instrument'

        self.proposal_list.sort(key=lambda x: int(x.split(' ')[0]), reverse=True)

        # no errors found
        return ''

    def populate_proposal_users(self):
        """
        parses user for a proposal and instrument from a json struct
        """

        # get the user's info from EUS
        info = get_info(protocol="https",
                         server=self.server_path,
                         user=self.user,
                         password=self.password,
                         info_type = 'proposalinfo/' + self.proposal_id)

        try:
            info = json.loads(info)
        except Exception:
            return 'Unable to parse proposal user information'

        # print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

        members = info["members"]
        if not members:
            return 'Unable to parse proposal members'

        self.proposal_users = []

        for member in members.iteritems():
            id =  member[1]
            first_name = id["first_name"]
            if not first_name:
                return 'Unable to parse user name'
            last_name = id["last_name"]
            if not last_name:
                return 'Unable to parse user name'
            self.proposal_users.append(first_name + " " + last_name)

    def populate_proposal_users(self):
        """
        parses user for a proposal and instrument from a json struct
        """

        # get the user's info from EUS
        info = get_info(protocol="https",
                         server=self.server_path,
                         user=self.user,
                         password=self.password,
                         info_type = 'proposalinfo/' + self.proposal_id)

        try:
            info = json.loads(info)
        except Exception:
            return 'Unable to parse proposal user information'

        # print json.dumps(info, sort_keys=True, indent=4, separators=(',', ': '))

        members = info["members"]
        if not members:
            return 'Unable to parse proposal members'

        self.proposal_users = []

        for member in members.iteritems():
            id =  member[1]
            first_name = id["first_name"]
            if not first_name:
                return 'Unable to parse user name'
            last_name = id["last_name"]
            if not last_name:
                return 'Unable to parse user name'
            self.proposal_users.append(first_name + " " + last_name)

    def cleanup_session(self):
        """
        resets a session to a clean state
        """
        self.instrument = None
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
        self.meta_list = []
        self.dir_sizes = []
        self.directory_history = []
        self.file_sizes = []
        self.selected_dirs = []
        self.selected_files = []
