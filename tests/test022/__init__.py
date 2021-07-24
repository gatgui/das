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
      k0 = "compat.boolean"
      v0 = das.get_schema_type(k0)
      for k1 in das.list_schema_types("compat"):
         v1 = das.get_schema_type(k1)
         rv = v0.is_type_compatible(v1)
         if k1 == k0:
            self.assertTrue(rv)
         else:
            self.assertFalse(rv)

   def testInteger(self):
      k0 = "compat.integer"
      v0 = das.get_schema_type(k0)
      for k1 in das.list_schema_types("compat"):
         v1 = das.get_schema_type(k1)
         rv = v0.is_type_compatible(v1)
         if k1.startswith("compat.integer"):
            if "Enum" in k1:
               self.assertFalse(rv)
            else:
               self.assertTrue(rv)
         else:
            self.assertFalse(rv)

   def testIntegerMin(self):
      st = das.get_schema_type("compat.integerMin1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integer")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerMin3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange1")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange4")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange5")))

   def testIntegerMax(self):
      st = das.get_schema_type("compat.integerMax1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integer")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerMax3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange1")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange4")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange5")))

   def testIntegerRange(self):
      st = das.get_schema_type("compat.integerRange1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integer")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMin3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerMax3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerRange2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange4")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerRange5")))

   def testIntegerEnum(self):
      st = das.get_schema_type("compat.integerEnum1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integer")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.integerEnum1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerEnum2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.integerEnum3")))

   def testReal(self):
      k0 = "compat.real"
      v0 = das.get_schema_type(k0)
      for k1 in das.list_schema_types("compat"):
         v1 = das.get_schema_type(k1)
         rv = v0.is_type_compatible(v1)
         if k1.startswith("compat.real"):
            self.assertTrue(rv)
         else:
            self.assertFalse(rv)

   def testRealMin(self):
      st = das.get_schema_type("compat.realMin1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.real")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realMin3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange4")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange5")))

   def testRealMax(self):
      st = das.get_schema_type("compat.realMax1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.real")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realMax3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin3")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange4")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange5")))

   def testRealRange(self):
      st = das.get_schema_type("compat.realRange1")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.real")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMin3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax2")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realMax3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.realRange3")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange4")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.realRange5")))

   def testString(self):
      k0 = "compat.string"
      v0 = das.get_schema_type(k0)
      for k1 in das.list_schema_types("compat"):
         v1 = das.get_schema_type(k1)
         rv = v0.is_type_compatible(v1)
         if k1.startswith("compat.string"):
            self.assertTrue(rv)
         else:
            self.assertFalse(rv)

   def testStringChoice(self):
      st = das.get_schema_type("compat.stringChoice1")
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.string")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.stringChoice2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.stringMatch")))
      st = das.get_schema_type("compat.stringChoice2")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.string")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.stringChoice1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.stringMatch")))

   def testStringMatch(self):
      st = das.get_schema_type("compat.stringMatch")
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.string")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.stringChoice1")))
      self.assertFalse(st.is_type_compatible(das.get_schema_type("compat.stringChoice2")))
      self.assertTrue(st.is_type_compatible(das.get_schema_type("compat.stringChoice3")))
