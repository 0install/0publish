#!/usr/bin/env python2.4
import sys, logging, os, tempfile
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector.reader import InvalidInterface
from zeroinstall.injector import model, reader
import unittest
from xml.dom import minidom

sys.path.insert(0, '..')

import create, merge

header = """<?xml version="1.0" ?>
<interface xmlns="http://zero-install.sourceforge.net/2004/injector/interface"
	   uri='http://test/hello.xml'>
  <name>test</name>
  <summary>for testing</summary>
  <description>This is for testing.</description>
"""
footer = """
</interface>
"""

def parse(xml):
	dom = minidom.parseString(xml)
	uri = dom.documentElement.getAttribute('uri')
	assert uri

	tmp = tempfile.NamedTemporaryFile(prefix = 'test-')
	try:
		tmp.write(xml)
		tmp.flush()
		iface = model.Interface(uri)
		reader.update(iface, tmp.name, local = True)
		return iface
	finally:
		tmp.close()

local_file = os.path.join(os.path.dirname(__file__), 'local.xml')
local_file_req = os.path.join(os.path.dirname(__file__), 'local-req.xml')

def tap(s):
	#print s
	return s

class TestValidator(unittest.TestCase):
	def testCreate(self):
		master = parse(create.create_from_local(local_file))
		assert master.uri == 'http://test/hello.xml', master
		assert len(master.implementations) == 1
	
	def testMergeFirst(self):
		master = parse(merge.merge(header + footer, local_file))
		assert master.uri == 'http://test/hello.xml', master
		assert len(master.implementations) == 1

	def testMergeSecond(self):
		master = parse(merge.merge(header + "<implementation id='sha1=123' version='1'/>" + footer, local_file))
		assert master.uri == 'http://test/hello.xml', master
		assert len(master.implementations) == 2

	def testMergeGroup(self):
		master = parse(tap(merge.merge(header + "<group><implementation id='sha1=123' version='1'/></group>" + footer, local_file)))
		assert master.uri == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		assert master.implementations['sha1=002'].requires == []

	def testMergeLocalReq(self):
		master = parse(tap(merge.merge(header + "<group x='x'><implementation id='sha1=123' version='1'/></group>" + footer, local_file_req)))
		assert master.uri == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		deps = master.implementations['sha1=003'].requires
		assert len(deps) == 1
		#assert deps[0].interface == 'http://foo', deps[0]
	
	def testLocalContext(self):
		def get_context(xml_frag):
			doc = minidom.parseString(header + xml_frag + footer)
			impls = list(doc.getElementsByTagNameNS(XMLNS_IFACE, 'implementation'))
			assert len(impls) == 1
			return merge.Context(impls[0])

		ctx = get_context("<implementation id='sha1=001' version='1'/>")
		assert ctx.attribs[(None, 'id')] == 'sha1=001'
		assert ctx.attribs[(None, 'version')] == '1'

		ctx = get_context("<group t='t' x='1' y:z='2' xmlns:y='foo'><implementation id='sha1=001' version='1' t='r'/></group>")
		assert ctx.attribs[(None, 'id')] == 'sha1=001'
		assert ctx.attribs[(None, 'version')] == '1'
		assert ctx.attribs[(None, 't')] == 'r'
		assert ctx.attribs[(None, 'x')] == '1'
		assert ctx.attribs[('foo', 'z')] == '2'

suite = unittest.makeSuite(TestValidator)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
