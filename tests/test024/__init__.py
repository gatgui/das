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
       v = das.make("mix.tuple", "C", "D", "E")
       v.niceEcho()

   def testSequence(self):
       v = das.make("mix.sequence", "hello", "world")
       v.niceEcho()

   def testSet(self):
       v = das.make("mix.set", "basket", "fruit")
       v.niceEcho()

   def testDict(self):
       v = das.make("mix.dict", key1="value1", key2="value2")
       v.niceEcho()
