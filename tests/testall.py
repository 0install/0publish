#!/usr/bin/env python

# For a coverage report:
# 0install run -w 'shift; python3-coverage run' --command=test ../0publish.xml
# python3-coverage html

import unittest, os, sys
for x in ['LANGUAGE', 'LANG']:
	if x in os.environ:
		del os.environ[x]
my_dir = os.path.dirname(sys.argv[0])
if not my_dir:
	my_dir = os.getcwd()

if len(sys.argv) > 1:
	testLoader = unittest.TestLoader()
	alltests = testLoader.loadTestsFromNames(sys.argv[1:])
else:
	suite_names = [f[:-3] for f in os.listdir(my_dir)
			if f.startswith('test') and f.endswith('.py')]
	suite_names.remove('testall')
	suite_names.sort()

	alltests = unittest.TestSuite()

	for name in suite_names:
		m = __import__(name, globals(), locals(), [])
		alltests.addTest(m.suite)

a = unittest.TextTestRunner(verbosity=2).run(alltests)

print("\nResult", a)
if not a.wasSuccessful():
	sys.exit(1)
