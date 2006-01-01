from zeroinstall.injector import gpg
import tempfile, os, base64

def check_signature(path):
	data = file(path).read()
	if data.startswith('BEGIN'):
		data_stream, sigs = gpg.check_stream(file(path))
		sign_fn = sign_plain
	elif '\n<!-- Base64 Signature' in data:
		data_stream, sigs = gpg.check_stream(file(path))
		sign_fn = sign_xml
	else:
		return data, sign_unsigned, None
	for sig in sigs:
		if isinstance(sig, gpg.ValidSig):
			return data_stream.read(), sign_fn, sig.fingerprint
	raise Exception('No valid signatures found!')

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
	except:
		os.unlink(tmp)
		raise
	os.rename(tmp + '.asc', path)

def sign_xml(path, data, key):
	tmp = write_tmp(path, data)
	try:
		run_gpg(key, '--detach-sign', tmp)
	finally:
		os.unlink(tmp)
	tmp += '.sig'
	encoded = base64.encodestring(file(tmp).read())
	sig = "<!-- Base64 Signature\n" + encoded + "\n-->\n"
	os.rename(write_tmp(path, data + sig), path)
