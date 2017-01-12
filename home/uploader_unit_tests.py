"""
    index server unit and integration tests
"""

# pylint: disable=no-self-use
# justification: unit test requirement


import unittest
from QueryMetadata import QueryMetadata

class IndexServerUnitTests(unittest.TestCase):
    """
    index server unit and integration tests
    """

    #def test_meta_upload_list(self):
    #    """
    #    test_meta_upload_list
    #    """
    #    x = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8181', 'd3e889')

    #    x.load_meta()

    #    for meta in x.meta_list:
    #        meta.value = '34002'

    #    l = x.create_meta_upload_list()

    #    print l

    #    server_url = 'http://dmlb2000.emsl.pnl.gov'
    #    port = '8051'
    #    transaction_id = get_unique_id(server_url, port, '1', 'transaction')
    #    print transaction_id

    #    t = {"destinationTable": "Transactions._id", "value": transaction_id}

    #    l.append(t)

    #    file_id = get_unique_id(server_url, port, '1', 'file_mode')

    #    t = {
    #        'destinationTable': 'Files',
    #        '_id': file_id,
    #        'name': 'foo.txt', 'subdir': 'a/b/',
    #        'ctime': 'Tue Nov 29 14:09:05 PST 2016',
    #        'mtime': 'Tue Nov 29 14:09:05 PST 2016',
    #        'size': 128, 'mimetype': 'text/plain'
    #    }

    #    l.append(t)

    #    blob = json.dumps(l, sort_keys=True, indent=4)

    #    x = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8121', 'd3e889')

    #    x.post_upload_metadata(l)

    #    print blob

    #    file = open("metablob.json", "w")

    #    file.write(blob)

    #    file.close()

    def test_get_display(self):
        """
        test get_diplay
        """
        mdata = self.test_initialize()

        node = mdata.get_node("instrumentDirectory")
        display = mdata.get_display(node)
        print display

        node = mdata.get_node("ProposalDirectory")
        display = mdata.get_display(node)
        print display

    def test_initialize(self):
        """
        tests the initial population of the metadata
        """
        mdata = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8181', 'd3e889')

        mdata.load_meta()

        mdata.initial_population()

        return mdata

    def test_query_meta(self):
        """
        builds the metadata queries to the policy server
        """
        mdata = QueryMetadata('http://dmlb2000.emsl.pnl.gov:8181', 'd3e889')

        mdata.load_meta()

        for meta in mdata.meta_list:
            # if this is a user entered field it doesn't need to be filled
            if meta.display_type != "enter":
                query = mdata.build_query(meta)

                mdata.get_list(query)


if __name__ == '__main__':
    unittest.main()
    print 'test complete'
