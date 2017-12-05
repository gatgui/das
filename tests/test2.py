import os
import sys
from pprint import pprint
import setup
import das

rv = das.read(setup.thisdir + "/shader.asset", schema="asset.TokenDict")
das.pprint(rv)

try:
   rv = das.read(setup.thisdir + "/error1.asset", schema="asset.TokenDict")
except Exception, e:
   print(str(e))

try:
   rv = das.read(setup.thisdir + "/error2.asset", schema="asset.TokenDict")
except Exception, e:
   print(str(e))
