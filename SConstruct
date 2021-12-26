import os
import sys
import excons

env = excons.MakeBaseEnv()

env.SConscript("Qute/SConstruct")

version = None

sys.path.insert(0, os.getcwd() + "/python")
try:
   import das
   version = das.__version__
except Exception as e:
   print("Can't figure out DaS version (%s)" % e)

prjs = [
   {  "name": "das",
      "type": "install",
      "install": {
         "bin": excons.glob("bin/das*"),
         "python/das": excons.glob("python/das/*.py"),
         "python/das/importlib-1.0.4": excons.glob("python/das/importlib-1.0.4/*")
      }
   }
]

excons.DeclareTargets(env, prjs)

excons.EcosystemDist(env, "das.env", {"das": excons.OutputBaseDirectory()}, version=version)
