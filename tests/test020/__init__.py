# -*- coding: utf8 -*-
import os
import unittest
import das
import das.mixin
import das.schematypes


class TestCase(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      pass

   def setUp(self):
      pass

   def tearDown(self):
      pass

   def cleanUp(self):
      pass

   @classmethod
   def tearDownClass(cls):
      pass

   # Test functions
   def testTuple(self):
      t_tup = das.schematypes.Tuple(das.schematypes.Real(), das.schematypes.Real())
      tup = t_tup.make_default()
      with self.assertRaises(das.ValidationError):
         tmp = tup + (20,)

   def testSequence(self):
      t_seq = das.schematypes.Sequence(das.schematypes.String(), min_size=1, max_size=3, default=["a"])

      seq = t_seq.make_default()
      ref = ["a"]

      # das.Sequence.__imul__
      with self.assertRaises(das.ValidationError):
         seq *= 4
      self.assertTrue(seq == ref)

      # das.Sequence.__mul__, __rmul__
      self.assertTrue(3 * seq == seq * 3)

      self.assertTrue(seq == ref)

      # das.Sequence.extend
      with self.assertRaises(das.ValidationError):
         seq.extend(["b", "c", "d", "e"])
      self.assertTrue(seq == ref)

      # das.Sequence.__iadd__
      with self.assertRaises(das.ValidationError):
         seq += ["b", "c", "d", "e"]
      self.assertTrue(seq == ref)

      # das.Sequence.pop
      with self.assertRaises(das.ValidationError):
         seq.pop(-1)
      self.assertTrue(seq == ref)

      seq += ["b", "c"]
      ref += ["b", "c"]

      # das.Sequence.append
      with self.assertRaises(das.ValidationError):
         seq.append("d")
      self.assertTrue(seq == ref)

      # das.Sequence.insert
      with self.assertRaises(das.ValidationError):
         seq.insert(-10, "9")
      self.assertTrue(seq == ref)

      # das.Sequence.__setslice__
      with self.assertRaises(das.ValidationError):
         seq[-10:2] = ["x", "y", "z"]
      self.assertTrue(seq == ref)

      seq[-10:2] = ["x", "y"]
      self.assertTrue(seq == ["x", "y", "c"])

      seq.remove("y")
      seq.remove("c")
      with self.assertRaises(das.ValidationError):
         seq.remove("x")
      self.assertTrue(seq == ["x"])

      seq.extend(["y", "z"])
      del(seq[:2])
      self.assertTrue(seq == ["z"])

   def testSet(self):
      ref = set(["a", "b", "c"])

      t_set = das.schematypes.Set(das.schematypes.String())
      s = t_set.make_default()

      with self.assertRaises(KeyError):
         s.pop()

      s |= ref

      item = s.pop()
      self.assertTrue((s | set([item])) == ref)

      s.add(item)
      self.assertTrue(s == ref)

      with self.assertRaises(das.ValidationError):
         s.add(20)
      self.assertTrue(s == ref)

      with self.assertRaises(das.ValidationError):
         s.update(["d", 3, "f"])
      self.assertTrue(s == ref)

      with self.assertRaises(das.ValidationError):
         s |= [1, 2, 3]
      self.assertTrue(s == ref)

      with self.assertRaises(das.ValidationError):
         s &= [1, 2, 3]
      self.assertTrue(s == ref)

      with self.assertRaises(das.ValidationError):
         s -= [1, 2, 3]
      self.assertTrue(s == ref)

      with self.assertRaises(das.ValidationError):
         s ^= [1, 2, 3]
      self.assertTrue(s == ref)

      s.clear()
      self.assertTrue(s == set())

   def testDict(self):
      t_dict = das.schematypes.Dict(ktype=das.schematypes.Tuple(das.schematypes.Integer(), das.schematypes.Integer()),
                                    vtype=das.schematypes.Sequence(das.schematypes.String()),
                                    __default__={(0, 0): ["a", "b", "c"]})

      class t_mixin(das.Mixin):
         def __init__(self, *args, **kwargs):
            super(t_mixin, self).__init__(*args, **kwargs)

         def _validate_globally(self):
            with das.GlobalValidationDisabled(self):
               if len(self) == 0:
                  raise Exception("No less than 1 key")
               elif len(self) > 3:
                  raise Exception("No more than 3 keys")
               for k, _ in self.iteritems():
                  x, y = k
                  if x < 0 or y < 0:
                     raise Exception("No negative numbers in key")

      dct = das.mixin.bind([t_mixin], t_dict.make_default(), force=True)

      with self.assertRaises(das.ValidationError):
         dct[(1.2, 3.1)] = []

      with self.assertRaises(KeyError):
         del(dct[(0, 1)])

      with self.assertRaises(das.ValidationError):
         del(dct[(1.2, 1.7)])

      with self.assertRaises(das.ValidationError):
         print(dct["hello"])

      with self.assertRaises(das.ValidationError):
         dct[(1, 1)] = "hello"

      with self.assertRaises(das.ValidationError):
         dct[(1, 1)] = "hello"

      dct[(1, 1)] = []

      with self.assertRaises(das.ValidationError):
         dct[(-1, 0)] = ["hello"]

      dct[(2, 2)] = ["back"]

      with self.assertRaises(das.ValidationError):
         dct[(3, 3)] = ["front"]

      self.assertTrue(dct.pop((4, 4), None) is None)

      self.assertFalse(dct.pop((0, 0), None) is None)

      dct.popitem()

      with self.assertRaises(das.ValidationError):
         dct.popitem()

      with self.assertRaises(das.ValidationError):
         dct.clear()

   def testStruct(self):
      t_struct = das.schematypes.Struct(
         opt=das.schematypes.Optional(das.schematypes.Boolean()),
         nopt=das.schematypes.Tuple(das.schematypes.Real(), das.schematypes.Real()))

      st = t_struct.make_default()

      with self.assertRaises(das.ValidationError):
         st.pop("nopt")

      st.opt = False

      self.assertTrue(st.pop("opt") is False)

      self.assertTrue(st.pop("opt", None) is None)

      with self.assertRaises(das.ValidationError):
         st.unknown = 2.0

      self.assertTrue(st == {"nopt": (0, 0)})

      with self.assertRaises(das.ValidationError):
         st.clear()

      with self.assertRaises(das.ValidationError):
         st.popitem()

      with self.assertRaises(das.ValidationError):
         st.update(opt=True, extra=20.0)

      self.assertTrue(st == {"nopt": (0, 0)})
