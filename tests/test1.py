import os
import sys
from pprint import pprint
import setup
import das

print("=== Available schemas")
pprint(das.list_schemas())

print("=== 'hud' schema module content")
pprint(filter(lambda x: not (x.startswith("__") and x.endswith("__")), dir(das.schema.hud)))

print("=== Read data...")
hud = das.read("%s/test.hud" % setup.thisdir, schema="hud.HUD")
das.pprint(hud)

print("=== Write data...")
das.write(hud, "%s/out1.hud" % setup.thisdir)

print("=== Read written data...")
hud2 = das.read("%s/out1.hud" % setup.thisdir, schema="hud.HUD")
das.pprint(hud2)

print("=== Comparison")
print(hud == hud2)
print("--- Changed some value")
hud2.text.elements[2].opacity = 0.5
print(hud == hud2)

print("=== Write data with errors...")
hud2.text.elements[2].align = ("top", "left")
try:
   das.write(hud2, "%s/out2.hud" % setup.thisdir)
except Exception, e:
   print(e)
   print("--- Fix invalid data and write")
   hud2.text.elements[2].align = ("left", "top")
   das.write(hud2, "%s/out2.hud" % setup.thisdir)
   print("--- Read and compare again")
   hud3 = das.read("%s/out2.hud" % setup.thisdir, schema="hud.HUD")
   print(hud2 == hud3)
