# -*- coding: utf8 -*-
import os
import unittest
import das
import math


class TestCase(unittest.TestCase):
   TestDir = None
   Schema = None
   HomerOutput = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.Schema = cls.TestDir + "/inherit.schema"
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

   # Test functions
   def testInheritStatic(self):
      sr = das.make_default("inherit.ScaledResolution")
      sr.width = 20
      sr.height = 10
      self.assertTrue(sr.pixel_count() == 200)
      sr.scale = {"x": 2, "y": 1}
      sx = int(round(sr.width * sr.scale.x))
      sy = int(round(sr.height * sr.scale.y))
      self.assertTrue((sx * sy) == 400)
      self.assertFalse(sr.scale.is_uniform())

   def testInheritDynamic(self):
      st = das.get_schema_type("inherit.Margins")
      st.inherit("inherit.Resolution")
      st.inherit("inherit.Scale")
      # => this modifies the type itself
      # _st = st.copy()
      # das.add_schema_type("inherit.Margins2", _st)
      # ml = das.get_registered_mixins("inherit.Margins")
      # das.register_mixins(*ml, schema_type="inherit.Margins2")
      # _st.inherit()
      # -> das.copy_type("inherit.Margins", "Margins2")

      sr = das.make_default("inherit.Margins")
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
      st = das.get_schema_type("inherit.ScaledResolution")
      with self.assertRaises(Exception):
         st.inherit("inherit.Rect1")
   
   def testFieldConflict2(self):
      st = das.get_schema_type("inherit.ScaledResolution")
      with self.assertRaises(Exception):
         st.inherit("inherit.Rect2")
   