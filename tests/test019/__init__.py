# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error


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
   def testAssign1(self):
      obj = das.make_default("orswitch.Test")
      obj.resolution = (1920, 1080)

   def testAssign2(self):
      obj = das.make_default("orswitch.Test")
      obj.resolution = {"base": (1920, 1080), "margins": {"10p": (1.1, 1.1)}, "defaultMargin": ""}

   def testAssign3(self):
      obj = das.make_default("orswitch.Test")
      with self.assertRaises(das.ValidationError):
         obj.resolution = {"base": (1280, 720)}