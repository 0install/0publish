import os
from xml.dom import minidom, XMLNS_NAMESPACE
from zeroinstall.injector.namespaces import XMLNS_IFACE


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
  <!-- <feed-for interface='http://site/interface'> -->

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
