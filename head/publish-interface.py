#!/usr/bin/env python
from xml.dom import minidom, Node
import sys, os
import shutil
import time

XMLNS_IFACE = 'http://zero-install.sourceforge.net/2004/injector/interface'

if len(sys.argv) != 3:
	print >>sys.stderr, "Usage: %s interface.xml key\n" \
		"- interface.xml will be updated with missing details, etc.\n" \
		"- interface.xml.asc (signed interface) is created.\n" \
		"\nUpload the signed interface to your webserver." % sys.argv[0]
	sys.exit(1)

interface = sys.argv[1]
key = sys.argv[2]

shutil.copy(interface, interface + '.bak')
doc = minidom.parse(interface)

root = doc.documentElement
assert root.namespaceURI == XMLNS_IFACE
assert root.localName == 'interface'

root.setAttribute('last-modified', str(long(time.time())))

def update_impls(node):
	print node
	if node.namespaceURI != XMLNS_IFACE:
		return
	if node.localName == 'implementation':
		href = node.getAttribute('href')
		print "href:", href
	for x in node.childNodes:
		if x.nodeType == Node.ELEMENT_NODE:
			update_impls(x)
update_impls(root)

doc.writexml(file(interface, 'w'))

print "Changes:"
os.spawnvp(os.P_WAIT, 'diff', ('diff', '-u', '--', interface + '.bak', interface))

print "Signing..."
os.spawnvp(os.P_WAIT, 'gpg', ('gpg',
			      '--default-key', key,
			      '--yes',
			      '--clearsign', interface))
