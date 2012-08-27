import os, io, StringIO
from zeroinstall.injector import model, namespaces, qdom
from zeroinstall.injector.reader import InvalidInterface, update
from xml.dom import minidom, Node, XMLNS_NAMESPACE
import tempfile
from logging import warn, info

group_impl_attribs = ['version', 'version-modifier', 'released', 'main', 'stability', 'arch', 'license', 'doc-dir', 'self-test', 'langs', 'local-path']

known_elements = {
	'interface' : ['uri', 'min-injector-version', 'main'],	# (main is deprecated)
	'name' : [],
	'summary' : [],
	'description' : [],
	'needs-terminal' : [],
	'homepage' : [],
	'category' : ['type'],
	'icon' : ['type', 'href'],
	'feed' : ['src', 'arch'],
	'feed-for' : ['interface'],
	'replaced-by' : ['interface'],

	'group' : group_impl_attribs,
	'implementation' : ['id'] + group_impl_attribs,
	'package-implementation' : ['package', 'main', 'distributions'],
	'manifest-digest' : ['sha1new', 'sha256', 'sha256new'],
	'command' : ['name', 'path', 'shell-command'],
	'arg' : [],

	'archive' : ['href', 'size', 'extract', 'type', 'start-offset'],
	'recipe' : [],
	'requires' : ['interface', 'use', 'importance'],
	'runner' : ['interface', 'use', 'importance', 'command'],
	'version' : ['not-before', 'before'],
	'environment' : ['name', 'insert', 'value', 'default', 'mode'],
	'executable-in-var' : ['name', 'command'],
	'executable-in-path' : ['name', 'command'],
	#'overlay' : ['src', 'mount-point'],
}

known_distros = frozenset([
	"Windows", "Darwin", "Debian", "RPM", "Slack",
	"Arch", "Gentoo", "Ports", "MacPorts", "Cygwin"
])

def checkElement(elem):
	if elem.namespaceURI != namespaces.XMLNS_IFACE:
		info("Note: Skipping unknown (but namespaced) element <%s>", elem.localName)
		return	# Namespaces elements are OK

	if elem.localName not in known_elements:
		warn("Unknown Zero Install element <%s>.\nNon Zero-Install elements should be namespaced.", elem.localName)
		return
	
	known_attrs = known_elements[elem.localName]

	for (uri, name), value in elem.attributes.itemsNS():
		if uri == XMLNS_NAMESPACE:
			continue	# Namespace declarations are fine

		if uri:
			info("Note: Skipping unknown (but namespaced) attribute '%s'", name)
			continue

		if name not in known_attrs:
			warn("Unknown Zero Install attribute '%s' on <%s>.\nNon Zero-Install attributes should be namespaced.",
					name, elem.localName)

		if name == 'distributions':
			if ',' in value:
				warn("Use ' ' to separate distribution names, not ',' (%s)", value)
			else:
				for distro in value.split(' '):
					if distro not in known_distros:
						warn("Unknown distribution name '%s' (expected one of %s)", distro, '|'.join(known_distros))
		
	for child in elem.childNodes:
		if child.nodeType == Node.ELEMENT_NODE:
			checkElement(child)

def check(data, warnings = True):
	assert type(data) == bytes, type(data)	# (must not be unicode)

	try:
		doc = minidom.parseString(data)
		if doc.documentElement.getAttribute('uri'):
			local_path = None
		else:
			local_path = '/tmp/local.xml'
		model.ZeroInstallFeed(qdom.parse(StringIO.StringIO(data)), local_path = local_path)
	except InvalidInterface, ex:
		raise
	except Exception, ex:
		warn("Internal error: %s", ex)
		raise InvalidInterface(str(ex))
	
	if warnings:
		checkElement(doc.documentElement)
