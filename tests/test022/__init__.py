# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error
import math


class TestCase(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      os.environ["DAS_SCHEMA_PATH"] = os.path.abspath(os.path.dirname(__file__))

   def setUp(self):
      self.types = {}
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions
   def testBoolean(self):
      for k0 in das.list_schema_types("compat"):
         v0 = das.get_schema_type(k0)
         for k1 in das.list_schema_types("compat"):
            if k1 == k0:
               continue
            v1 = das.get_schema_type(k1)
            print("%s / %s -> %s" % (k0, k1, v0.is_type_compatible(v1)))
