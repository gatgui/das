# -*- coding: utf8 -*-
import os
import unittest
import das

class TestCase(unittest.TestCase):
   TestDir = None
   OutputFile = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.OutputFile = cls.TestDir + "/out.alias"
      os.environ["DAS_SCHEMA_PATH"] = cls.TestDir

   def setUp(self):
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])
      if os.path.isfile(cls.OutputFile):
         os.remove(cls.OutputFile)

   # Test functions

   def test1(self):
      r = das.make_default("testalias.MyStruct")
      r.margin = "both"
      das.write(r, self.OutputFile)

   def test2(self):
      r0 = das.make("testalias.MyStruct", defaultMargin="both")
      r1 = das.read(self.OutputFile)
      self.assertEqual(r0, r1)
      self.assertEqual(r0.margin, r0.defaultMargin)
      self.assertEqual(r1.margin, r1.defaultMargin)
      with self.assertRaises(das.ValidationError):
         r0.defaultMargin = "any"
      r0.defaultMargin = "none"
      self.assertEqual(r0.margin, "none")

