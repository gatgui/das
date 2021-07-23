# -*- coding: utf8 -*-
import os
import unittest
import das # pylint: disable=import-error
import math


class TestCase(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      pass

   def setUp(self):
      self.types = {"boolean": das.schematypes.Boolean(default=True),
                    "integer": das.schematypes.Integer(default=1),
                    "integerMin": das.schematypes.Integer(default=5, min=1),
                    "integerMax": das.schematypes.Integer(default=5, max=10),
                    "integerRange": das.schematypes.Integer(default=5, min=1, max=10),
                    "integerEnum": das.schematypes.Integer(default=1, enum={"enum1": 1, "enum2": 2, "enum3": 3}),
                    "real": das.schematypes.Real(default=0.5),
                    "realMin": das.schematypes.Real(default=0.5, min=-10),
                    "realMax": das.schematypes.Real(default=0.5, max=10),
                    "realRange": das.schematypes.Real(default=0.5, min=-10, max=10),
                    "string": das.schematypes.String(default="hello"),
                    "stringLooseChoices": das.schematypes.String(default="hello", choices=["hello", "goodbye"], strict=False),
                    "stringStrictChoices": das.schematypes.String(default="hello", choices=["hello", "goodbye"], strict=True),
                    "stringMatches": das.schematypes.String(default="v001", matches=r"v\d{3,}")}
      self.addCleanup(self.cleanUp)

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      pass

   # Test functions
   def testBoolean(self):
      for k0, v0 in self.types.iteritems():
         for k1, v1 in self.types.iteritems():
            if k1 == k0:
               continue
            print("%s / %s -> %s" % (k0, k1, v0.is_type_compatible(v1)))
