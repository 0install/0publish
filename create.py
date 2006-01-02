import os
from xml.dom import minidom, XMLNS_NAMESPACE
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector import model, reader

_local_template_start = """<?xml version="1.0" ?>
<?xml-stylesheet type='text/xsl'
     href='http://0install.net/2006/stylesheets/interface.xsl'?>
"""

_template = """<?xml version="1.0" ?>
<?xml-stylesheet type='text/xsl'
     href='http://0install.net/2006/stylesheets/interface.xsl'?>

<interface xmlns="http://zero-install.sourceforge.net/2004/injector/interface">
  <name>%s</name>
  <summary>cures all ills</summary>
  <description>
    A longer, multi-line description of the behaviour of the
    program goes here. State clearly what the program is for
    (clearly enough that people who don't want it will
    realise too).

    Use a blank line to separate paragraphs.
  </description>

  <!-- Optionally, uncomment this to specify an icon: -->
  <!-- <icon href='http://site/icon.png' type='image/png'/> -->

  <!-- Optionally, uncomment this to give the address of
       the signed master interface: -->
  <!-- <feed-for interface='http://site/interface'/> -->

  <!-- Set 'main' to the relative path of your default
        executable within the implementation's directory.
	E.g.: "myprog" or "bin/myprog" -->
  <group main='myprog'>
    <!-- List any libraries your program needs here -->
    <!--
    <requires interface="http://site/library">
      <environment insert="python" name="PYTHONPATH"/>
    </requires>
    -->

    <!-- List all implementations here.
         For local interfaces, '.' is a relative path from this
	 interface file to the directory containing the program.
	 Usually, you can just leave it as '.'.
    -->
    <implementation id="." version="0.1" released='Snapshot'/>
  </group>
</interface>
"""

def create(f):
	assert not os.path.exists(f)
	name = os.path.basename(f)
	return _template % (name.split('.', 1)[0])

def create_from_local(local):
	iface = model.Interface(os.path.abspath(local))
	reader.update(iface, local, local = True)
	doc = minidom.parseString(_local_template_start +
		'<interface xmlns="http://zero-install.sourceforge.net/2004/injector/interface"/>')
	root = doc.documentElement
	def element(uri, localName, data):
		root.appendChild(doc.createTextNode('\n  '))
		element = doc.createElementNS(uri, localName)
		element.appendChild(doc.createTextNode(data))
		return element
	root.appendChild(element(XMLNS_IFACE, 'name', iface.name))
	root.appendChild(element(XMLNS_IFACE, 'summary', iface.summary))
	root.appendChild(element(XMLNS_IFACE, 'description', iface.description + '\n  '))

	if not iface.feed_for:
		raise Exception("No <feed-for> in '%s'; can't use it as a local feed." % local)
	if len(iface.feed_for) != 1:
		raise Exception("Multiple <feed-for> elements. Not supported, sorry!")
	uri = iface.feed_for.keys()[0]

	root.setAttribute('uri', uri)

	local_doc = minidom.parse(local)
	for icon in local_doc.getElementsByTagNameNS(XMLNS_IFACE, 'icon'):
		if icon.parentNode is local_doc.documentElement:
			root.appendChild(doc.createTextNode('\n  '))
			root.appendChild(doc.importNode(icon, True))

	root.appendChild(doc.createTextNode('\n'))

	# minidom's writer loses the newline after the PI
	return _local_template_start + root.toxml()
