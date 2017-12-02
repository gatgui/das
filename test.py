import os
import sys

pydir = os.path.join(os.path.dirname(__file__), "python")

sys.path.insert(0, pydir)
os.environ["DAS_SCHEMA_PATH"] = os.path.join(pydir, "DaS", "schemas")

import DaS

class HUD(object):
   @staticmethod
   def attribute(value):
      return value

hud = DaS.Read("test.hud", attribute=HUD.attribute)
print(hud)

#hud = DaS.HUD("test.hud")
#print(hud)
