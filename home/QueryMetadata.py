from home.Authorization import Authorization
import json
import pycurl
from StringIO import StringIO
import os

import requests

class MetaData(object):
    """
    structure used to pass upload metadata back and forth to the upload page
    """
    id = "id"
    table = ''
    destinationTable = ''
    displayTitle = ''
    key = ''
    value = ''
    type = 'enter'
    dependency = {}
    columns = []
    format = "%s"
    
    choose_list = []

    select_list = []
    select_list.append ( {"key":"34001", "display" :"invalid1"})
    select_list.append ( {"key":"34002", "display" :"valid"})
    select_list.append ( {"key":"34003", "display" :"invalid3"})

    def __init__(self):
        pass

class QueryMetadata(object):
    """
    loads metadata based on user authorization and context
    """

    host = ''
    user = ''
    meta_list = []

    def __init__(self, host, user):
        """
        constructor for Query class
        """
        self.host = host
        self.user = user
        self.load_meta()

    def build_query (self, meta):
        """
        builds a json query structure
        """

        #query = """
        #{
        #    "user": "d3e889",
        #    "columns": [ "name_short", "diplay_name" ],
        #    "from": "instruments",
        #    "where" : { "_id": "37654" }
        #}
        #"""
        
        query = {}
        query["user"] = self.user
        query["columns"] = meta.columns
        query["from"] = meta.table

        where_clause = {}
        # loop over the dependency list
        for key, value in meta.dependency.iteritems():
            # value is the where we are getting the actual value from the populated meta
            # key is the field , for instance "_id"
            
            for check_obj in self.meta_list:
                if value == check_obj.id:
                    where_clause[key] = check_obj.value;
                    break

        query["where"] = where_clause

        retVal = json.dumps (query, sort_keys = True, indent=4)

        return retVal

    def create_meta_upload(self, meta):
        """
        creates an object that ultimately the metadata server will be able to 
        use to store the value of this metadata field
        """
        meta_obj = {}
        meta_obj['destinationTable'] = meta.destinationTable
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

    def load_meta(self):
        """
        """
        configuration = read_config()

        # create a list of metadata entries to pass to the list upload page
        try:
            self.meta_list = []
            for meta in configuration['metadata']:

                meta_entry = MetaData()

                if 'table' in meta:
                    meta_entry.table = meta['table']

                if 'destinationTable' in meta:
                    meta_entry.destinationTable = meta['destinationTable']

                if 'metaID' in meta:
                    meta_entry.id = meta['metaID']

                if 'displayType' in meta:
                    meta_entry.type = meta['displayType']
                    
                if 'displayTitle' in meta:
                    meta_entry.displayTitle = meta['displayTitle']
                    
                if 'queryDependency' in meta:
                    meta_entry.dependency = meta['queryDependency']

                if 'queryFields' in meta:
                    meta_entry.columns = meta['queryFields']

                if 'diplayFormat' in meta:
                    meta_entry.format = meta['diplayFormat']

                if 'key' in meta:
                    meta_entry.key = meta['key']

                if 'value' in meta:
                    meta_entry.value = meta['value']

                self.meta_list.append(meta_entry)

        except KeyError:
            return 'Configuration: missing metadata'

        return ''


    def initial_population(self):
        """
        assumption that the base seed is in the first element
        """
        for meta in self.meta_list:
            # if this is a user entered field it doesn't need to be filled
            if meta.type != "enter":
                self.build_query(meta)


    def get_list(self, query):
        """
            gets a list of items based on the json query structure
        """

        r=""


        try:

            headers = {'content-type': 'application/json'}
            url = self.host + '/uploader'

            r = requests.post(url, headers=headers, data=query)

            l = json.loads(r.content)

            return l

        except Exception, e:
            print e
            return[]

    def populate_metadata_from_form(self, form):
        """
        populates the upload metadata from the upload form
        """
        for meta in self.meta_list:
            try:
                value = form[meta.id]
                if value:
                    meta.value = value
            except KeyError:
                pass
        

    def post_upload_metadata(self, meta_list):
        """
        upload metadata to server
        """
        meta_str = json.dumps(meta_list)

        try:
            headers = {'content-type': 'application/json'}
            url = self.host + '/ingest'

            r = requests.put(url, headers=headers, data=meta_str)

            l = json.loads(r.content)

            return l

        except Exception, e:
            print e
            return[]

    def query (self, form):
        self.post_upload_metadata(form)
        return None 


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
