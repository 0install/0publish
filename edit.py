import tempfile, os

def edit(data):
	fd, tmp = tempfile.mkstemp(prefix = '0publish-')
	try:
		stream = os.fdopen(fd, 'w')
		stream.write(data)
		stream.close()
		editor = os.environ.get('EDITOR', 'vi')
		if os.spawnlp(os.P_WAIT, editor, editor, tmp):
			raise Exception('Editing with $EDITOR ("%s") failed')
		new_data = file(tmp).read()
	finally:
		os.unlink(tmp)
	if new_data == data:
		raise Exception('Data unchanged after edit. Aborting.')
	return new_data
