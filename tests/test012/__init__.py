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
      cls.OutputFile = cls.TestDir + "/out.setdata"
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

   def _makeValue(self):
      r = das.make_default("testset.MySet")
      r |= (1, 3.3, "hello", "world")
      return r

   # Test functions

   def test1(self):
      r = self._makeValue()
      das.write(r, self.OutputFile)

   def test2(self):
      r0 = self._makeValue()
      r1 = das.read(self.OutputFile)
      self.assertEqual(r0, r1)
      r0 |= (2, 4, -2.3, "goodbye")
      self.assertNotEqual(r0, r1)

   def test3(self):
      r = das.read(self.OutputFile)
      with self.assertRaises(das.ValidationError):
         r.add([1, 2, 3])
