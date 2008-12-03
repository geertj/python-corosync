#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

from corosync.test.base import BaseTest


class TestTest(BaseTest):
    """Test the test infrastructure."""

    def remote_func(self):
	return 'ping'

    def test_remote(self):
	"""Test remote test invocation"""
	self.require(cluster=True, nodes=2)
	self.start_on_cluster_nodes(self.remote_func)
	result = self.remote_results()
	assert len(result) > 0
	for res in result:
	    assert res == 'ping'
