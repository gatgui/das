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

class ClipSource(das.FunctionSet):
   def __init__(self):
      super(ClipSource, self).__init__("timeline.ClipSource")

   def setMedia(self, path):
      _, ext = map(lambda x: x.lower(), os.path.splitext(path))
      if ext == ".fbx":
         print("Get range from FBX file")
      elif ext == ".abc":
         print("Get range from Alembic file")
      elif ext == ".mov":
         print("Get range from Movie file")
      self.data.media = os.path.abspath(path).replace("\\", "/")

   def setClipOffsets(self, start, end):
      dataStart, dataEnd = self.data.dataRange
      clipStart = min(dataEnd, dataStart + max(0, start))
      clipEnd = max(dataStart, dataEnd + min(end, 0))
      if clipStart == dataStart and clipEnd == dataEnd:
         self.data.clipRange = None
      else:
         self.data.clipRange = (clipStart, clipEnd)

das.write(das.make_default("timeline.ClipSource"), "./out.tl")
cs = ClipSource()
cs.read("./out.tl")
cs.pprint()
cs.data.dataRange = (100, 146)
cs.setMedia("./source.mov")
cs.setClipOffsets(1, -1)
cs.pprint()
cs.write("./out.tl")
print(type(cs.copy()))
cs.copy().pprint()
c = das.copy(cs.data)
print(type(c.copy()))
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
