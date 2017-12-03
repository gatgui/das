import os
import sys

# Setup environment for tests
pydir = os.path.join(os.path.dirname(__file__), "python")

sys.path.insert(0, pydir)
os.environ["DAS_SCHEMA_PATH"] = os.path.join(pydir, "DaS", "schemas")

# Test code
import DaS

class Attribute(object):
   def __init__(self, attr):
      super(Attribute, self).__init__()
      self.attr = attr

   def __str__(self):
      return "attribute('%s')" % self.attr

   def __repr__(self):
      return "attribute('%s')" % self.attr

   def __cmp__(self, oth):
      s0 = str(self)
      s1 = str(oth)
      return (-1 if (s0 < s1) else (0 if (s0 == s1) else 1))


def attribute(value):
   return Attribute(value)

hud = DaS.Read("test.hud", attribute=attribute)
DaS.PrettyPrint(hud)
DaS.Write(hud, "out.hud")
hud2 = DaS.Read("out.hud", attribute=attribute)
print(hud2 == hud)

sch = DaS.Read("python/DaS/schemas/HUD.schema",
               Boolean=DaS.Boolean,
               Integer=DaS.Integer,
               Real=DaS.Real,
               String=DaS.String,
               Sequence=DaS.Sequence,
               Class=DaS.Class,
               Or=DaS.Or,
               Attribute=Attribute)
DaS.PrettyPrint(sch)
