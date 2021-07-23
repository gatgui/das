import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   TestDir = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      os.environ["DAS_SCHEMA_PATH"] = cls.TestDir

   def setUp(self):
      pass

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions

   def _makeOne(self):
      v = das.make_default("comparetest.CompareType")
      v.attribs.extend([{"weight1": 0.1, "weight2": -1.4}, {"distance1": 10.2, "distance2": 3.9}])
      v.people = (das.Struct(name="Alfred", age=28), das.Struct(name="Ingrid", age=24))
      return v

   def testEqual1(self):
      v0 = self._makeOne()
      v0.option = True
      v1 = das.copy(v0)
      self.assertEqual(v0, v1)

   def testEqual2(self):
      v0 = self._makeOne()
      v0.option = True
      v1 = self._makeOne()
      v1.option = True
      self.assertEqual(v0, v1)

   def testNonEqual1(self):
      v0 = self._makeOne()
      v1 = das.copy(v0)
      v1.option = False
      self.assertNotEqual(v0, v1)

   def testNonEqual2(self):
      v0 = self._makeOne()
      v1 = self._makeOne()
      v1.option = False
      self.assertNotEqual(v0, v1)
