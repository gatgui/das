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
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions
   def testInheritStatic(self):
      sr = das.make_default("extend.ScaledResolution")
      sr.width = 20
      sr.height = 10
      self.assertTrue(sr.pixel_count() == 200)
      sr.scale = {"x": 2, "y": 1}
      sx = int(round(sr.width * sr.scale.x))
      sy = int(round(sr.height * sr.scale.y))
      self.assertTrue((sx * sy) == 400)
      self.assertFalse(sr.scale.is_uniform())

   def testInheritDynamic(self):
      st = das.get_schema_type("extend.Margins").copy()
      st.extend("extend.Resolution")
      st.extend("extend.Scale")
      sr = st.make_default()
      sr.width = 20
      sr.height = 10
      sr.x = 2
      sr.y = 1
      sx = int(round(sr.width * sr.x))
      sy = int(round(sr.height * sr.y))
      self.assertTrue(sr.pixel_count() == 200)
      self.assertTrue((sx * sy) == 400)
      self.assertFalse(sr.is_uniform())

   def testFieldConflict1(self):
      st = das.get_schema_type("extend.ScaledResolution")
      with self.assertRaises(Exception):
         st.extend("extend.Rect1")
   
   def testFieldConflict2(self):
      st = das.get_schema_type("extend.ScaledResolution")
      with self.assertRaises(Exception):
         st.extend("extend.Rect2")

   def testFieldOverride(self):
      st = das.get_schema_type("extend.ScaledResolution")
      st.extend("extend.Rect3")
