# -*- coding: utf8 -*-
import os
import unittest
import das


class TestCase(unittest.TestCase):
   TestDir = None
   HomerInput = None
   HomerOutput = None
   SimpsonsInput = None
   SimpsonsOutput = None
   MultipleOutput = None

   @classmethod
   def setUpClass(cls):
      cls.TestDir = os.path.abspath(os.path.dirname(__file__))
      cls.HomerInput = cls.TestDir + "/homer.person"
      cls.HomerOutput = cls.TestDir + "/homer.csv"
      cls.SimpsonsInput = cls.TestDir + "/simpsons.family"
      cls.SimpsonsOutput = cls.TestDir + "/simpsons.csv"
      cls.MultipleOutput = cls.TestDir + "/multiple.csv"
      os.environ["DAS_SCHEMA_PATH"] = cls.TestDir

   def setUp(self):
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      if os.path.isfile(self.HomerOutput):
        os.remove(self.HomerOutput)
      if os.path.isfile(self.SimpsonsOutput):
        os.remove(self.SimpsonsOutput)
      if os.path.isfile(self.MultipleOutput):
        os.remove(self.MultipleOutput)

   @classmethod
   def tearDownClass(cls):
      del(os.environ["DAS_SCHEMA_PATH"])

   # Test functions
   def testSimpsons(self):
      simpsons = das.read(self.SimpsonsInput)
      das.write_csv(simpsons, self.SimpsonsOutput)
      from_csv = das.read_csv(self.SimpsonsOutput)[0]
      self.assertEqual(simpsons, from_csv)
      simpsons.father.name.given = "ned"
      self.assertNotEqual(simpsons, from_csv)

   def testHomer(self):
      homer = das.read(self.HomerInput)
      das.write_csv(homer, self.HomerOutput)
      from_csv = das.read_csv(self.HomerOutput)[0]
      self.assertEqual(homer, from_csv)
      from_csv.name.family = "flanders"
      self.assertNotEqual(homer, from_csv)

   def testMultiple(self):
      simpsons = das.read(self.SimpsonsInput)
      homer = das.read(self.HomerInput)

      ned = das.make_default("csv.Person")
      ned.name.given = "ned"
      ned.name.family = "flanders"
      rod = das.make_default("csv.Relationship")
      todd = das.make_default("csv.Relationship")
      rod.data.name.given = "rod"
      rod.data.name.family = "flanders"
      todd.data.name.given = "todd"
      todd.data.name.family = "flanders"
      ned.family = [rod, todd]

      das.write_csv([simpsons, homer, ned], self.MultipleOutput, alias={"csv.Person": "p", "csv.Family": "f"})

      read_data = das.read_csv(self.MultipleOutput)
      self.assertEqual(read_data[0], simpsons)
      self.assertEqual(read_data[1], homer)
      self.assertEqual(read_data[2], ned)
      self.assertNotEqual(read_data[2], homer)
      self.assertNotEqual(read_data[1], ned)
