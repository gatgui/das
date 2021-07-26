# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   TestDir = None
   OutputFile = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.OutputFile = cls.TestDir + "/out.data"
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
      if os.path.isfile(cls.OutputFile):
         os.remove(cls.OutputFile)

   # Test functions

   def test1(self):
      r0 = das.make_default("testmultiline.MyStruct")
      r0.comment = """hello
world.
Be happy!"""
      das.write(r0, self.OutputFile)
      r1 = das.read(self.OutputFile)
      self.assertEqual(r0.comment, r1.comment)

   def test2(self):
      r0 = das.make_default("testmultiline.MyStruct")
      r0.comment = u"""hello
world.
Be happy!"""
      das.write(r0, self.OutputFile)
      r1 = das.read(self.OutputFile)
      self.assertEqual(r0.comment, r1.comment)

   def test3(self):
      r0 = das.make_default("testmultiline.MyStruct")
      r0.comment = u"""昨日
今日
明日"""
      das.write(r0, self.OutputFile)
      r1 = das.read(self.OutputFile)
      self.assertEqual(r0.comment, r1.comment)