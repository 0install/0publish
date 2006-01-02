from xml.dom import minidom
from zeroinstall.injector import namespaces, model
import time, re

date_format = '\d{4}-\d{2}-\d{2}'

def make_release(data):
	"""Normally there's only one implementation, but we can cope with several."""
	doc = minidom.parseString(data)
	unreleased = []
	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	for x in all_impls:
		released = x.getAttribute('released')
		if released is None or not re.match(date_format, released):
			unreleased.append((None, x))
	if not unreleased:
		if len(all_impls) == 0:
			raise Exception('No implementations in interface file!')
		if len(all_impls) > 1:
			raise Exception("Multiple implementations, but all are released. Aborting.")
		impl = all_impls[0]
		unreleased.append((impl.getAttribute('released'), impl))
	
	for released, x in unreleased:
		id = x.getAttribute('id')
		version = x.getAttribute('version')
		stability = x.getAttribute('stability')
		print "Implementation '%s' (version: %s  released: %s  stability: %s)" % \
				(id, version, x.getAttribute('released'), stability)
		new_version = raw_input('Version [%s]: ' % version)
		if new_version:
			version = new_version
		if not released:
			released = time.strftime('%Y-%m-%d')
		while True:
			new_released = raw_input('Released [%s]: ' % released)
			if not new_released:
				break
			if re.match(date_format, new_released):
				released = new_released
				break
			print "Invalid date format. Use YYYY-MM-DD."

		while True:
			new_stability = raw_input('Stability [testing]: ').lower()
			if not new_stability:
				new_stability = model.testing.name
			for level in model.stability_levels:
				if level.startswith(new_stability):
					stability = level
					break
			else:
				print "Invalid level '%s'" % new_stability
				print "Choose one of", ', '.join(model.stability_levels.keys())
				continue
			break

		x.setAttribute('version', version)
		x.setAttribute('released', released)
		x.setAttribute('stability', stability)
	
	return doc.toxml()
