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

   runtests = []
   runfuncs = {}
   for runtest in sys.argv[1:]:
      spl = runtest.split(".")
      if len(spl) > 2:
         print("Ignore invalid test specification: %s" % runtest)
         continue
      elif len(spl) == 2:
         testname, funcname = spl
         if not testname in runtests:
            lst = runfuncs.get(testname, [])
            if not funcname in lst:
               lst.append(funcname)
            runfuncs[testname] = sorted(lst)
      else:
         testname = spl[0]
         if not testname in runtests:
            if testname in runfuncs:
               del(runfuncs[testname])
            runtests.append(testname)

   runall = (len(runtests) + len(runfuncs) == 0)

   # Get list of available tests
   tests = filter(lambda x: os.path.isdir(x) and
                     re.match(r"^test\d{3}$", os.path.basename(x)) and
                     os.path.isfile(x+"/__init__.py"),
                  glob.glob("./*"))
   for test in sorted(tests):
      name = os.path.basename(test)

      if name in runfuncs:
         # specific functions
         try:
            mod = imp.load_source(name, test+"/__init__.py")
            for fn in runfuncs[name]:
               print("Add '%s.%s' to test suite..." % (name, fn))
            names = ["TestCase.%s" % x for x in runfuncs[name]]
            suite.addTests(loader.loadTestsFromNames(names, module=mod))
         except Exception as e:
            print("Skipping '%s' (%s)" % (name, e))
      elif runall or (runtests and name in runtests):
         # whole tests
         try:
            mod = imp.load_source(name, test+"/__init__.py")
            print("Add '%s' to test suite..." % name)
            suite.addTests(loader.loadTestsFromTestCase(mod.TestCase))
         except Exception as e:
            print("Skipping '%s' (%s)" % (name, e))
      else:
         print("Skip test '%s'" % name)
         continue

   unittest.TextTestRunner(verbosity=3).run(suite)
