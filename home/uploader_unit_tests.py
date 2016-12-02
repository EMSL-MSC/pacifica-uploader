"""
    index server unit and integration tests
"""

import unittest
import json

from QueryMetadata import QueryMetadata




class IndexServerUnitTests(unittest.TestCase):
    """
    index server unit and integration tests
    """

    def test_create_meta_upload_list(self):
        """
        
        """
        x = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8181', 'd3e889')

        x.load_meta()

        for meta in x.meta_list:
            meta.value = '34002'

        l = x.create_meta_upload_list()

        print l

        t = {"destinationTable": "Transaction._id", "value": 48909809}

        l.append (t)

        blob = json.dumps(l)

        x = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8121')

        print blob

        file = open("metablob.txt", "w")

        file.write(blob)

        file.close()

    def test_query_meta(self):
        """
        
        """
        x = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8181', 'd3e889')

        x.load_meta()

        #query = """
        #{
        #    "user": "d3e889",
        #    "columns": [ "first_name", "last_name" ],
        #    "from": "users",
        #    "where" : { "proposal_id": "48273" }
        #}
        #"""
        #y = x.get_list(query)
        #print y

        file = open("query.txt", "w")

        for meta in x.meta_list:
            # if this is a user entered field it doesn't need to be filled
            if meta.type != "enter":
                query = x.build_query(meta)

                file.write( query)

                
                y = x.get_list(query)

                z = json.dumps (y, sort_keys = True, indent=4)

                file.write( z)

        file.close()



if __name__ == '__main__':
    unittest.main()
    print 'test complete'
