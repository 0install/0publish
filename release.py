from xml.dom import minidom, Node
from zeroinstall.injector import namespaces
import time, re

date_format = '\d{4}-\d{2}-\d{2}'

def set_interface_uri(data, uri):
	"""Set the uri attribute on the root element."""
	doc = minidom.parseString(data)
	doc.documentElement.setAttribute('uri', uri)
	return doc.toxml('utf-8')

def add_version(data, version):
	"""Create a new <implementation> after the last one in the file."""
	doc = minidom.parseString(data)
	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	new_impl = doc.createElementNS(namespaces.XMLNS_IFACE, 'implementation')
	new_impl.setAttribute('version', version)
	new_impl.setAttribute('id', '.')

	if not all_impls:
		print('No existing <implementation> elements found; creating first one!')
		next = None
		last_impl = doc.documentElement.childNodes[-1]
	else:
		last_impl = all_impls[-1]
	previous = last_impl.previousSibling
	next = last_impl.nextSibling
	parent = last_impl.parentNode
	if previous and previous.nodeType == Node.TEXT_NODE:
		parent.insertBefore(doc.createTextNode(previous.nodeValue), next)
	parent.insertBefore(new_impl, next)
	return doc.toxml('utf-8')

def set_attributes(data, selected_version, id = None, version = None, released = None, stability = None, main = None, arch = None):
	"""Normally there's only one implementation, but we can cope with several."""
	if released == 'today': released = time.strftime('%Y-%m-%d')
	if released and released != 'Snapshot' and not re.match(date_format, released):
		raise Exception('Invalid date format. Use YYYY-MM-DD.')

	doc = minidom.parseString(data)
	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')

	if selected_version == None:
		# Select the version with no "released" attribute
		unreleased = None
		for x in all_impls:
			_released = x.getAttribute('released')
			if released is None or not re.match(date_format, _released):
				if unreleased:
					raise Exception('Multiple unreleased implementations!')
				unreleased = x
		if unreleased is None:
			if len(all_impls) == 0:
				raise Exception('No implementations in feed file!')
			if len(all_impls) > 1:
				raise Exception("Multiple implementations, but all are released. Aborting.")
			unreleased = all_impls[0]
		versions_to_change = [unreleased]
	else:
		# Select the version the user asked for
		versions_to_change = []
		for x in all_impls:
			node = x
			while True:
				_version = node.getAttribute('version')
				if _version is not None: break
				node = node.getParentNode()
				assert node.localName == 'group'
			if _version == selected_version:
				versions_to_change.append(x)
		if not versions_to_change:
			if len(all_impls) == 0:
				raise Exception('No implementations in feed file!')
			raise Exception("No implementations with version=%s" % selected_version)
	
	# In future, we may want to bulk change implementations...
	for x in versions_to_change:
		if id is not None: x.setAttribute('id', id)
		if released is not None:
			if released:
				x.setAttribute('released', released)
			elif x.hasAttribute('released'):
				x.removeAttribute('released')
		if stability is not None: x.setAttribute('stability', stability)
		if main is not None: x.setAttribute('main', main)
		if arch is not None: x.setAttribute('arch', arch)
		if version is not None:
			x.setAttribute('version', version)
		if x.hasAttribute('version-modifier'):
			x.removeAttribute('version-modifier')
	
	return doc.toxml('utf-8')
