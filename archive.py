from xml.dom import minidom
from zeroinstall import SafeException
from zeroinstall.zerostore import manifest
try:
	from zeroinstall.zerostore import unpack
except ImportError:
	# Older versions don't have it
	import unpack
from zeroinstall.injector import namespaces
import os, shutil, tempfile

import digest
import xmltools

def ro_rmtree(root):
	"""Like shutil.rmtree, except that we also delete with read-only items.
	@param root: the root of the subtree to remove
	@type root: str
	@since: 0.28"""
	for main, dirs, files in os.walk(root):
		os.chmod(main, 0700)
	shutil.rmtree(root)

def manifest_for_dir(dir, alg):
	if alg == 'sha1':
		# (for older versions of the injector)
		import sha
		class SHA1:
			def new_digest(self): return sha.new()
			def generate_manifest(self, dir): return manifest.generate_manifest(dir)
			def getID(self, digest): return 'sha1=' + digest.hexdigest()
		algorithm = SHA1()
	else:
		algorithm = manifest.get_algorithm(alg)

	digest = algorithm.new_digest()
	for line in algorithm.generate_manifest(dir):
		digest.update(line + '\n')
	return algorithm.getID(digest)

def autopackage_get_start_offset(package):
	for line in file(package):
		if line.startswith('export dataSize=') or line.startswith('export data_size='):
			return os.path.getsize(package) - int(line.split('"', 2)[1])
	raise Exception("Can't find payload in autopackage (missing 'dataSize')")

def add_archive(data, url, local_file, extract, algs):
	if local_file is None:
		local_file = os.path.abspath(os.path.basename(url))
		if not os.path.exists(local_file):
			raise SafeException("Use --archive-file option to specify a local copy of the archive "
					"(default file '%s' does not exist)" % local_file)

	doc = minidom.parseString(data)

	assert algs

	if local_file.endswith('.package'):
		start_offset = autopackage_get_start_offset(local_file)
		type = 'application/x-bzip-compressed-tar'
	else:
		start_offset = 0
		type = None

	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	tmpdir = tempfile.mkdtemp('-0publish')
	try:
		if start_offset or type:
			unpack.unpack_archive(url, file(local_file), tmpdir, extract, start_offset = start_offset, type = type)
		else:
			unpack.unpack_archive(url, file(local_file), tmpdir, extract)
		if extract:
			extracted = os.path.join(tmpdir, extract)
		else:
			extracted = tmpdir

		archive_id = manifest_for_dir(extracted, algs[0])
		extra_digests = set([manifest_for_dir(extracted, a) for a in algs[1:]])
	finally:
		ro_rmtree(tmpdir)

	local_ifaces = []
	for impl in all_impls:
		this_id = impl.getAttribute('id')
		if this_id == archive_id:
			break
		if this_id.startswith('/') or this_id.startswith('.'):
			local_ifaces.append(impl)
	else:
		if len(local_ifaces) == 0:
			raise Exception('Nothing with id "%s", and no local implementations' % archive_id)
		if len(local_ifaces) > 1:
			raise Exception('Nothing with id "%s", and multiple local implementations!' % archive_id)
		impl = local_ifaces[0]
		impl.setAttribute('id', archive_id)
	
	assert impl.getAttribute('id') == archive_id

	archive = xmltools.create_element(impl, 'archive')
	archive.setAttribute('href', url)
	archive.setAttribute('size', str(os.stat(local_file).st_size - start_offset))
	if extract is not None:
		archive.setAttribute('extract', extract)
	if start_offset:
		archive.setAttribute('start-offset', str(start_offset))
	if type:
		archive.setAttribute('type', type)

	# Remove digests we already
	for x in xmltools.children(impl, 'manifest-digest'):
		digest_element = x
		break
	else:
		digest_element = doc.createElementNS(namespaces.XMLNS_IFACE, 'manifest-digest')
		xmltools.insert_before(digest_element, archive)
	for x in extra_digests - set([digest.digests(impl)]):
		name, value = x.split('=')
		digest_element.setAttribute(name, value)

	return doc.toxml('utf-8')
