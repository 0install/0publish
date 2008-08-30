from xml.dom import minidom
from zeroinstall.injector import namespaces
from logging import warn

def mark_stable(data):
	"""Find the single release marked as 'testing' and make it 'stable'."""
	doc = minidom.parseString(data)
	testing = []
	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	for x in all_impls:
		if get_stability(x) == 'testing':
			testing.append(x)
	if len(testing) == 0:
		raise Exception('No implementations are currently "testing"!')
	impl = testing[-1]
	if len(testing) > 1:
		warn("Multiple 'testing' implementations - changing last one (%s)", impl.getAttribute('version'))
	
	impl.setAttribute('stability', 'stable')
	
	return doc.toxml()

def get_stability(x):
	root = x.ownerDocument.documentElement
	while x is not root:
		stab = x.getAttribute('stability')
		if stab: return stab
		x = x.parentNode
	return 'testing'
