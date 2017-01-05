
# pylint: disable=broad-except
# justification: argument with style

"""
class to query the policy server and provide metadata to the browser
"""
import json
import os

import requests


class MetaData(object):
    """
    structure used to pass upload metadata back and forth to the upload page
    """
    # unique ID form this meta node
    meta_id = "id"
    # table from which the selection values are drawn
    source_table = ''
    # table to which the selection will be stored
    destination_table = ''
    # columns that will be pulled from the table
    columns = []
    # returned field that will be used as the actual value to be returned to
    # the uploader
    value_field = ''
    # used for key/value pairs
    key = ''
    # selected value
    value = ''
    # meta nodes that must be populated to build the query for this node
    query_dependencies = {}
    # title of field in the browser client
    display_title = ''
    # format of the displayed data
    display_format = "%s"

    # format of the artificial directory name (if any) for searching the
    # archive
    directory_order = None

    # flag that indicates whether this node has been initialized
    initialized = False

    # a dictionary that holds the meta ID and a list to populate a dropdown
    # the browser uses the ID to populate the correct field
    browser_field_population = {}

    def __init__(self):
        pass


class QueryMetadata(object):
    """
    loads metadata based on user authorization and context
    """

    host = ''
    user = ''
    meta_list = []

    def __init__(self, host, networkID):
        """
        constructor for Query class
        """
        self.host = host
        self.load_meta()

        self.initialize_user(networkID)

    def build_query(self, meta):
        """
        builds a json query structure:
        {
            "user": "d3e889",
            "columns": [ "name_short", "diplay_name" ],
            "from": "instruments",
            "where" : { "_id": "37654" }
        }
        """

        query = {}
        query["user"] = self.user
        query["columns"] = meta.columns
        query["from"] = meta.source_table

        where_clause = {}
        # loop over the dependency list
        for column, meta_id in meta.query_dependencies.iteritems():
            # meta_id is the where we are getting the actual value from the populated meta
            # column is the field , for instance "_id"

            for check_obj in self.meta_list:
                if meta_id == check_obj.meta_id:
                    where_clause[column] = check_obj.value
                    break

        query["where"] = where_clause

        ret_val = json.dumps(query, sort_keys=True, indent=4)

        return ret_val

    def create_meta_upload(self, meta):
        """
        creates an object that ultimately the metadata server will be able to
        use to store the value of this metadata field
        """
        meta_obj = {}
        meta_obj['destinationTable'] = meta.destination_table
        if meta.key != "":
            meta_obj['key'] = meta.key
        meta_obj['value'] = meta.value

        return meta_obj

    def create_meta_upload_list(self):
        """
        creates list of objects that ultimately the metadata server will be able to
        use to store the value of this metadata field
        """
        upload_list = []

        for meta in self.meta_list:
            upload_list.append(self.create_meta_upload(meta))

        return upload_list

    def initialize_user(self, network_id):
        """
        initializes the login node with the network ID so that
        it can be converted to the user id on meta init.
        we are assuming all uploaders with have a login
        """
        try:
            meta = self.get_node('logon')
            meta.value = network_id
            self.user = -1

            return True
        except Exception:
            return False

    def load_meta(self):
        """
        puts the metadata into a format that can eventually be
        read by the metadata archive
        """
        configuration = read_config()

        # create a list of metadata entries to pass to the list upload page
        try:
            self.meta_list = []
            for meta in configuration['metadata']:

                meta_entry = MetaData()

                if 'table' in meta:
                    meta_entry.source_table = meta['table']

                if 'destinationTable' in meta:
                    meta_entry.destination_table = meta['destinationTable']

                if 'metaID' in meta:
                    meta_entry.meta_id = meta['metaID']

                if 'displayType' in meta:
                    meta_entry.display_type = meta['displayType']

                if 'displayTitle' in meta:
                    meta_entry.display_title = meta['displayTitle']

                if 'queryDependency' in meta:
                    meta_entry.query_dependencies = meta['queryDependency']

                if 'valueField' in meta:
                    meta_entry.value_field = meta['valueField']

                if 'queryFields' in meta:
                    meta_entry.columns = meta['queryFields']

                if 'diplayFormat' in meta:
                    meta_entry.display_format = meta['diplayFormat']

                if 'key' in meta:
                    meta_entry.key = meta['key']

                if 'value' in meta:
                    meta_entry.value = meta['value']

                if 'directoryOrder' in meta:
                    meta_entry.directory_order = meta['directoryOrder']

                self.meta_list.append(meta_entry)

        except KeyError:
            return 'Configuration: missing metadata'

        return ''

    def get_node(self, meta_id):
        """
        returns a meta node based on it's unique id
        """
        for meta in self.meta_list:
            if meta_id == meta.meta_id:
                return meta

        return None

    def build_selection_list(self, meta, query_result):
        """
        builds a json structure that can be used by the browser client
        to populate a dropdown list

        format:
            field_population = {'meta_id':'thingy',
                      'selection_list':[
                          {"id":"34001", "text" :"invalid1"},
                          {"id":"34002", "text" :"valid"},
                          {"id":"34003", "text" :"invalid3"}
                          ]}
        """

        meta.browser_field_population['meta_id'] = meta.meta_id

        # build the list of choices
        choices = []
        for result in query_result:
            # result is a hash of column identifiers and values
            # first get the key field if any
            try:
                key = result[meta.value_field]
            except Exception:
                key = ''

            try:
                # format the display value
                display = meta.display_format % result
            except Exception:
                # skip it if it doesn't exist
                pass

             # put in format to be used by select2
            choices.append({"id": key, "text": display})

        # special case for logon, need to initialize user
        if meta.meta_id == 'logon':
            first = choices[0]
            meta.value = first['id']
            self.user = first['id']

        meta.browser_field_population['selection_list'] = choices

    def update_parents(self, meta):
        """
        recursively updates meta nodes until the base node is updatad
        """

        if meta.initialized:
            return

        for query_field, meta_id in meta.query_dependencies.iteritems():
            dependency = self.get_node(meta_id)

            # ignore self referential nodes
            if meta_id != dependency.meta_id:
                if not dependency.initialized:
                    self.update_parents(dependency)

        # once the dependencies are filled we can create the query and populate
        # the list
        query = self.build_query(meta)

        query_result = self.get_list(query)

        self.build_selection_list(meta, query_result)

        if meta.value == '':
            if meta.browser_field_population:
                sel_list = meta.browser_field_population['selection_list']
                if sel_list:
                    meta.value = sel_list[0]['id']

    def initial_population(self):
        """
        populate all the lists from the policy server for the first time
        """
        init_fields = []

        for meta in self.meta_list:
            # if this is a user entered field it doesn't need to be filled
            if meta.display_type != "enter":
                self.update_parents(meta)
                if any(meta.browser_field_population):
                    init_fields.append(meta.browser_field_population)

        return init_fields

    def populate_dependencies(self, form):
        """
        when a selected field changes in the browser,
        the modified for is sent here.  The changed item is
        updated and all dependencies are updated.
        """
        update_fields = []

        # get the node that changed
        selected_id = form['selected_id']
        meta = self.get_node(selected_id)

        # fill in the current data from the form
        self.populate_metadata_from_form(form)

        self.update_children(meta, update_fields)

        return update_fields

    def find_children(self, meta_id):
        """
        find a list of nodes that contain this id in their dependency list
        """
        children = []

        for meta in self.meta_list:
            # if this is a user entered field it doesn't need to be filled
            if meta.display_type != "enter":
                ids = list(meta.query_dependencies.values())
                if meta_id in ids:
                    # cut off self-referential infinite loop
                    if meta_id != meta.meta_id:
                        children.append(meta)

        return children

    def update_children(self, meta, update_fields):
        """
        queries the policy server to reload the selection options
        for fields that are dependent on a modified field
        """
        children = self.find_children(meta.meta_id)

        for child in children:
            query = self.build_query(child)
            query_result = self.get_list(query)
            self.build_selection_list(child, query_result)
            if any(child.browser_field_population):
                update_fields.append(child.browser_field_population)

            self.update_children(child, update_fields)

    def get_list(self, query):
        """
            gets a list of items based on the json query structure
        """
        try:

            headers = {'content-type': 'application/json'}
            url = self.host + '/uploader'

            reply = requests.post(url, headers=headers, data=query)

            data = json.loads(reply.content)

            # check for error
            try:
                status = data['status']
                print status
                return []
            except Exception, ex:
                print ex.message
                return data

        except Exception, ex:
            print ex
            return[]

    def populate_metadata_from_form(self, form):
        """
        populates the upload metadata from the upload form
        """
        for meta in self.meta_list:
            try:
                value = form[meta.meta_id]
                if value:
                    meta.value = value
            except KeyError:
                pass


def read_config():
    """
    read the configuration file
    """
    config_file = 'UploaderConfig.json'

    if not os.path.isfile(config_file):
        return ''

    with open(config_file, 'r') as config:
        configuration = json.load(config)

    return configuration
