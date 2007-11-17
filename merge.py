import os
from xml.dom import minidom, XMLNS_NAMESPACE, Node
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector import model, reader
from logging import info
import xmltools

def childNodes(parent, namespaceURI, localName = None):
	for x in parent.childNodes:
		if x.nodeType != Node.ELEMENT_NODE: continue
		if x.namespaceURI != namespaceURI: continue

		if localName is None or x.localName == localName:
			yield x

class Context:
	def __init__(self, impl):
		doc = impl.ownerDocument
		self.attribs = {}
		self.requires = []

		node = impl
		while True:
			for name, value in node.attributes.itemsNS():
				if name not in self.attribs:
					self.attribs[name] = value
			if node.nodeName == 'group':
				# We don't care about <requires> inside <implementation>; they'll get copied over anyway
				for x in childNodes(node, XMLNS_IFACE, 'requires'):
					self.requires.append(x)
			node = node.parentNode
			if node.nodeName != 'group':
				break

def find_impls(parent):
	"""Return all <implementation> children, including those inside groups."""
	for x in childNodes(parent, XMLNS_IFACE):
		if x.localName == 'implementation':
			yield x
		elif x.localName == 'group':
			for y in find_impls(x):
				yield y

def find_groups(parent):
	"""Return all <group> children, including those inside other groups."""
	for x in childNodes(parent, XMLNS_IFACE, 'group'):
		yield x
		for y in find_groups(x):
			yield y
	
def is_subset(group, impl):
	for key in group.attribs:
		if key not in impl.attribs.keys():
			print "BAD", key
			return False		# Group sets an attribute the impl doesn't want
	for g_req in group.requires:
		for i_req in impl.requires:
			if nodesEqual(g_req, i_req): break
		else:
			return False		# Group adds a requires that the impl doesn't want
	return True

def merge(data, local):
	local_doc = minidom.parse(local)
	master_doc = minidom.parseString(data)

	# Merge each implementation in the local feed in turn (normally there will only be one)
	for impl in find_impls(local_doc.documentElement):
		# 1. Get the context of the implementation to add. This is:
		#    - The set of its requirements
		#    - Its attributes
		new_impl_context = Context(impl)

		# 2. For each <group> in the master feed, see if it provides a compatible context:
		#    - A subset of the new implementation's requirements
		#    - A subset of the new implementation's attributes (names, not values)
		#    Choose the most compatible <group> (the root counts as a minimally compatible group)

		best_group = (0, master_doc.documentElement)

		for group in find_groups(master_doc.documentElement):
			group_context = Context(group)
			if is_subset(group_context, new_impl_context):
				best_group = (0, group)

		group = best_group[1]
		group_context = Context(group)

		# If we have additional requirements, we'll need to create a subgroup and add them
		if len(new_impl_context.requires) > len(group_context.requires):
			subgroup = xmltools.create_element(group, 'group')
			group = subgroup
			group_context = Context(group)
			for x in new_impl_context.requires:
				for y in group_context.requires:
					if nodesEqual(x, y): break
				else:
					req = master_doc.importNode(x, True)
					#print "Add", req
					xmltools.insert_element(req, group)

		new_impl = master_doc.importNode(impl, True)
		for name, value in new_impl.attributes.itemsNS():
			if name in group_context.attribs and group_context.attribs[name] == value:
				#print "Deleting duplicate attribute", name, value
				new_impl.removeAttributeNS(name[0], name[1])
			else:
				# Might have been on a parent group; move to the impl
				#print "Set", name, value
				new_impl.setAttributeNS(name[0], name[1], value)

		xmltools.insert_element(new_impl, group)

	return master_doc.toxml()
