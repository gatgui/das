import os
import re
import sys
import datetime

__version__ = "0.3.0"

from .types import (ReservedNameError,
                    TypeBase,
                    Tuple,
                    Sequence,
                    Set,
                    Dict,
                    Struct)
from .schematypes import ValidationError
from .validation import (UnknownSchemaError,
                         Schema,
                         SchemaLocation,
                         SchemaTypesRegistry)
from .mixin import (SchemaTypeError,
                    BindError,
                    Mixin,
                    bind,
                    has_bound_mixins,
                    get_bound_mixins)
from . import schema

# For backward compatibiilty
Das = Struct


def load_schemas(paths=None):
   SchemaTypesRegistry.instance.load_schemas(paths=paths)


def list_schemas():
   return SchemaTypesRegistry.instance.list_schemas()


def has_schema():
   return SchemaTypesRegistry.instance.has_schema()


def get_schema(name):
   return SchemaTypesRegistry.instance.get_schema(name)


def list_schema_types(schema=None):
   return SchemaTypesRegistry.instance.list_schema_types(schema)


def has_schema_type(name):
   return SchemaTypesRegistry.instance.has_schema_type(name)


def get_schema_type(name):
   return SchemaTypesRegistry.instance.get_schema_type(name)


def get_schema_type_name(typ):
   return SchemaTypesRegistry.instance.get_schema_type_name(typ)


def register_mixins(*mixins):
   print("[das] Register mixins: %s" % ", ".join(map(lambda x: x.__module__ + "." + x.__name__, mixins)))
   tmp = {}
   for mixin in mixins:
      st = mixin.get_schema_type()
      lst = tmp.get(st, [])
      lst.append(mixin)
      tmp[st] = lst
   for k, v in tmp.iteritems():
      SchemaTypesRegistry.instance.set_schema_type_property(k, "mixins", v)


def get_registered_mixins(name):
   return SchemaTypesRegistry.instance.get_schema_type_property(name, "mixins")


def get_schema_path(name):
   return SchemaTypesRegistry.instance.get_schema_path(name)


def get_schema_module(name):
   return SchemaTypesRegistry.instance.get_schema_module(name)


def make_default(name):
   return SchemaTypesRegistry.instance.make_default(name)


def adapt_value(value, schema_type=None, key=None, index=None):
   if schema_type:
      return schema_type.validate(value, key=key, index=index)
   else:
      if isinstance(value, TypeBase):
         return value
      elif isinstance(value, dict):
         try:
            rv = Struct(**value)
         except ReservedNameError, e:
            # If failed to create Struct because of a ReservedNameError exception, wrap using Dict class
            rv = Dict(**value)
         return rv
      else:
         klass = None
         if isinstance(value, tuple):
            klass = Tuple
         elif isinstance(value, list):
            klass = Sequence
         elif isinstance(value, set):
            klass = Set
         if klass is not None:
            n = len(value)
            l = [None] * n
            i = 0
            for item in value:
               l[i] = adapt_value(item)
               i += 1
            return klass(l)
         else:
            return value


def validate(d, schema):
   get_schema_type(schema).validate(d)


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

   with open(path, "r") as f:
      rv = eval(f.read(), globals(), funcs)

   return (rv if sch is None else sch.validate(rv))


def copy(d, deep=True):
   if isinstance(d, list):
      if deep:
         rv = d.__class__([copy(x, deep=True) for x in d])
      else:
         rv = d.__class__(d[:])
   elif isinstance(d, tuple):
      if deep:
         rv = d.__class__([copy(x, deep=True) for x in d])
      else:
         rv = d.__class__(d[:])
   elif isinstance(d, set):
      if deep:
         rv = d.__class__([copy(x, deep=True) for x in d])
      else:
         rv = d.__class__([x for x in d])
   elif isinstance(d, dict):
      if deep:
         rv = d.__class__()
         for k, v in d.iteritems():
            rv[k] = copy(v, deep=True)
      else:
         rv = d.copy()
   elif isinstance(d, Struct):
      if deep:
         rv = d.__class__()
         for k, v in d._dict.iteritems():
            rv[k] = copy(v, deep=True)
      else:
         rv = d._copy()
   elif hasattr(d, "copy") and callable(getattr(d, "copy")):
      rv = d.copy()
   else:
      rv = d
   if isinstance(rv, TypeBase) and isinstance(d, TypeBase):
      rv._set_schema_type(d._get_schema_type())
   return rv


def pprint(d, stream=None, indent="  ", depth=0, inline=False, eof=True):
   if stream is None:
      stream = sys.stdout

   tindent = indent * depth

   if not inline:
      stream.write(tindent)

   if isinstance(d, (dict, Struct)):
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
   d._validate()

   schema_type = d._get_schema_type()

   with open(path, "w") as f:
      f.write("# version: %s\n" % __version__)
      f.write("# author: %s\n" % os.environ["USER" if sys.platform != "win32" else "USER"])
      f.write("# date: %s\n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
      if schema_type:
         st = get_schema_type_name(schema_type)
         f.write("# schema_type: %s\n" % st)
      pprint(d, stream=f, indent=indent)


# Utilities

_PrintedMsgs = set()

def print_once(msg):
   global _PrintedMsgs
   if msg in _PrintedMsgs:
      return
   print(msg)
   _PrintedMsgs.add(msg)
