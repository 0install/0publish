import os
from xml.dom import minidom, XMLNS_NAMESPACE
from zeroinstall.injector.namespaces import XMLNS_IFACE

def create(f):
	assert not os.path.exists(f)
	name = os.path.basename(f)
	
	impl = minidom.getDOMImplementation()
	doc = impl.createDocument(XMLNS_IFACE, 'interface', None)

	def text(name, value):
		e = doc.createElementNS(XMLNS_IFACE, name)
		e.appendChild(doc.createTextNode(value))
		return e

	root = doc.documentElement
	root.setAttributeNS(XMLNS_NAMESPACE, 'xmlns', XMLNS_IFACE)
	root.setAttribute('uri', "http://SITE/interfaces/%s" % name)

	root.appendChild(doc.createComment(
		" Set the uri attribute above to a location from which\n"
		"      this file can be downloaded. Try to choose a\n"
		"      location that won't change! "))

	root.appendChild(text("name", name))
	root.appendChild(text("summary", 'a brief one-line summary'))
	root.appendChild(text("description",
		"A longer, multi-line description of the behaviour of the\n"
		"program goes here. State clearly what the program is for\n"
		"(clearly enough that people who don't want it will\n"
		"realise too)."))
	
	group = doc.createElementNS(XMLNS_IFACE, 'group')
	root.appendChild(group)

	group.appendChild(doc.createComment(
		' Add dependencies and implementations here. '))
	
	doc.writexml(file(f, 'w'), addindent = " ", newl = '\n')

	print "Wrote '%s'." % f
	print "Now edit it in a text editor, and set the uri, summary "
	print "and description as indicated. When you're ready to add an "
	print "implementation, run 0publish on the file again."
