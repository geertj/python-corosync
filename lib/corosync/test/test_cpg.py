#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

import time

from corosync.cpg import CPG
from corosync.test.base import BaseTest
from corosync.dispatch import ThreadedDispatcher


class LoggingCPG(CPG):

    def __init__(self, name, stop):
	super(LoggingCPG, self).__init__(name)
	self.m_messages = []
	self.m_changes = []
	self.m_stop = stop

    def messages(self):
	return self.m_messages

    def changes(self):
	return self.m_changes

    def message_delivered(self, addr, message):
	if message == 'stop':
	    self.stop()
	else:
	    self.m_messages.append((addr, message))

    def configuration_changed(self, members, left, joined):
	self.m_changes.append((members, left, joined))


class TestCPG(BaseTest):
    """Simple test."""

    def _node_test_simple(self):
	cpg = LoggingCPG('test.group', stop='stop')
	dispatcher = ThreadedDispatcher()
	dispatcher.add_service(cpg)
	dispatcher.start()
	dispatcher.wait()
	return cpg.messages()

    def test_simple(self):
	self.require(cluster=True, nodes=3)
	self.start_on_cluster_nodes(self._node_test_simple)
	cpg = LoggingCPG('test.group', stop='stop')
	dispatcher = ThreadedDispatcher()
	dispatcher.add_service(cpg)
	dispatcher.start()
	time.sleep(2.0)  # ensure all nodes are registered
	cpg.send_message('ping')
	cpg.send_message('stop')
	dispatcher.wait()
	assert len(cpg.messages()) == 1
	assert cpg.messages()[0][1] == 'ping'
	result = self.remote_results()
	for res in result:
	    assert len(res) == 1
	    assert res[0][1] == 'ping'
