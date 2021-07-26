# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   TestDir = None
   InputFile = None
   OutputFile = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.InputFile = cls.TestDir + "/old.compat"
      cls.OutputFile = cls.TestDir + "/out.compat"
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

   def testSet(self):
      r = das.make_default("compatibility.SomeType")
      r.oldField = ["hello", "world"]

   def testOld(self):
      r = das.read(self.InputFile)
      self.assertEqual(r.newField == ["hello", "world"], True)

   def testNew(self):
      r = das.read(self.InputFile)
      das.write(r, self.OutputFile)
      with open(self.OutputFile, "r") as f:
         d = eval(f.read())
         self.assertEqual(d["newField"] == ["hello", "world"], True)
