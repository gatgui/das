import os
import re
import sys
import datetime

__version__ = "1.1.0"

from .types import (ReservedNameError,
                    Struct,
                    Sequence)
from .schematypes import (ValidationError,
                          TypeValidator,
                          Boolean,
                          Integer,
                          Real,
                          String,
                          Sequence,
                          Tuple,
                          StaticDict,
                          DynamicDict,
                          Class,
                          Or,
                          Optional,
                          Empty,
                          SchemaType)
from .validation import (UnknownSchemaError,
                         Schema,
                         SchemaLocation,
                         SchemaTypesRegistry,
                         load_schemas,
                         list_schemas,
                         has_schema,
                         get_schema,
                         list_schema_types,
                         has_schema_type,
                         get_schema_type,
                         get_schema_type_name,
                         get_schema_path,
                         get_schema_module,
                         validate,
                         make_default)
from .fsets import (BindError,
                    SchemaTypeError,
                    FunctionSet)
from . import schema

# For backward compatibiilty
Das = Struct

def read_meta(path):
   md = {}
   mde = re.compile("^\s*([^:]+):\s*(.*)\s*$")
   with open(path, "r") as f:
      for l in f.readlines():
         l = l.strip()
         if l.startswith("#"):
            m = mde.match(l[1:])
            if m is not None:
               md[m.group(1)] = m.group(2)
         else:
            break
   return md


def read(path, schema_type=None, ignore_meta=False, **funcs):
   # Read header data
   md = {}
   if not ignore_meta:
      md = read_meta(path)

   if schema_type is None:
      schema_type = md.get("schema_type", None)

   if schema_type is not None:
      sch = get_schema_type(schema_type)
      mod = get_schema_module(schema_type)
      if mod is not None and hasattr(mod, "__all__"):
         for item in mod.__all__:
            funcs[item] = getattr(mod, item)
   else:
      sch, mod = None, None

   # if sch is defined, lookup for class override
   rv = Das()
   with open(path, "r") as f:
      rv._update(**eval(f.read(), globals(), funcs))

   rv._validate(sch)

   return rv


def copy(d, deep=True):
   if not deep:
      return d._copy()
   else:
      rv = Das(d._dict)
      for k, v in rv._dict.items():
         if isinstance(v, Das):
            rv._dict[k] = copy(v, deep=True)
      return rv


def pprint(d, stream=None, indent="  ", depth=0, inline=False, eof=True):
   if stream is None:
      stream = sys.stdout

   tindent = indent * depth

   if not inline:
      stream.write(tindent)

   if isinstance(d, (dict, Das)):
      stream.write("{\n")
      n = len(d)
      i = 0
      keys = [k for k in d]
      keys.sort()
      for k in keys:
         stream.write("%s%s'%s': " % (tindent, indent, k))
         v = d[k]
         pprint(v, stream, indent=indent, depth=depth+1, inline=True, eof=False)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s}" % tindent)

   elif isinstance(d, list):
      stream.write("[\n")
      n = len(d)
      i = 0
      for v in d:
         pprint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s]" % tindent)

   elif isinstance(d, set):
      stream.write("set([\n")
      n = len(d)
      i = 0
      for v in d:
         pprint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s])" % tindent)

   elif isinstance(d, (str, unicode)):
      stream.write("'%s'" % d)

   else:
      stream.write(str(d))

   if eof:
      stream.write("\n")


def write(d, path, indent="  "):
   # Validate before writing
   d._validate()
   with open(path, "w") as f:
      f.write("# version: %s\n" % __version__)
      f.write("# author: %s\n" % os.environ["USER" if sys.platform != "win32" else "USER"])
      f.write("# date: %s\n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
      if d._schema_type:
         st = get_schema_type_name(d._schema_type)
         f.write("# schema_type: %s\n" % st)
      pprint(d, stream=f, indent=indent)
