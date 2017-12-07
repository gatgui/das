import os
import sys

thisdir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(thisdir, "..", "python"))
os.environ["DAS_SCHEMA_PATH"] = "%s/test001%s%s/test002" % (thisdir, os.pathsep, thisdir)

import das

stl = das.list_schema_types("hud")

for st in stl:
   print("=== %s" % st)
   v = das.make_default(st)
   print(type(v).__name__)
   das.pprint(v)
