from xml.dom import minidom
from zeroinstall.injector import namespaces

def add_sizes(data, feed):
	'''add missing sizes to archives'''
	doc = minidom.parseString(data)

	archive_sizes = {}
	for archive in feed.archives:
		archive_sizes[archive.url] = archive.size

	xml_archives = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'archive')
	for xml_archive in xml_archives:
		xml_archive.setAttribute('size', str(archive_sizes[xml_archive.getAttribute('href')]))

	return doc.toxml()

