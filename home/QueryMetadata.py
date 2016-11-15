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
    table = 'TransactionKeyValue'
    title = ''
    value = ''
    type = 'enter'
    dependency = {}
    columns = []
    format = "%s"
    
    choose_list = []

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
        self.user = user.upper()
        self.load_meta()

    def build_query (self, meta):
        """
        builds a json query structure
        """

        x = """
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

        retVal = json.dumps (query)

        return retVal

    def load_query(self, meta):
        """
        """

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

                if 'metaID' in meta:
                    meta_entry.id = meta['metaID']

                if 'displayType' in meta:
                    meta_entry.type = meta['displayType']
                    
                if 'queryDependency' in meta:
                    meta_entry.dependency = meta['queryDependency']

                if 'queryFields' in meta:
                    meta_entry.columns = meta['queryFields']

                if 'diplayFormat' in meta:
                    meta_entry.format = meta['diplayFormat']

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

        try:

            headers = {'content-type': 'application/json'}
            url = self.host + '/uploader'

            r = requests.post(url, headers=headers, data=query)

            l = json.loads(r.content)

            return l

        except Exception, e:
            print e
            return []

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
