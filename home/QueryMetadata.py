# pylint: disable=too-many-instance-attributes
# justification: it is the perfect amount of attributes


"""
class to query the policy server and provide metadata to the browser
"""
import json
import os

import requests
import copy

# pylint: disable=too-few-public-methods
# justification: perfect amount of methods, possibly look at using "collection"

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
    query_dependencies = None
    # type of display (select, entry, etc.)
    display_type = ''
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
    browser_field_population = None

    def __init__(self):
        pass


class QueryMetadata(object):
    """
    loads metadata based on user authorization and context
    """

    host = ''
    user = ''
    meta_list = []
    auth = {}

    def __init__(self, host):
        """
        constructor for Query class
        """
        self.host = host

    def build_query(self, meta):
        """
        builds a json query structure:
        {
            "user": "1234666",
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


    def create_meta_upload_list(self):
        """
        creates list of objects that ultimately the metadata server will be able to
        use to store the value of this metadata field
        """
        upload_list = []

        for meta in self.meta_list:
            upload_list.append(create_meta_upload(meta))

        return upload_list

    @staticmethod
    def set_if_there(meta, meta_key, obj, attr):
        """ kludge to avoid too many conditionals """
        if meta_key in meta:
            setattr(obj, attr, meta[meta_key])

    def load_meta(self):
        """
        puts the metadata into a format that can eventually be
        read by the metadata archive
        """
        configuration = read_config()

        # get authorization

        self.set_if_there(configuration, 'auth', self, 'auth')


        # create a list of metadata entries to pass to the list upload page
        try:
            self.meta_list = []
            for meta in configuration['metadata']:

                meta_entry = MetaData()

                meta_entry.browser_field_population = {}

                self.set_if_there(meta, 'sourceTable', meta_entry, 'source_table')
                self.set_if_there(meta, 'destinationTable', meta_entry, 'destination_table')
                self.set_if_there(meta, 'metaID', meta_entry, 'meta_id')
                self.set_if_there(meta, 'displayType', meta_entry, 'display_type')
                self.set_if_there(meta, 'displayTitle', meta_entry, 'display_title')
                self.set_if_there(meta, 'queryDependency', meta_entry, 'query_dependencies')
                self.set_if_there(meta, 'valueField', meta_entry, 'value_field')
                self.set_if_there(meta, 'queryFields', meta_entry, 'columns')
                self.set_if_there(meta, 'diplayFormat', meta_entry, 'display_format')
                self.set_if_there(meta, 'key', meta_entry, 'key')
                self.set_if_there(meta, 'value', meta_entry, 'value')
                self.set_if_there(meta, 'directoryOrder', meta_entry, 'directory_order')

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

        print 'build_selection_list, query_result is'
        print query_result

        meta.browser_field_population['meta_id'] = meta.meta_id

        # build the list of choices
        choices = []
        for result in query_result:
            # result is a hash of column identifiers and values
            # first get the key field if any
            try:
                key = result[meta.value_field]
            except KeyError:
                key = ''

            if meta.display_format != '':
                display = meta.display_format % result
            else:
                display = ''

            # put in format to be used by select2
            choices.append({"id": key, "text": display})

        meta.browser_field_population['selection_list'] = choices

    def update_parents(self, meta):
        """
        recursively updates meta nodes until the base node is updatad
        """

        if meta.initialized:
            return

        for meta_id in meta.query_dependencies.values():
            dependency = self.get_node(meta_id)

            # ignore self referential nodes dfh
            if meta_id != dependency.meta_id:
                if not dependency.initialized:
                    self.update_parents(dependency)

        # once the dependencies are filled we can create the query and populate
        # the list
        query = self.build_query(meta)

        query_result = self.get_list(query)

        # validate that we have a valid json return value
        # will throw an error to the base level if not
        # json.loads(query_result) # why does this fail with valid json?

        self.build_selection_list(meta, query_result)

        if meta.value == '':
            if meta.browser_field_population:
                sel_list = meta.browser_field_population['selection_list']
                if sel_list:
                    meta.value = sel_list[0]['id']


    def initial_population(self, network_id):
        """
        populate all the lists from the policy server for the first time
        """

        # this is a special case, self-referential node that replaces the network id 
        # with the pacifica id.  We have other ways of getting the pacifica id, but 
        # leaving this in for now as it follows the basic model for transfering metadata
        # to the metadata archive.  Refer back to this in time. (dfh)

        node = self.get_node('logon')
        node.value = network_id

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

    def get_Pacifica_user(self, network_id):
        """
            user specific to this instance of Pacifica
        """

        try:
            headers = {'content-type': 'application/json'}
            url = self.host + '/status/users/search/' + network_id + '/simple'

            certlist = self.auth['cert']
            for path in certlist:
                exists = os.path.isfile(path)
                if not exists:
                    raise Exception('Authorization file not found')

            reply = requests.get(url, headers=headers,**self.auth)
            data = json.loads(reply.content)
            record = data[0]            
            id = record['person_id']
            return id

        except Exception, ex:
            err = str(ex.strerror) + ': url: ' + url
            print err
            raise Exception (err)

    def get_list(self, query):
        """
            gets a list of items based on the json query structure
        """

        try:
            headers = {'content-type': 'application/json'}
            url = self.host + '/uploader'

            reply = requests.post(url, headers=headers, data=query, **self.auth)

            data = json.loads(reply.content)

            return data

        except Exception, ex:
            err = str(ex.message) + ' query: ' + query
            print err
            raise Exception (err) 


    def get_display(self, meta):
        """
        gets the display value for a meta node
        """
        query = self.build_query(meta)
        query_result = self.get_list(query)
        self.build_selection_list(meta, query_result)

        selection_list = meta.browser_field_population['selection_list']
        entry = selection_list[0]
        display = entry['text']

        return display

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

def create_meta_upload(meta):
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
