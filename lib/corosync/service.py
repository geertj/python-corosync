#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.


class Service(object):
    """Base class for python-corosync services."""

    def start(self):
	"""Register to the executive and start receiving events."""
	raise NotImplementedError

    def stop(self):
	"""Stop receiving events."""
	raise NotImplementedError

    def active(self):
	"""Return True if this service is active, false otherwise."""
	raise NotImplementedError

    def fileno(self):
	"""Return a file descriptor that can be used to wait for events."""
	raise NotImplementedError

    def dispatch(self, type=None):
	"""Dispatch events for this service."""
	raise NotImplementedError
