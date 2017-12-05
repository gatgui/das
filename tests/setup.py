import os
import sys

thisdir = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(0, os.path.join(thisdir, "../python"))

os.environ["DAS_SCHEMA_PATH"] = thisdir
