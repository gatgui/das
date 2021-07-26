# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   TestDir = None
   InputFile = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.InputFile = cls.TestDir + "/in.data"
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

   def test1(self):
      das.read(self.InputFile, strict_schema=False)
