# -*- coding: utf8 -*-
import os
import unittest
import das

class TestCase(unittest.TestCase):
   TestDir = None
   TooOld = None
   TooNew = None
   Older = None
   Newer = None
   NoInf = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.TooOld = cls.TestDir + "/tooold.compat"
      cls.TooNew = cls.TestDir + "/toonew.compat"
      cls.Older = cls.TestDir + "/older.compat"
      cls.Newer = cls.TestDir + "/newer.compat"
      cls.OutputFile = cls.TestDir + "/out.compat"
      cls.NoInf = cls.TestDir + "/noinf.compat"
      os.environ["DAS_SCHEMA_PATH"] = cls.TestDir

   def setUp(self):
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      if os.path.isfile(self.OutputFile):
        os.remove(self.OutputFile)

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions

   def testTooOld(self):
      with self.assertRaises(das.VersionError):
         das.read(self.TooOld)

   def testOlder(self):
      das.read(self.Older)

   def testNewer(self):
      r = das.read(self.Newer)
      das.write(r, self.OutputFile)
      self.assertEqual(das.read(self.Newer), das.read(self.OutputFile))
      self.assertNotEqual(das.read(self.Newer, schema_type=None, ignore_meta=True), das.read(self.OutputFile, schema_type=None, ignore_meta=True))

   def testTooNew(self):
      with self.assertRaises(das.VersionError):
         das.read(self.TooNew)

   def testNoInf(self):
      with self.assertRaises(das.ValidationError):
         das.read(self.NoInf)
