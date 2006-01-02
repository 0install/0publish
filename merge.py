import os
from xml.dom import minidom, XMLNS_NAMESPACE
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector import model, reader

def merge(data, local):
	local_doc = minidom.parse(local)
	master_doc = minidom.parseString(data)

	for impl in local_doc.getElementsByTagNameNS(XMLNS_IFACE, 'implementation'):
		new_impl = master_doc.importNode(impl, True)
		while impl.parentNode is not local_doc:
			impl = impl.parentNode
			for attr in ['stability', 'released', 'main', 'arch', 'version']:
				if impl.hasAttribute(attr) and not new_impl.hasAttribute(attr):
					new_impl.setAttribute(attr, impl.getAttribute(attr))

		master_doc.documentElement.appendChild(master_doc.createTextNode('  '))
		master_doc.documentElement.appendChild(new_impl)
		master_doc.documentElement.appendChild(master_doc.createTextNode('\n'))
		print "Impl", new_impl

	# minidom's writer loses the newline after the PI
	return master_doc.toxml()
