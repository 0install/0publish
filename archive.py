from xml.dom import minidom
from zeroinstall.injector.download import Download
from zeroinstall.support import tasks
from zeroinstall.injector import namespaces

def add_sizes(data):
	'''add missing sizes to archives'''
	doc = minidom.parseString(data)
	archives = doc.documentElement.getElementsByTagNameNS(namespaces.XMLNS_IFACE, 'archive')

	to_change = [(archive, Download(archive.getAttribute('href')))  
	      		for archive in archives 
		       	if archive.getAttribute('size') is None or archive.getAttribute('size') == '']

	for archive, download in to_change:
		download.start()

	blockers = [download.downloaded for archive, download in to_change]

	@tasks.async
	def add_sizes_():
		for archive, download in to_change:
			while not download.downloaded.happened:
				yield blockers
				tasks.check(blockers)
			size = download.get_bytes_downloaded_so_far()
			archive.setAttribute('size', str(size))

	tasks.wait_for_blocker(add_sizes_())
	return doc.toxml()

