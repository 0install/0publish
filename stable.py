from xml.dom import minidom
from zeroinstall.injector import namespaces, model
from logging import warn

def mark_stable(data):
	"""Find the single release marked as 'testing' and make it 'stable'."""
	doc = minidom.parseString(data)
	testing = []
	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	for x in all_impls:
		if get_stability(x) == 'testing':
			testing.append((get_version(x), x))
	if len(testing) == 0:
		raise Exception('No implementations are currently "testing"!')

	testing = sorted(testing)
	higest_version = testing[-1][0]
	latest_testing = [impl for version, impl in testing if version == higest_version]

	if len(latest_testing) < len(testing):
		warn("Multiple 'testing' versions - changing %d (of %d) with version %s", len(latest_testing), len(testing), model.format_version(higest_version))
	
	for impl in latest_testing:
		impl.setAttribute('stability', 'stable')
	
	return doc.toxml('utf-8')

def get_stability(x):
	root = x.ownerDocument.documentElement
	while x is not root:
		stab = x.getAttribute('stability')
		if stab: return stab
		x = x.parentNode
	return 'testing'

def get_version(x):
	root = x.ownerDocument.documentElement
	while x is not root:
		version = x.getAttribute('version')
		if version:
			mod = x.getAttribute('version-modifier')
			if mod: version += mod
			return model.parse_version(version)
		x = x.parentNode
	raise Exception("No version on %s" % x)
