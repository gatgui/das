import os
import unittest
import das

class TestCase(unittest.TestCase):
   TestDir = None
   OutputFile = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.OutputFile = cls.TestDir + "/out.tl"
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

   def testWithValue(self):
      rv = das.read(self.TestDir + "/test0.tl", schema_type="timeline.ClipSource")
      self.assertIsNotNone(rv.clipRange)

   def testWithNone(self):
      rv = das.read(self.TestDir + "/test1.tl", schema_type="timeline.ClipSource")
      self.assertIsNone(rv.clipRange)

   def testSaveNone(self):
      rv = das.read(self.TestDir + "/test0.tl", schema_type="timeline.ClipSource")
      rv.clipRange = None
      das.write(rv, self.OutputFile)
      self.assertTrue(os.path.isfile(self.OutputFile))

   def testSaveNone2(self):
      rv = das.read(self.TestDir + "/test0.tl", schema_type="timeline.ClipSource")
      rv.dataRange = None
      with self.assertRaises(das.ValidationError):
         das.write(rv, self.OutputFile)

   def testSaveValue(self):
      rv = das.read(self.TestDir + "/test1.tl", schema_type="timeline.ClipSource")
      rv.clipRange = [1, 100]
      das.write(rv, self.OutputFile)
      self.assertTrue(os.path.isfile(self.OutputFile))

   def testSaveInvalidValue(self):
      rv = das.read(self.TestDir + "/test1.tl", schema_type="timeline.ClipSource")
      rv.clipRange = (1, 100, 10)
      with self.assertRaises(das.ValidationError):
         das.write(rv, self.OutputFile)
