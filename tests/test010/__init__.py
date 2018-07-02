# -*- coding: utf8 -*-
import os
import unittest
import das

class TestCase(unittest.TestCase):
   TestDir = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      os.environ["DAS_SCHEMA_PATH"] = cls.TestDir

   def setUp(self):
      pass

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions

   def testValidate(self):
      with self.assertRaises(das.ValidationError):
         das.make("validation.SomeType", value_pairs={"weight": 1.0})
      v = das.make_default("validation.SomeType")
      with self.assertRaises(das.ValidationError):
        v.value_pairs["weight"] = 1.0
      v.valid_keys.append("weight")
      v.value_pairs["weight"] = 2.0
