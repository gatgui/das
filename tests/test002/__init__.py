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
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions

   def testRead1(self):
      _ = das.read(self.TestDir + "/ok.asset", schema_type="asset.TokenDict")

   def testRead2(self):
      with self.assertRaises(das.ValidationError):
         das.read(self.TestDir + "/error1.asset", schema_type="asset.TokenDict")

   def testRead3(self):
      with self.assertRaises(das.ValidationError):
         das.read(self.TestDir + "/error2.asset", schema_type="asset.TokenDict")
