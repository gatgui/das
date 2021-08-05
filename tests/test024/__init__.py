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
   def testTuple(self):
       v = das.make_default("mix.tuple")
       v.niceEcho()

   def testSequence(self):
       v = das.make_default("mix.sequence")
       v.append("hello")
       v.append("world")
       v.niceEcho()

   def testSet(self):
       v = das.make_default("mix.set")
       v.add("fruit")
       v.add("basket")
       v.niceEcho()

   def testDict(self):
       v = das.make_default("mix.dict")
       v["key1"] = "value1"
       v["key2"] = "value2"
       v.niceEcho()
