from xml.dom import minidom
from zeroinstall.zerostore import Store, manifest, unpack
from zeroinstall.injector import namespaces
import os, time, re, shutil, tempfile, sha

def manifest_for_dir(dir, alg):
	algorithm = manifest.get_algorithm(alg)
	digest = algorithm.new_digest()
	for line in algorithm.generate_manifest(dir):
		digest.update(line + '\n')
	return algorithm.getID(digest)

def add_archive(data, url, local_file, extract):
	if local_file is None:
		raise Exception('Use --archive-file option to specify a local copy')

	doc = minidom.parseString(data)

	if local_file.endswith('.deb'):
		# Debs require 0launch >= 0.20 anyway, so use the new hash to avoid
		# problems with directory mtimes
		alg = 'sha1new'
	else:
		alg = 'sha1'

	all_impls = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'implementation')
	tmpdir = tempfile.mkdtemp('-0publish')
	try:
		unpack.unpack_archive(url, file(local_file), tmpdir, extract)
		if extract:
			extracted = os.path.join(tmpdir, extract)
		else:
			extracted = tmpdir

		archive_id = manifest_for_dir(extracted, alg)
	finally:
		shutil.rmtree(tmpdir)

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

	nl = doc.createTextNode('\n      ')
	impl.appendChild(nl)

	archive = doc.createElementNS(namespaces.XMLNS_IFACE, 'archive')
	impl.appendChild(archive)
	archive.setAttribute('href', url)
	archive.setAttribute('size', str(os.stat(local_file).st_size))
	if extract is not None:
		archive.setAttribute('extract', extract)

	nl = doc.createTextNode('\n    ')
	impl.appendChild(nl)

	return doc.toxml()
