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
   def testInherit1(self):
      sr = das.make_default("inherit.ScaledResolution")
      print(sr.pixel_count())
      sx = int(round(sr.width * sr.scale.x))
      sy = int(round(sr.height * sr.scale.y))
      print(sx * sy)
      print(sr.is_uniform())
