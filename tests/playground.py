import os
import re
import sys
import glob

thisdir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(thisdir, "..", "python"))
dirs = map(lambda y: thisdir + "/" + y, filter(lambda x: re.match("test\d+", x), os.listdir(thisdir)))
os.environ["DAS_SCHEMA_PATH"] = os.pathsep.join(dirs)

import das

stl = das.list_schema_types("hud")

for st in stl:
   print("=== %s" % st)
   v = das.make_default(st)
   print(type(v).__name__)
   das.pprint(v)
   if hasattr(v, "_schema_type"):
      print(v._schema_type)

print("=== FunctionSet tests using timeline.ClipSource schema type ===")

class Range(das.FunctionSet):
   def __init__(self, data=None, validate=True):
      # Make sure to initialize before calling base class constructor that will
      # in turn call get_schema_type
      self.schema_type = das.get_schema_type("timeline.Range")
      super(Range, self).__init__(data=data, validate=validate)

   def get_schema_type(self):
      return self.schema_type

   def __iter__(self):
      return iter(self.data)

   def __getitem__(self, idx):
      return self.data[idx]

   def extend(self, start, end):
      cs, ce = self.data
      if start < cs:
         cs = start
      if end > ce:
         ce = end
      self.data = (cs, ce)


class ClipSource(das.FunctionSet):
   def __init__(self, data=None, validate=True):
      # Make sure to initialize before calling base class constructor that will
      # in turn call get_schema_type
      self.schema_type = das.get_schema_type("timeline.ClipSource")
      super(ClipSource, self).__init__(data=data, validate=validate)

   def get_schema_type(self):
      return self.schema_type

   @property
   def media(self):
      return self.data.media

   @media.setter
   def media(self, value):
      self.data.media = value

   @property
   def dataRange(self):
      return self.data.dataRange

   @dataRange.setter
   def dataRange(self, value):
      self.data.dataRange = value

   @property
   def clipRange(self):
      return self.data.clipRange

   @clipRange.setter
   def clipRange(self, value):
      self.data.clipRange = value

   def set_media(self, path):
      _, ext = map(lambda x: x.lower(), os.path.splitext(path))
      if ext == ".fbx":
         print("Get range from FBX file")
      elif ext == ".abc":
         print("Get range from Alembic file")
      elif ext == ".mov":
         print("Get range from Movie file")
      self.media = os.path.abspath(path).replace("\\", "/")

   def set_clip_offsets(self, start, end):
      data_start, data_end = self.dataRange
      clip_start = min(data_end, data_start + max(0, start))
      clip_end = max(data_start, data_end + min(end, 0))
      if clip_start == data_start and clip_end == data_end:
         self.clipRange = None
      else:
         self.clipRange = (clip_start, clip_end)

das.set_schema_type_function_set("timeline.Range", Range)
das.set_schema_type_function_set("timeline.ClipSource", ClipSource)

print("-- make def (1)")
dv = das.make_default("timeline.ClipSource")
print("-- write (1)")
das.write(dv, "./out.tl")
print("-- make def (2)")
cs = das.make_default("timeline.ClipSource")
print("-- read (1)")
cs = das.read("./out.tl")
print("-- read (2)")
cs.read("./out.tl")
cs.pprint()
cs.dataRange = (100, 146)
cs.dataRange.extend(102, 150)
cs.set_media("./source.mov")
cs.set_clip_offsets(1, -1)
cs.pprint()
print("-- write (2)")
cs.write("./out.tl")
cs.copy().pprint()
c = das.copy(cs.data)
for k, v in c.iteritems():
   print("%s = %s" % (k, v))
os.remove("./out.tl")

print("=== Name conflict resolution ===")
d = das.make_default("conflicts.DictMethod")
das.pprint(d)
print("keys = %s" % d.keys)
print("_keys() -> %s" % d._keys())
print("values = %s" % d.values)
print("_values() -> %s" % d._values())
print("items() -> %s" % d.items())
for k, v in d.items():
   print("%s = %s" % (k, v))
das.pprint(d)
d._clear()
das.pprint(d)
