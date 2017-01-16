"""
    index server unit and integration tests
"""
from __future__ import absolute_import

import unittest
from .QueryMetadata import QueryMetadata

class IndexServerUnitTests(unittest.TestCase):
    """
    index server unit and integration tests
    """

    def test_get_display(self):
        """
        test get_diplay
        """
        mdata = self.test_initialize()

        self.assertTrue(True)

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
