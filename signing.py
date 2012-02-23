from zeroinstall import SafeException
from zeroinstall.injector import gpg
import tempfile, os, base64, sys, shutil
import subprocess
from logging import warn

def check_signature(path):
	data = file(path).read()
	xml_comment = data.rfind('\n<!-- Base64 Signature')
	if xml_comment >= 0:
		data_stream, sigs = gpg.check_stream(file(path))
		sign_fn = sign_xml
		data = data[:xml_comment + 1]
		data_stream.close()
	elif data.startswith('-----BEGIN'):
		warn("Plain GPG signatures are no longer supported - not checking signature!")
		warn("Will save in XML format.")
		child = subprocess.Popen(['gpg', '--decrypt', path], stdout = subprocess.PIPE)
		data, unused = child.communicate()
		import __main__
		__main__.force_save = True
		return data, sign_xml, None
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
		import __main__
		__main__.force_save = True
		return data, sign_unsigned, None
	sys.exit(1)

def write_tmp(path, data):
	"""Create a temporary file in the same directory as 'path' and write data to it."""
	tmpdir = os.path.dirname(path)
	if tmpdir:
		assert os.path.isdir(tmpdir), "Not a directory: " + tmpdir
	fd, tmp = tempfile.mkstemp(prefix = 'tmp-', dir = tmpdir)
	stream = os.fdopen(fd, 'w')
	stream.write(data)
	stream.close()

	umask = os.umask(0)
	os.umask(umask)
	os.chmod(tmp, 0644 & ~umask)

	return tmp

def run_gpg(default_key, *arguments):
	arguments = list(arguments)
	if default_key is not None:
		arguments = ['--default-key', default_key] + arguments
	arguments.insert(0, '--use-agent')
	arguments.insert(0, 'gpg')
	if os.spawnvp(os.P_WAIT, 'gpg', arguments):
		raise SafeException("Command '%s' failed" % arguments)

def sign_unsigned(path, data, key):
	os.rename(write_tmp(path, data), path)

def sign_xml(path, data, key):
	tmp = write_tmp(path, data)
	sigtmp = tmp + '.sig'
	try:
		run_gpg(key, '--detach-sign', '--output', sigtmp, tmp)
	finally:
		os.unlink(tmp)
	encoded = base64.encodestring(file(sigtmp).read())
	os.unlink(sigtmp)
	sig = "<!-- Base64 Signature\n" + encoded + "\n-->\n"
	os.rename(write_tmp(path, data + sig), path)

def export_key(dir, fingerprint):
	assert fingerprint is not None
	# Convert fingerprint to key ID
	stream = os.popen('gpg --with-colons --list-keys %s' % fingerprint)
	try:
		keyID = None
		for line in stream:
			parts = line.split(':')
			if parts[0] == 'pub':
				if keyID:
					raise Exception('Two key IDs returned from GPG!')
				keyID = parts[4]
	finally:
		stream.close()
	key_file = os.path.join(dir, keyID + '.gpg')
	if os.path.isfile(key_file):
		return
	key_stream = file(key_file, 'w')
	stream = os.popen("gpg -a --export '%s'" % fingerprint)
	shutil.copyfileobj(stream, key_stream)
	stream.close()
	key_stream.close()
	print "Exported public key as '%s'" % key_file
