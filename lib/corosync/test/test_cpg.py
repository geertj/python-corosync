#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

import time
import random

from corosync.cpg import CPG
from corosync.test.base import BaseTest
from corosync.dispatch import ThreadedDispatcher


class LoggingCPG(CPG):

    def __init__(self, name, stop):
	super(LoggingCPG, self).__init__(name)
	self.m_messages = []
	self.m_changes = []

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
	cpg = LoggingCPG('test.group', stop='stop')
	dispatcher = ThreadedDispatcher()
	dispatcher.add_service(cpg)
	dispatcher.start()
	self.start_on_cluster_nodes(self._node_test_simple)
	nodes = len(self.cluster_nodes())
	while len(cpg.members()) != nodes + 1:
	    time.sleep(0.5)  # wait until everybody has joined
	cpg.send_message('ping')
	cpg.send_message('stop')
	dispatcher.wait()
	assert len(cpg.messages()) == 1
	assert cpg.messages()[0][1] == 'ping'
	result = self.remote_results()
	for res in result:
	    assert len(res) == 1
	    assert res[0][1] == 'ping'

    def _node_test_ordering(self):
	cpg = LoggingCPG('test.ordering', stop='stop')
	dispatcher = ThreadedDispatcher()
	dispatcher.add_service(cpg)
	dispatcher.start()
	while not cpg.messages():
	    time.sleep(0.5)  # wait for 'start' message'
	for i in range(1000):
	    cpg.send_message('test-%d' % random.randint(0, 100000))
	dispatcher.wait()
	return cpg.messages()

    def test_ordering(self):
	self.require(cluster=True, nodes=3)
	cpg = LoggingCPG('test.ordering', stop='stop')
	dispatcher = ThreadedDispatcher()
	dispatcher.add_service(cpg)
	dispatcher.start()
	self.start_on_cluster_nodes(self._node_test_ordering)
	nodes = len(self.cluster_nodes())
	while len(cpg.members()) != nodes + 1:
	    time.sleep(0.5)  # wait until everybody has joined
	cpg.send_message('start')
	while len(cpg.messages()) != nodes * 1000 + 1:
	    time.sleep(0.5)
	cpg.send_message('stop')
	dispatcher.wait()
	assert len(cpg.messages()) == nodes * 1000 + 1
	result = self.remote_results()
	assert len(result) == nodes
	for res in result:
	    assert len(res) == nodes * 1000 + 1
	reference = [ msg for (addr, msg) in cpg.messages() ]
	for res in result:
	    messages = [ msg for (addr, msg) in res ]
	    assert messages == reference
