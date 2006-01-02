import os
from zeroinstall.injector import model
from zeroinstall.injector.reader import InvalidInterface, update
import tempfile
from logging import warn

def check(data):
	fd, tmp_name = tempfile.mkstemp(prefix = '0publish-validate-')
	os.close(fd)
	tmp_iface = model.Interface(tmp_name)
	try:
		tmp_file = file(tmp_name, 'w')
		tmp_file.write(data)
		tmp_file.close()
		try:
			update(tmp_iface, tmp_name, local = True)
			return True
		except InvalidInterface, ex:
			raise
		except Exception, ex:
			warn("Internal error", ex)
			raise InvalidInterface(str(ex))
	finally:
		os.unlink(tmp_name)
