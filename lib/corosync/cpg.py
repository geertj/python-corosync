#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

from corosync import _cpg

Error = _cpg.Error

# Import CPG_* constant
for symbol in dir(_cpg):
    if symbol.isupper():
	globals()[symbol] = getattr(_cpg, symbol)


class ClosedProcessGroup(object):
    """Closed process group.

    This object provides an object oriented API to AIS closed process groups.
    """

    def __init__(self, name):
	"""Constructor."""
	self.m_name = name
	self.m_handle = None

    def name(self):
	"""Return the process group name."""
	return self.m_name

    def activate(self):
	"""Activate the process group. This will start the delivery of
	messages."""
	self.m_handle = _cpg.initialize(self)
	_cpg.join(self.m_handle, self.m_name)

    def deactivate(self):
	"""Deactivate the process group. This will stop the delivery of
	messages."""
	_cpg.leave(self.m_handle, self.m_name)
	_cpg.finalize(self.m_handle)
	self.m_handle = None

    def fileno(self):
	"""Return a file descriptor that can be selected on."""
	if self.m_handle is None:
	    raise Error, 'Process group not activated.'
	return _cpg.fd_get(self.m_handle)

    def members(self):
	"""Return a list of group members.
	
	The return value is a list of 3-tuples (nodeid, pid, reason).
	"""
	if self.m_handle is None:
	    raise Error, 'Process group not activated.'
	name, members = _cpg.membership_get(self.m_handle)
	return members

    def send_message(self, message, guarantee=TYPE_AGREED):
	"""Send a message to all group members."""
	if self.m_handle is None:
	    raise Error, 'Process group not activated.'
	_cpg.mcast_joined(self.m_handle, guarantee, message)

    def _deliver_fn(self, name, addr, message):
	"""INTERNAL: message delivery callback."""
	self.message_delivered(addr, message)

    def _confchg_fn(self, name, members, left, joined):
	"""INTERNAL: configuration change callback."""
	self.configuration_changed(members, left, joined)

    def message_delivered(self, addr, message):
	"""Callback that is raised when a message is delivered."""
	raise NotImplementedError

    def configuration_changed(self, members, left, joined):
	"""Callback that is raised when a configuration change happens."""
	raise NotImplementedError
