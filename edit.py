import tempfile, os
from logging import info, debug

path_dirs = os.environ.get('PATH', '/bin:/usr/bin').split(':')

def available_in_path(command):
	info("Checking for %s in $PATH", command)
	for x in path_dirs:
		debug("Checking for %s/%s", x, command)
		if os.path.isfile(os.path.join(x, command)):
			return True
	return False

def edit(data):
	fd, tmp = tempfile.mkstemp(prefix = '0publish-', suffix = '.xml')
	try:
		stream = os.fdopen(fd, 'wb')
		stream.write(data)
		stream.close()
		editor = os.environ.get('EDITOR', None)
		if editor is None:
			info("$EDITOR not set. Trying fallbacks...")
			for editor in ['sensible-editor', 'nano', 'vi']: # ,'ed'] ;-)
				if available_in_path(editor):
					break
			else:
				raise Exception("No editor found. Try setting $EDITOR first.")
		info("Editing tmp file with '%s %s'..." % (editor, tmp))
		if os.spawnlp(os.P_WAIT, editor, editor, tmp):
			raise Exception('Editing with $EDITOR ("%s") failed' % editor)
		with open(tmp, 'rb') as stream:
			new_data = stream.read()
	finally:
		os.unlink(tmp)
	return new_data
