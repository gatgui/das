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

print("=== timeline.ClipSource")
das.write(das.make_default("timeline.ClipSource"), "./out.tl")
tl = das.read("./out.tl")
das.pprint(tl)
print(tl._schema_type)
