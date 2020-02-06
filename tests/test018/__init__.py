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
      cls.Schema = cls.TestDir + "/conform.schema"      
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
   def testFill(self):
      res = {"age": 1}

      try:
         res = das.conform(res, "conform.Person")
      except:
         self.assertTrue(True)
      else:
         self.assertTrue(False)

      self.assertNotIn("name", res)

      res = {"age": 1}

      try:
         res = das.conform(res, "conform.Person", fill=True)
      except:
         self.assertTrue(False)
      else:
         self.assertTrue(True)

      self.assertIn("name", res)

   def testStruct(self):
      bart = {"name": {"given": "Bart", "family": "Simpson", "middle": "Jojo"}, "age": 10, "gender": "male"}
      res = das.conform(bart, "conform.Person")
      self.assertNotIn("gender", res)
      self.assertIn("name", res)
      self.assertIn("given", res["name"])
      self.assertIn("family", res["name"])
      self.assertNotIn("middle", res["name"])
      self.assertIn("age", res)

      bart.pop("age")
      try:
         res = das.conform(bart, "conform.Person")
      except:
         self.assertTrue(True)
      else:
         self.assertTrue(False)

   def testSequence(self):
      seq = [{"name": {"given": "Lisa", "family": "Simpson", "middle": "Marie"}, "age": 7, "gender": "female"}, {"name": {"given": "Bart", "family": "Simpson", "middle": "Jojo"}, "age": 10, "gender": "male"}]
      res = das.conform(seq, "conform.PersonSeq")
      for per in res:
         self.assertNotIn("gender", per)
         self.assertIn("name", per)
         self.assertIn("given", per["name"])
         self.assertIn("family", per["name"])
         self.assertNotIn("middle", per["name"])
         self.assertIn("age", per)

   def testDict(self):
      try:
         res = das.conform({1: {"given": "Bart", "family": "Simpson"}}, "conform.NameDict")
      except Exception as e:
         self.assertTrue(False)
      else:
         self.assertTrue(True)

      try:
         res = das.conform({1: "Simpson"}, "conform.NameDict")
      except Exception as e:
         self.assertTrue(True)
      else:
         self.assertTrue(False)
