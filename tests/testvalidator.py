#!/usr/bin/env python
import sys, logging
from io import StringIO
from zeroinstall.injector.reader import InvalidInterface
import unittest

sys.path.insert(0, '..')

import validator

header = """<?xml version="1.0" ?>
<?xml-stylesheet type='text/xsl' href='http://0install.net/2006/stylesheets/interface.xsl'?>
<interface xmlns="http://zero-install.sourceforge.net/2004/injector/interface">
  <name>test</name>
  <summary>for testing</summary>
  <description>
    This is for testing.
  </description>
  <homepage>http://0install.net</homepage>
  <feed-for interface='http://0install.net/2007/tests/just-testing.xml'/>"""
footer = """
</interface>
"""

root_logger = logging.getLogger()

def check(xml, expectWarnings = ""):
	my_log_stream = StringIO()
	my_handler = logging.StreamHandler(my_log_stream)

	root_logger.handlers = []

	root_logger.addHandler(my_handler)
	old_stderr = sys.stderr
	try:
		sys.stderr = my_log_stream
		validator.check(xml)
		warnings = my_log_stream.getvalue()
	finally:
		sys.stderr = old_stderr
		root_logger.removeHandler(my_handler)
	if expectWarnings:
		assert expectWarnings in warnings, "Expected warning '%s' not in '%s'" % (expectWarnings, warnings)
	elif warnings:
		raise Exception("Unexpected warnings '%s'" % warnings)

class TestValidator(unittest.TestCase):
	def testSimple(self):
		check(header + footer)

	def testWarnings(self):
		check(header + "<foo/>" + footer, expectWarnings = "Unknown Zero Install element <foo>")
		check(header + "<foo:bar xmlns:foo='http://foo'/>" + footer)
		check(header + "<group foo='bar'/>" + footer, expectWarnings = "Non Zero-Install attributes should be namespaced")
	
	def testInvalid(self):
		try:
			check(header)
		except InvalidInterface as ex:
			assert "no element found" in str(ex), ex

		try:
			check(header + "<implementation/>" + footer)
		except InvalidInterface as ex:
			assert "Missing 'id' attribute" in str(ex), ex

suite = unittest.makeSuite(TestValidator)
if __name__ == '__main__':
	sys.argv.append('-v')
	unittest.main()
