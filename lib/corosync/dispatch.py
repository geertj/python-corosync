#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

import select
import errno
from threading import Thread

from corosync.exception import Error

DISPATCH_ONE = 1
DISPATCH_ALL = 2
DISPATCH_BLOCKING = 3


class ThreadedDispatcher(Thread):
    """Dispatcher thread."""

    def __init__(self):
	"""Constructor."""
	super(ThreadedDispatcher, self).__init__()
	self.m_services = []

    def add_service(self, service):
	"""Start dispatching events for `service'."""
	self.m_services.append(service)

    def start(self):
	"""Start dispatching events."""
	super(ThreadedDispatcher, self).start()

    def run(self):
	"""Main work function."""
	fds = []
	timeout = 1.0
	self.m_stop = False
	for service in self.m_services:
	    service.start()
	while not self.m_stop:
	    fds = [ service.fileno() for service in self.m_services if
		    service.active() ]
	    if not fds:
		break  # all services stopped
	    try:
		ret = select.select(fds, [], [], timeout)
	    except select.error, err:
		error = err.args[0]
		if error == errno.EINTR:
		    continue  # interrupted by signal
		else:
		    raise Error, str(err)  # not recoverable
	    if not ret[0]:
		continue  # timeout
	    for service in self.m_services:
		if service.fileno() in ret[0]:
		    service.dispatch()
	for service in self.m_services:
	    if service.active():
		service.stop()

    def stop(self):
	"""Stop all registered services and then stop the dispatcher thread."""
	self.m_stop = True
	self.join()

    def wait(self):
	"""Wait until all services are stopped and then stop the dispatcher thread."""
	self.join()
