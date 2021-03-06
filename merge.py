from xml.dom import minidom, XMLNS_NAMESPACE, Node
from zeroinstall.injector.namespaces import XMLNS_IFACE
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
		self.attribs = {}		# (ns, localName) -> value
		self.requires = []
		self.commands = {}		# (name, version-expr) -> <command>

		node = impl
		while True:
			for name, value in node.attributes.itemsNS():
				if name[0] == XMLNS_NAMESPACE:
					xmltools.register_namespace(value, name[1])
				elif name not in self.attribs:
					self.attribs[name] = value
			if node.nodeName == 'group':
				# We don't care about <requires> or <command> inside <implementation>;
				# they'll get copied over anyway
				for x in childNodes(node, XMLNS_IFACE, 'requires'):
					self.requires.append(x)
				for x in childNodes(node, XMLNS_IFACE, 'restricts'):
					self.requires.append(x)
				for x in childNodes(node, XMLNS_IFACE, 'command'):
					command_name = (x.getAttribute('name'), x.getAttribute('if-0install-version'))
					if command_name not in self.commands:
						self.commands[command_name] = x
					# (else the existing definition on the child should be used)
			node = node.parentNode
			if node.nodeName != 'group':
				break

	@property
	def has_main_and_run(self):
		"""Checks whether we have a main and a <command name='run'>.
		This case requires special care."""
		for name, expr in self.commands:
			if name == 'run':
				break
		else:
			return False	# No run command
		return (None, 'main') in self.attribs

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
		if key not in list(impl.attribs.keys()):
			#print "BAD", key
			return (0,)		# Group sets an attribute the impl doesn't want
	matching_commands = 0
	for name_expr, g_command in group.commands.items():
		if name_expr not in impl.commands:
			return (0,)		# Group sets a command the impl doesn't want
		if nodesEqual(g_command, impl.commands[name_expr]):
			# Prefer matching commands to overriding them
			matching_commands += 1
	for g_req in group.requires:
		for i_req in impl.requires:
			if nodesEqual(g_req, i_req): break
		else:
			return (0,)		# Group adds a requires that the impl doesn't want
	# Score result so we get groups that have all the same requires/commands first, then ones with all the same attribs
	return (1, len(group.requires) + len(group.commands), len(group.attribs) + matching_commands)

# Note: the namespace stuff isn't quite right yet.
# Might get conflicts if both documents use the same prefix for different things.
def merge(data, local):
	local_doc = minidom.parse(local)
	master_doc = minidom.parseString(data)

	known_ids = set()
	def check_unique(elem):
		impl_id = impl.getAttribute("id")
		if impl_id in known_ids:
			raise Exception("Duplicate ID " + impl_id)
		known_ids.add(impl_id)

	for impl in find_impls(master_doc.documentElement):
		check_unique(impl)

	# Merge each implementation in the local feed in turn (normally there will only be one)
	for impl in find_impls(local_doc.documentElement):
		check_unique(impl)

		# 1. Get the context of the implementation to add. This is:
		#    - The set of its requirements
		#    - The set of its commands
		#    - Its attributes
		new_impl_context = Context(impl)

		# 2. For each <group> in the master feed, see if it provides a compatible context:
		#    - A subset of the new implementation's requirements
		#    - A subset of the new implementation's command names
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

		if new_impl_context.has_main_and_run:
			# If the existing group doesn't have the same main value then we'll need a new group. Otherwise,
			# we're likely to override the command by having main on the implementation element.
			current_group_main = group_context.attribs.get((None, 'main'), None)
			need_new_group_for_main = current_group_main != new_impl_context.attribs[(None, 'main')]
		else:
			need_new_group_for_main = False

		new_commands = []
		for name_expr, new_command in new_impl_context.commands.items():
			if need_new_group_for_main and name_expr[0] == 'run':
				# If we're creating a new <group main='...'> then we can't inherit an existing <command name='run'/>,
				old_command = None
			else:
				old_command = group_context.commands.get(name_expr, None)
			if not (old_command and nodesEqual(old_command, new_command)):
				new_commands.append(xmltools.import_node(master_doc, new_command))

		# If we have additional requirements or commands, we'll need to create a subgroup and add them
		if len(new_impl_context.requires) > len(group_context.requires) or new_commands or need_new_group_for_main:
			subgroup = xmltools.create_element(group, 'group')
			group = subgroup
			#group_context = Context(group)
			for x in new_impl_context.requires:
				for y in group_context.requires:
					if nodesEqual(x, y): break
				else:
					req = xmltools.import_node(master_doc, x)
					#print "Add", req
					xmltools.insert_element(req, group)
			for c in new_commands:
				xmltools.insert_element(c, group)

			if need_new_group_for_main:
				group.setAttribute('main', new_impl_context.attribs[(None, 'main')])
				# We'll remove it from the <implementation> below, when cleaning up duplicates

			group_context = Context(group)

		new_impl = xmltools.import_node(master_doc, impl)

		# Attributes might have been set on a parent group; move to the impl
		for name in new_impl_context.attribs:
			#print "Set", name, value
			xmltools.add_attribute_ns(new_impl, name[0], name[1], new_impl_context.attribs[name])

		for name, value in new_impl.attributes.itemsNS():
			if name[0] == XMLNS_NAMESPACE or \
			   (name in group_context.attribs and group_context.attribs[name] == value):
				#print "Deleting duplicate attribute", name, value
				new_impl.removeAttributeNS(name[0], name[1])

		xmltools.insert_element(new_impl, group)

	return master_doc.toxml('utf-8')
