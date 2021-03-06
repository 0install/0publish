from xml.dom import minidom
from zeroinstall.injector import namespaces
from zeroinstall.zerostore import manifest, Stores, NotStored
import xmltools
from logging import info

stores = Stores()

def digests(impl):
	id = impl.getAttribute('id')
	if '=' in id:
		yield id.split('=', 1)
	for x in xmltools.children(impl, 'manifest-digest'):
		for name, value in x.attributes.itemsNS():
			if name[0] is None:
				yield name[1], value

def get_version(impl):
	while impl:
		v = impl.getAttribute('version')
		if v: return v
		impl = impl.parentNode

def add_digest(impl, alg_name):
	alg = manifest.get_algorithm(alg_name)
	
	# Scan through the existing digests
	# - If we've already got the one we need, return
	# - Otherwise, find a cached implementation we can use
	existing_path = None
	for a, value in digests(impl):
		if a in ('sha1', 'sha1new', 'sha256'):
			digest = '%s=%s' % (a, value)
		else:
			digest = '%s_%s' % (a, value)
		if a == alg_name:
			return False			# Already signed with this algorithm
		if not existing_path:
			try:
				existing_path = stores.lookup(digest)
				if existing_path:
					existing_digest = digest
			except NotStored:
				pass		# OK

	if existing_path is None:
		print("No implementations of %s cached; can't calculate new digest" % get_version(impl))
		return False

	info("Verifying %s", existing_path)
	manifest.verify(existing_path, existing_digest)

	print("Adding new digest to version %s" % get_version(impl))

	new_digest = alg.new_digest()
	for line in alg.generate_manifest(existing_path):
		new_digest.update((line + '\n').encode())

	for md in xmltools.children(impl, 'manifest-digest'):
		break
	else:
		md = xmltools.create_element(impl, 'manifest-digest')
	_, digest_value = manifest.splitID(alg.getID(new_digest))
	md.setAttribute(alg_name, digest_value)

	return True

def add_digests(data, alg = None):
	doc = minidom.parseString(data)

	if alg is None:
		alg = 'sha1new'
	
	changed = False
	for impl in doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation'):
		if impl.getAttribute('id') in "./":
			continue		# Local implementation

		if add_digest(impl, alg):
			changed = True

	if changed:
		return doc.toxml('utf-8')
	else:
		return data
