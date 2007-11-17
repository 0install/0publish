import os
from xml.dom import minidom, XMLNS_NAMESPACE, Node
from zeroinstall.injector.namespaces import XMLNS_IFACE
from zeroinstall.injector import model, reader
from logging import info
import xmltools

def childNodes(parent, namespaceURI = None, localName = None):
	for x in parent.childNodes:
		if x.nodeType != Node.ELEMENT_NODE: continue
		if namespaceURI is not None and x.namespaceURI != namespaceURI: continue

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

def nodesEqual(a, b):
	assert a.nodeType == Node.ELEMENT_NODE
	assert b.nodeType == Node.ELEMENT_NODE

	if a.namespaceURI != b.namespaceURI:
		return False

	if a.nodeName != b.nodeName:
		return False
	
	a_attrs = set(["%s %s" % (name, value) for name, value in a.attributes.itemsNS()])
	b_attrs = set(["%s %s" % (name, value) for name, value in b.attributes.itemsNS()])

	if a_attrs != b_attrs:
		#print "%s != %s" % (a_attrs, b_attrs)
		return False
	
	a_children = list(childNodes(a))
	b_children = list(childNodes(b))

	if len(a_children) != len(b_children):
		return False
	
	for a_child, b_child in zip(a_children, b_children):
		if not nodesEqual(a_child, b_child):
			return False
	
	return True

def score_subset(group, impl):
	"""Returns (is_subset, goodness)"""
	for key in group.attribs:
		if key not in impl.attribs.keys():
			#print "BAD", key
			return (0,)		# Group sets an attribute the impl doesn't want
	for g_req in group.requires:
		for i_req in impl.requires:
			if nodesEqual(g_req, i_req): break
		else:
			return (0,)		# Group adds a requires that the impl doesn't want
	# Score result so we get groups that have all the same requires first, then ones with all the same attribs
	return (1, len(group.requires), len(group.attribs))

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

		best_group = ((1, 0, 0), master_doc.documentElement)	# (score, element)

		for group in find_groups(master_doc.documentElement):
			group_context = Context(group)
			score = score_subset(group_context, new_impl_context)
			if score > best_group[0]:
				best_group = (score, group)

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
