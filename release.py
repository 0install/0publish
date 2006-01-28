from xml.dom import minidom
from zeroinstall.injector import namespaces, model
import time, re

date_format = '\d{4}-\d{2}-\d{2}'

def make_release(data, id, version, released, stability):
	"""Normally there's only one implementation, but we can cope with several."""
	if released and released != 'Snapshot' and not re.match(date_format, released):
		raise Exception('Invalid date format. Use YYYY-MM-DD.')

	doc = minidom.parseString(data)
	unreleased = None
	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	for x in all_impls:
		_released = x.getAttribute('released')
		if released is None or not re.match(date_format, _released):
			if unreleased:
				raise Exception('Multiple unreleased implementations!')
			unreleased = x
	if unreleased is None:
		if len(all_impls) == 0:
			raise Exception('No implementations in interface file!')
		if len(all_impls) > 1:
			raise Exception("Multiple implementations, but all are released. Aborting.")
		unreleased = all_impls[0]
	
	# In future, we may want to bulk change implementations...
	for x in [unreleased]:
		if id is not None: x.setAttribute('id', id)
		if version is not None: x.setAttribute('version', version)
		if released is not None: x.setAttribute('released', released)
		if stability is not None: x.setAttribute('stability', stability)
	
	return doc.toxml()
