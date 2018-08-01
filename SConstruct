import os
import sys
import excons

env = excons.MakeBaseEnv()

version = None

sys.path.insert(0, os.getcwd() + "/python")
try:
   import das
   version = das.__version__
except Exception, e:
   print("Can't figure out DaS version (%s)" % e)

prjs = [
   {  "name": "das",
      "type": "install",
      "install": {
         "python/das": excons.glob("python/das/*.py"),
         "python/das/importlib-1.0.4": excons.glob("python/das/importlib-1.0.4/*")
      }
   }
]

excons.DeclareTargets(env, prjs)

targets = {"das": Glob(excons.OutputBaseDirectory() + "/python/*")}
ecodirs = {"das": "/python"}
excons.EcosystemDist(env, "das.env", ecodirs, version=version, targets=targets)

Default(["das"])
