# -*- coding: utf8 -*-
import os
import unittest
import das


class TestCase(unittest.TestCase):
   TestDir = None
   Schema = None
   HomerOutput = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.Schema = cls.TestDir + "/orswitch.schema"
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
   def testSwitch(self):
      res1 = (1920, 1080)
      res2 = {"base": (1920, 1080), "margins": {"10p": (1.1, 1.1)}, "defaultMargin": ""}
      obj = das.make_default("orswitch.Test")
      obj.resolution = res2
      obj.resolution = res1
