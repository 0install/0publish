#!/usr/bin/env python
import sys, os, tempfile, StringIO
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector.reader import InvalidInterface
from zeroinstall.injector import model, reader, qdom
import unittest
from xml.dom import minidom

sys.path.insert(0, '..')

import create, merge, release

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
	stream = StringIO.StringIO(xml)
	return model.ZeroInstallFeed(qdom.parse(stream))

local_file = os.path.join(os.path.dirname(__file__), 'local.xml')
local_file_req = os.path.join(os.path.dirname(__file__), 'local-req.xml')
local_file_if = os.path.join(os.path.dirname(__file__), 'local-if.xml')
local_file_command = os.path.join(os.path.dirname(__file__), 'local-command.xml')
local_file_zi13 = os.path.join(os.path.dirname(__file__), 'zeroinstall-injector-1.3.xml')

def tap(s):
	#print s
	return s

class TestLocal(unittest.TestCase):
	def testCreate(self):
		master = parse(create.create_from_local(local_file))
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 1
	
	def testMergeFirst(self):
		master = parse(merge.merge(header + footer, local_file))
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 1

	def testMergeSecond(self):
		master = parse(merge.merge(header + "<implementation id='sha1=123' version='1'/>" + footer, local_file))
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2

	def testMergeGroup(self):
		master = parse(merge.merge(header + "<group>\n    <implementation id='sha1=123' version='1'/>\n  </group>" + footer, local_file))
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		assert master.implementations['sha1=002'].requires == []

	def testMergeLocalReq(self):
		master = parse(tap(merge.merge(header + "<group x='x'>\n    <implementation id='sha1=123' version='1'/>\n  </group>" + footer, local_file_req)))
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		deps = master.implementations['sha1=003'].requires
		assert len(deps) == 1
		assert deps[0].interface == 'http://foo', deps[0]

		assert master.implementations['sha1=003'].metadata['http://mynamespace/foo bob'] == 'bob'

	def testNotSubset(self):
		master = parse(merge.merge(header + "<group a='a'>\n    <implementation id='sha1=123' version='1'/>\n  </group>" + footer, local_file))
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		assert master.implementations['sha1=123'].metadata.get('a', None) == 'a'
		assert master.implementations['sha1=002'].metadata.get('a', None) == None

		master = parse(merge.merge(header + """\n
  <group>
    <requires interface='http://foo' meta='foo'/>
    <implementation id='sha1=004' version='1'/>
  </group>
  <group>
    <requires interface='http://foo'>
      <version before='1'/>
    </requires>
    <implementation id='sha1=001' version='1'/>
  </group>""" + footer, local_file_req))
		assert len(master.implementations['sha1=001'].requires[0].restrictions) == 1
		assert len(master.implementations['sha1=003'].requires[0].restrictions) == 0

		assert master.implementations['sha1=004'].requires[0].metadata.get('meta', None) == 'foo'
		assert master.implementations['sha1=003'].requires[0].metadata.get('meta', None) == None

		assert master.implementations['sha1=003'].main == 'hello'

	def testMergeBest(self):
		master_xml = merge.merge(header + """\n
  <group>
    <implementation id='sha1=123' version='1'/>
  </group>
  <group>
    <requires interface='http://foo'/>
    <implementation id='sha1=002' version='2'/>
  </group>""" + footer, local_file_req)
		master = parse(master_xml)
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 3
		deps = master.implementations['sha1=003'].requires
		assert len(deps) == 1
		assert deps[0].interface == 'http://foo', deps[0]

		assert len(minidom.parseString(master_xml).documentElement.getElementsByTagNameNS(XMLNS_IFACE, 'group')) == 2
	
		# Again, but with the groups the other way around
		master_xml = merge.merge(header + """\n
  <group>
    <requires interface='http://foo'/>
    <implementation id='sha1=002' version='2'/>
  </group>
  <group>
    <implementation id='sha1=123' version='1'/>
  </group>""" + footer, local_file_req)
		master = parse(master_xml)
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 3
		deps = master.implementations['sha1=003'].requires
		assert len(deps) == 1
		assert deps[0].interface == 'http://foo', deps[0]

		assert len(minidom.parseString(master_xml).documentElement.getElementsByTagNameNS(XMLNS_IFACE, 'group')) == 2

	def testMergeCommand(self):
		# We create a new group inside this one, sharing the <requires> and adding the <command>
		master_xml = merge.merge(header + """
  <group>
    <requires interface='http://foo'>
      <environment name='TESTING' value='true' mode='replace'/>
    </requires>
    <implementation id='sha1=002' version='2'/>
  </group>""" + footer, local_file_command)
		master = parse(master_xml)
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		commands = master.implementations['sha1=003'].commands
		assert len(commands) == 1
		assert commands['run'].path == 'run.sh', commands['run'].path

		new_root = minidom.parseString(master_xml).documentElement
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'group')) == 2
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'requires')) == 1
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'command')) == 1
	
		# We create a new top-level group inside this one, as we can't share the test command
		master_xml = merge.merge(header + """
  <group>
    <requires interface='http://foo'>
      <environment name='TESTING' value='true' mode='replace'/>
    </requires>
    <command name='test' path='test.sh'/>
    <implementation id='sha1=002' version='2'/>
  </group>""" + footer, local_file_command)
		master = parse(master_xml)
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		commands = master.implementations['sha1=003'].commands
		assert len(commands) == 1
		assert commands['run'].path == 'run.sh', commands['run'].path

		new_root = minidom.parseString(master_xml).documentElement
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'group')) == 2
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'requires')) == 2
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'command')) == 2
	
		# We share the <requires> and override the <command>
		master_xml = merge.merge(header + """
  <group>
    <requires interface='http://foo'>
      <environment name='TESTING' value='true' mode='replace'/>
    </requires>
    <command name='run' path='old-run.sh'/>
    <implementation id='sha1=002' version='2'/>
  </group>""" + footer, local_file_command)
		master = parse(master_xml)
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		commands = master.implementations['sha1=003'].commands
		assert len(commands) == 1
		assert commands['run'].path == 'run.sh', commands['run'].path

		new_root = minidom.parseString(master_xml).documentElement
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'group')) == 2
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'requires')) == 1
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'command')) == 2

		# We share the <requires> and the <command>
		master_xml = merge.merge(header + """
  <group>
    <requires interface='http://foo'>
      <environment name='TESTING' value='true' mode='replace'/>
    </requires>
    <command name='run' path='run.sh'/>
    <implementation id='sha1=002' version='2'/>
  </group>""" + footer, local_file_command)
		master = parse(master_xml)
		assert master.url == 'http://test/hello.xml', master
		assert len(master.implementations) == 2
		commands = master.implementations['sha1=003'].commands
		assert len(commands) == 1
		assert commands['run'].path == 'run.sh', commands['run'].path

		new_root = minidom.parseString(master_xml).documentElement
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'group')) == 1
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'requires')) == 1
		assert len(new_root.getElementsByTagNameNS(XMLNS_IFACE, 'command')) == 1
	
	def testMerge2(self):
		master_xml = merge.merge(header + """
  <group license="OSI Approved :: GNU Lesser General Public License (LGPL)" main="0launch">
    <command name="run" path="0launch">
      <runner interface="http://repo.roscidus.com/python/python">
	<version before="3"/>
      </runner>
    </command>

    <group>
      <command name="run" path="0launch"/>
      <implementation id="sha1new=7d1ecfbd76a42d56f029f9d0c72e4ac26c8561de" released="2011-07-23" version="1.2"/>
    </group>
  </group>
  """ + footer, local_file_zi13)
		doc = minidom.parseString(master_xml)

		n_groups = len(doc.getElementsByTagName("group"))
		assert n_groups == 2
	
	def testMergeIf0installVersion(self):
		master_xml = merge.merge(header + """
  <group>
    <command name='run' path='run.sh'/>
    <implementation id="sha1=003" version="0.4"/>
  </group>
  """ + footer, local_file_if)
		doc = minidom.parseString(master_xml)

		n_commands = len(doc.getElementsByTagName("command"))
		assert n_commands == 3

		# We can share the run-old.sh <command>
		master_xml = merge.merge(header + """
  <group>
    <command name='run' path='run-old.sh' if-0install-version='..!2'/>
    <command name='run' path='run-mid.sh' if-0install-version='2..'/>
    <implementation id="sha1=003" version="0.4"/>
  </group>
  """ + footer, local_file_if)
		doc = minidom.parseString(master_xml)

		n_commands = len(doc.getElementsByTagName("command"))
		assert n_commands == 3

	def testLocalContext(self):
		def get_context(xml_frag):
			doc = minidom.parseString(header + xml_frag + footer)
			impls = list(doc.getElementsByTagNameNS(XMLNS_IFACE, 'implementation'))
			assert len(impls) == 1
			return merge.Context(impls[0])

		ctx = get_context("<implementation id='sha1=001' version='1'/>")
		assert ctx.attribs[(None, 'id')] == 'sha1=001'
		assert ctx.attribs[(None, 'version')] == '1'

		ctx = get_context("<group t='t' x='1' y:z='2' xmlns:y='yns'><implementation id='sha1=001' version='1' t='r'/></group>")
		assert ctx.attribs[(None, 'id')] == 'sha1=001'
		assert ctx.attribs[(None, 'version')] == '1'
		assert ctx.attribs[(None, 't')] == 'r'
		assert ctx.attribs[(None, 'x')] == '1'
		assert ctx.attribs[('yns', 'z')] == '2'

	def testSetAtttibs(self):
		local_data = open(local_file).read()
		result = release.set_attributes(local_data, '0.2', id = 'sha1=98765', version='3.7', main = None)
		feed = model.ZeroInstallFeed(qdom.parse(StringIO.StringIO(str(result))), "local.xml")
		assert len(feed.implementations) == 1
		assert feed.implementations['sha1=98765'].get_version() == '3.7'

		try:
			result = release.set_attributes(local_data, '0.3', id = 'sha1=98765', version='3.7', main = None)
			assert 0
		except Exception, ex:
			assert str(ex) == 'No implementations with version=0.3'

suite = unittest.makeSuite(TestLocal)
if __name__ == '__main__':
	unittest.main()
