#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

import os
import os.path
import pickle
from ConfigParser import ConfigParser
from threading import Thread

import pexpect
from nose import SkipTest

import corosync


class Error(Exception):
    """Test error."""


class RemoteTest(Thread):
    """Run a remote test in a separate thread."""

    def __init__(self, node, module, cls, method):
	super(RemoteTest, self).__init__()
	self.m_node = node
	self.m_module = module
	self.m_class = cls
	self.m_method = method

    def _run_remote(self):
	"""Run one test on a cluster node."""
	ssh = pexpect.spawn('ssh root@%s' % self.m_node)
	ssh.expect('#')
	ssh.sendline('cd python-corosync')
	ssh.expect('#')
	ssh.sendline('eval `python env.py`')
	ssh.expect('#')
	ssh.sendline('python')
	ssh.expect('>>>')
	ssh.sendline('import pickle')
	ssh.expect('>>>')
	ssh.sendline('from %s import %s as Test' % (self.m_module, self.m_class))
	ssh.expect('>>>')
	ssh.sendline('test = Test()')
	ssh.expect('>>>')
	ssh.sendline('ret = test.%s()' % self.m_method)
	ssh.expect('>>>')
	ssh.sendline('print pickle.dumps(ret).encode("base64")')
	ssh.expect('\r\n')
	ssh.expect('>>>')
	result = pickle.loads(ssh.before.decode('base64'))
	ssh.sendline('quit()')
	ssh.expect('#')
	ssh.sendline('exit')
	ssh.close()
	return result

    def run(self):
	self.m_result = self._run_remote()

    def result(self):
	return self.m_result


class BaseTest(object):
    """Simple test."""

    @classmethod
    def setup_class(cls):
	"""Class constructor."""
	base = os.path.normpath(corosync.__file__)
	for i in range(3):
	    base = os.path.split(base)[0]
	cls.c_topdir = base
	fname = os.path.join(base, 'env.py')
	if not os.access(fname, os.R_OK):
	    raise SkipTest, 'Tests must be run from a checked out source tree.'
	fname = os.path.join(base, 'test.cfg')
	if not os.access(fname, os.R_OK):
	    raise SkipTest, 'Test configuration not found at %s' % fname
	config = ConfigParser()
	config.read(fname)
	cls.c_config = config
	cls.c_copied_source = False
	if cls.cluster_enabled():
	    cls._check_cluster_nodes()
	    cls._copy_source_tree()

    @classmethod
    def topdir(cls):
	"""Return the top dir of the source tree."""
	return cls.c_topdir

    @classmethod
    def cluster_enabled(cls):
	"""Return True if cluster tests are enabled."""
	return cls.c_config.getboolean('test', 'cluster_tests')

    @classmethod
    def cluster_nodes(cls):
	"""Return the list of configured cluster nodes (excluding the local
	node)."""
	return cls.c_config.get('test', 'cluster_nodes').split()

    @classmethod
    def _check_cluster_nodes(cls):
	"""Check that we can reach all cluster nodes and that they have
	corosync running."""
	for node in cls.cluster_nodes():
	    ssh = pexpect.spawn('ssh %s echo ping' % node, timeout=5)
	    ret = ssh.expect(['ping', 'passphrase', 'password', pexpect.TIMEOUT, pexpect.EOF])
	    if ret > 0:
		m = 'Configured cluster node %s not reachable through ssh.\n' % node
		m += 'Please ensure that the current user can ssh to that node without a password.'
		raise SkipTest, m
	    ssh.close()
	    ssh = pexpect.spawn('ssh %s service corosync status' % node, timeout=5)
	    ret = ssh.expect(['running', 'stopped', pexpect.TIMEOUT, pexpect.EOF])
	    if ret > 0:
		m = 'Configured cluster node %s is not running corosync.\n' % node
		m += 'Please start corosync on this node.'
		raise SkipTest, m

    @classmethod
    def _copy_source_tree(cls):
	"""Copy the python-corosync source tree to the remote cluster
	nodes."""
	for node in cls.cluster_nodes():
	    ret = os.system('scp -q -r %s %s:' % (cls.topdir(), node))
	    if ret:
		m = 'Could not copy source tree to cluster node %s.' % node
		raise SkipTest, m

    def require(self, **kwargs):
	"""Require a condition or skip a test."""
	if kwargs.has_key('cluster'):
	    if not self.c_config.getboolean('test', 'cluster_tests'):
		raise SkipTest, 'Cluster tests not enabled.'
	if kwargs.has_key('nodes'):
	    nodes = self.c_config.get('test', 'cluster_nodes').split()
	    count = len(nodes) + 1
	    if kwargs['nodes'] > count:
		raise SkipTest, 'Not enough nodes for cluster test.'
    
    def start_on_cluster_nodes(self, test):
	"""Start `test' on all cluster nodes."""
	self.m_threads = []
	module = self.__module__
	cls = self.__class__.__name__
	method = test.__name__
	for node in self.cluster_nodes():
	    thread = RemoteTest(node, module, cls, method)
	    thread.start()
	    self.m_threads.append(thread)

    def remote_results(self):
	"""Return the results of the remote functions."""
	results = []
	for thread in self.m_threads:
	    thread.join()
	    results.append(thread.result())
	self.m_threads = []
	return results
