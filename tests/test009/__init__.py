# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   TestDir = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.InputFile = cls.TestDir + "/test.person"
      cls.OutputFile = cls.TestDir + "/out.person"
      os.environ["DAS_SCHEMA_PATH"] = cls.TestDir

   def setUp(self):
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      if os.path.isfile(self.OutputFile):
         os.remove(self.OutputFile)

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions

   def _makeOne(self):
      v = das.make_default("unicode.Person")
      v.firstname = u"太郎"
      v.lastname = u"北川"
      v.gender = u"男"
      return v

   def testRead(self):
      p = das.read(self.InputFile, schema_type="unicode.Person")
      self.assertTrue(p.firstname == u"ゆきこ")
      self.assertTrue(p.lastname == u"北川")
      self.assertFalse(p.gender == u"男")

   def testSet(self):
      p = self._makeOne()
      with self.assertRaises(das.ValidationError):
         p.gender = u"どちもない"

   def testEqual(self):
      das.write(self._makeOne(), self.OutputFile)
      p0 = self._makeOne()
      p1 = das.read(self.OutputFile)
      self.assertTrue(p0 == p1)

   def testNotEqual(self):
      das.write(self._makeOne(), self.OutputFile)
      p0 = self._makeOne()
      p1 = das.read(self.OutputFile)
      p1.gender = u"女"
      self.assertFalse(p0 == p1)
