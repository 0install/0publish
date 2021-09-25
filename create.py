import os
from xml.dom import minidom, Node
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector import model, reader, qdom

# minidom loses the newline after the stylesheet declaration, so we
# just serialise the body and glue this on the front manually...
# Firefox doesn't support cross-site links to style-sheets, so use a
# relative link instead.
xml_header = b"""<?xml version="1.0" ?>
<?xml-stylesheet type='text/xsl' href='feed.xsl'?>
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

  <!-- Optionally, uncomment this to specify the program's homepage: -->
  <!-- <homepage>http://site/prog</homepage> -->

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
    <implementation id="." version="0.1"/>
  </group>
</interface>
"""

def create(f):
	assert not os.path.exists(f)
	name = os.path.basename(f)
	return (_template % (name.split('.', 1)[0])).encode()

def remove_with_preceding_comments(element):
	root = element.ownerDocument.documentElement
	to_remove = [element]
	node = element
	while node.previousSibling:
		node = node.previousSibling
		if node.nodeType == Node.COMMENT_NODE or \
		   (node.nodeType == Node.TEXT_NODE and node.nodeValue.strip() == ''):
			to_remove.append(node)
		else:
			break
	for x in to_remove:
		root.removeChild(x)

def create_from_local(local):
	path = os.path.abspath(local)
	with open(path, 'rb') as stream:
		feed = model.ZeroInstallFeed(qdom.parse(stream), local_path = path)
	if not feed.feed_for:
		raise Exception("No <feed-for> in '%s'; can't use it as a local feed." % local)
	if len(feed.feed_for) != 1:
		raise Exception("Multiple <feed-for> elements. Not supported, sorry!")
	uri = list(feed.feed_for)[0]

	doc = minidom.parse(local)
	root = doc.documentElement
	root.setAttribute('uri', uri)

	for element in root.getElementsByTagNameNS(XMLNS_IFACE, 'feed-for'):
		if element.parentNode is root:
			remove_with_preceding_comments(element)

	root.appendChild(doc.createTextNode('\n'))

	# minidom's writer loses the newline after the PI
	return xml_header + root.toxml('utf-8')
