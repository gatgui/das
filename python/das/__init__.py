import os
import re
import sys
import datetime

__version__ = "0.5.0"

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


def make(_schema_type_name, *args, **kwargs):
   return SchemaTypesRegistry.instance.make(_schema_type_name, *args, **kwargs)


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
   return get_schema_type(schema).validate(d)


def _read_file(path, skip_content=False):
   mde = re.compile("^\s*([^:]+):\s*(.*)\s*$")
   reading_content = False
   content = ""
   md = {}
   if os.path.isfile(path):
      with open(path, "rb") as f:
         for l in f.readlines():
            sl = l.strip()
            if sl.startswith("#"):
               if not reading_content:
                  m = mde.match(sl[1:])
                  if m is not None:
                     md[m.group(1)] = m.group(2)
            else:
               reading_content = True
               if skip_content:
                  break
               else:
                  # Convert line endings to LF on the fly
                  content += l.rstrip() + "\n"
   return md, content


def read_meta(path):
   return _read_file(path, skip_content=True)[0]


def decode(d, encoding):
   if isinstance(d, list):
      rv = d.__class__([decode(x, encoding) for x in d])
   elif isinstance(d, tuple):
      rv = d.__class__([decode(x, encoding) for x in d])
   elif isinstance(d, set):
      rv = d.__class__([decode(x, encoding) for x in d])
   elif isinstance(d, dict):
      rv = d.__class__()
      for k, v in d.iteritems():
         rv[k] = decode(v, encoding)
   elif isinstance(d, Struct):
      rv = d.__class__()
      for k, v in d._dict.iteritems():
         rv[k] = decode(v, encoding)
   elif isinstance(d, str):
      try:
         d.decode("ascii")
         return d
      except:
         rv = d.decode(encoding)
         return rv
   elif isinstance(d, unicode):
      try:
         return d.encode("ascii")
      except:
         return d
   elif hasattr(d, "_decode") and callable(getattr(d, "_decode")):
      rv = d._decode(encoding)
   else:
      rv = d
   return rv


def read_string(s, schema_type=None, encoding=None, **funcs):
   if schema_type is not None:
      sch = get_schema_type(schema_type)
      mod = get_schema_module(schema_type)
      if mod is not None and hasattr(mod, "__all__"):
         for item in mod.__all__:
            funcs[item] = getattr(mod, item)
   else:
      sch, mod = None, None

   if not encoding:
      print("[das] Warning: No encoding specified, using system's default.")
   else:
      s = ("# encoding: %s\n" % encoding) + s

   rv = eval(s, globals(), funcs)

   if encoding:
      rv = decode(rv, encoding)

   return (rv if sch is None else sch.validate(rv))


def read(path, schema_type=None, ignore_meta=False, **funcs):
   # Read header data
   md, src = _read_file(path)

   if schema_type is None and not ignore_meta:
      schema_type = md.get("schema_type", None)

   encoding = md.get("encoding", None)

   return read_string(src, schema_type=schema_type, encoding=encoding, **funcs)


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


def pprint(d, stream=None, indent="  ", depth=0, inline=False, eof=True, encoding=None):
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
         # We assume string keys are 'ascii'
         if isinstance(k, unicode):
            try:
               k = k.encode("ascii")
            except:
               raise Exception("Non-ascii keys are not supported!")
         elif isinstance(k, str):
            try:
               k.decode("ascii")
            except:
               raise Exception("Non-ascii keys are not supported!")
         stream.write("%s%s'%s': " % (tindent, indent, k))
         v = d[k]
         pprint(v, stream, indent=indent, depth=depth+1, inline=True, eof=False, encoding=encoding)
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
         pprint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False, encoding=encoding)
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
         pprint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False, encoding=encoding)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s])" % tindent)

   elif isinstance(d, str):
      try:
         d.decode("ascii")
         stream.write("'%s'" % d)
      except Exception, e:
         if not encoding:
            raise Exception("Non-ascii string value found but no encoding provided (%s)." % e)
         try:
            stream.write(repr(d.decode(encoding)))
         except Exception, e:
            raise Exception("Non-ascii string value cannot be decoded to '%s' (%s)." % (encoding, e))

   elif isinstance(d, unicode):
      try:
         s = d.encode("ascii")
         stream.write("'%s'" % s)
      except:
         stream.write(repr(d))

   else:
      stream.write(str(d))

   if eof:
      stream.write("\n")


def write(d, path, indent="  ", encoding=None):
   d._validate()

   schema_type = d._get_schema_type()

   if encoding is None:
      print("[das] Warning: Assuming UTF-8 encoding for non-unicode strings.")
      encoding = "utf8"

   with open(path, "wb") as f:
      f.write("# encoding: %s\n" % encoding)
      f.write("# version: %s\n" % __version__)
      f.write("# author: %s\n" % os.environ["USER" if sys.platform != "win32" else "USERNAME"])
      f.write("# date: %s\n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
      if schema_type:
         st = get_schema_type_name(schema_type)
         f.write("# schema_type: %s\n" % st)
      pprint(d, stream=f, indent=indent, encoding=encoding)


# Utilities

_PrintedMsgs = set()

def print_once(msg):
   global _PrintedMsgs
   if msg in _PrintedMsgs:
      return
   print(msg)
   _PrintedMsgs.add(msg)
