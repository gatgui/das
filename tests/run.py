import os
import re
import imp
import sys
import glob
import unittest


if __name__ == "__main__":
   # Setup PYTHONPATH
   testdir = os.path.abspath(os.path.dirname(__file__))

   sys.path.append(testdir)
   sys.path.append(os.path.join(testdir, "../python"))

   os.chdir(testdir)

   suite = unittest.TestSuite()
   loader = unittest.TestLoader()

   runtests = sys.argv[1:]

   # Get list of available tests
   tests = filter(lambda x: os.path.isdir(x) and re.match(r"^test\d{3}$", os.path.basename(x)) and os.path.isfile(x+"/__init__.py"), glob.glob("./*"))
   for test in tests:
      name = os.path.basename(test)
      if runtests and not name in runtests:
         print("Skip test '%s'" % name)
         continue
      try:
         mod = imp.load_source(name, test+"/__init__.py")
         print("Add '%s' to test suite..." % name)
         suite.addTests(loader.loadTestsFromTestCase(mod.TestCase))
      except Exception as e:
         print("Skipping '%s' (%s)" % (name, e))

   unittest.TextTestRunner(verbosity=3).run(suite)
