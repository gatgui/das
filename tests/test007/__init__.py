import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      os.environ["DAS_SCHEMA_PATH"] = os.path.abspath(os.path.dirname(__file__))

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

   def testSetEnumFromInvalidInt(self):
      v = das.make_default("enumchoices.All")
      with self.assertRaises(das.ValidationError):
         v.enum = 2

   def testSetEnumFromInvalidString(self):
      v = das.make_default("enumchoices.All")
      with self.assertRaises(das.ValidationError):
         v.enum = "Undefined"

   def testSetEnumFromValidString(self):
      v = das.make_default("enumchoices.All")
      v.enum = "On"
      self.assertEqual(v.enum, 1)

   def testStrictStaticChoice(self):
      v = das.make_default("enumchoices.All")
      with self.assertRaises(das.ValidationError):
         v.sschoice = "goodbye"

   def testStaticChoice(self):
      v = das.make_default("enumchoices.All")
      v.schoice = "goodbye"
      self.assertEqual(v.schoice, "goodbye")

   def testStrictDynamicChoice(self):
      v = das.make_default("enumchoices.All")
      with self.assertRaises(das.ValidationError):
         v.sdchoice = "ccc"

   def testDynamicChoice(self):
      v = das.make_default("enumchoices.All")
      v.dchoice = "ccc"
      self.assertEqual(v.dchoice, "ccc")

