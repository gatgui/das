import os
import unittest
import das # pylint: disable=import-error

class TestCase(unittest.TestCase):
   TestDir = None
   InputFile = None
   OutputFile = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.InputFile = cls.TestDir + "/in.hud"
      cls.OutputFile = cls.TestDir + "/out.hud"
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

   def testRead1(self):
      self.assertRaises(Exception, das.read, self.InputFile)

   def testRead2(self):
      rv = das.read(self.InputFile, schema_type="hud.HUD")
      self.assertIsInstance(rv, das.types.Struct)

   def testWrite1(self):
      das.write(das.read(self.InputFile, schema_type="hud.HUD"), self.OutputFile)
      self.assertTrue(os.path.isfile(self.OutputFile))

   def testWrite2(self):
      hud = das.read(self.InputFile, schema_type="hud.HUD")
      with self.assertRaises(Exception):
         hud.text.elements[2].align = ("top", "left")

   def testCompare1(self):
      hud1 = das.read(self.InputFile, schema_type="hud.HUD")
      das.write(hud1, self.OutputFile)
      hud2 = das.read(self.OutputFile, schema_type="hud.HUD")
      self.assertEqual(hud1, hud2)

   def testCompare2(self):
      hud1 = das.read(self.InputFile, schema_type="hud.HUD")
      das.write(hud1, self.OutputFile)
      hud2 = das.read(self.OutputFile, schema_type="hud.HUD")
      hud2.text.elements[2].opacity = 0.5
      self.assertNotEqual(hud1, hud2)
