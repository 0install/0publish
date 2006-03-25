from zeroinstall.injector import gpg
import tempfile, os, base64, sys

def check_signature(path):
	data = file(path).read()
	xml_comment = data.rfind('\n<!-- Base64 Signature')
	if xml_comment >= 0:
		data_stream, sigs = gpg.check_stream(file(path))
		sign_fn = sign_xml
		data = data[:xml_comment + 1]
		data_stream.close()
	elif data.startswith('-----BEGIN'):
		data_stream, sigs = gpg.check_stream(file(path))
		sign_fn = sign_plain
		data = data_stream.read()
	else:
		return data, sign_unsigned, None
	for sig in sigs:
		if isinstance(sig, gpg.ValidSig):
			return data, sign_fn, sig.fingerprint
	print "ERROR: No valid signatures found!"
	for sig in sigs:
		print "Got:", sig
	ok = raw_input('Ignore and load anyway? (y/N) ').lower()
	if ok and 'yes'.startswith(ok):
		return data, sign_unsigned, None
	sys.exit(1)

def write_tmp(path, data):
	"""Create a temporary file in the same directory as 'path' and write data to it."""
	fd, tmp = tempfile.mkstemp(prefix = 'tmp-', dir = os.path.dirname(path))
	stream = os.fdopen(fd, 'w')
	stream.write(data)
	stream.close()
	return tmp

def run_gpg(default_key, *arguments):
	arguments = list(arguments)
	if default_key is not None:
		arguments = ['--default-key', default_key] + arguments
	arguments.insert(0, 'gpg')
	if os.spawnvp(os.P_WAIT, 'gpg', arguments):
		raise Exception("Command '%s' failed" % arguments)

def sign_unsigned(path, data, key):
	os.rename(write_tmp(path, data), path)

def sign_plain(path, data, key):
	tmp = write_tmp(path, data)
	try:
		run_gpg(key, '--clearsign', tmp)
	finally:
		os.unlink(tmp)
	os.rename(tmp + '.asc', path)

def sign_xml(path, data, key):
	tmp = write_tmp(path, data)
	try:
		run_gpg(key, '--detach-sign', tmp)
	finally:
		os.unlink(tmp)
	tmp += '.sig'
	encoded = base64.encodestring(file(tmp).read())
	os.unlink(tmp)
	sig = "<!-- Base64 Signature\n" + encoded + "\n-->\n"
	os.rename(write_tmp(path, data + sig), path)
