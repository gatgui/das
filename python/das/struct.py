import os
import re
import sys
import datetime
import das

__all__ = ["Das",
           "ReservedNameError",
           "read_meta",
           "read",
           "copy",
           "pprint",
           "write"]

# ---

class ReservedNameError(Exception):
   def __init__(self, name):
      super(ReservedNameError, self).__init__("'%s' is a reserved name" % name)


class Das(object):
   def __init__(self, *args, **kwargs):
      super(Das, self).__init__()
      self.__dict__["_dict"] = {}
      self.__dict__["_schema_type"] = None
      self._update(*args, **kwargs)

   def __getattr__(self, k):
      try:
         return self._dict[k]
      except KeyError:
         if hasattr(self._dict, k):
            # Look for an override method of the same name prefixed by '_' in current class
            k2 = '_' + k
            if hasattr(self, k2):
               #print("Forward '%s' to %s class '%s'" % (k, self.__class__.__name__, k2))
               return getattr(self, k2)
            else:
               #print("Forward '%s' to dict class '%s'" % (k, k))
               return getattr(self._dict, k)
         else:
            raise AttributeError("'Das' has not attribute '%s' (dict %s)" % (k, "has" if hasattr(self._dict, k) else "hasn't"))

   def __setattr__(self, k, v):
      self._check_reserved(k)
      self._dict[k] = v

   def __delattr__(self, k):
      del(self._dict[k])

   def __getitem__(self, k):
      return self._dict.__getitem__(k)

   def __setitem__(self, k, v):
      self._check_reserved(k)
      self._dict.__setitem__(k, v)

   def __delitem__(self, k):
      return self._dict.__delitem__(k)

   def __contains__(self, k):
      return self._dict.__contains__(k)

   def __cmp__(self, oth):
      return self._dict.__cmp__(oth._dict if isinstance(oth, Das) else oth)

   def __eq__(self, oth):
      return self._dict.__eq__(oth._dict if isinstance(oth, Das) else oth)

   def __ge__(self, oth):
      return self._dict.__ge__(oth._dict if isinstance(oth, Das) else oth)

   def __le__(self, oth):
      return self._dict.__le__(oth._dict if isinstance(oth, Das) else oth)

   def __gt__(self, oth):
      return self._dict.__gt__(oth._dict if isinstance(oth, Das) else oth)

   def __lt__(self, oth):
      return self._dict.__lt__(oth._dict if isinstance(oth, Das) else oth)

   def __iter__(self):
      return self._dict.__iter__()

   def __len__(self):
      return self._dict.__len__()

   def __str__(self):
      return self._dict.__str__()

   def __repr__(self):
      return self._dict.__repr__()

   # Override of dict.copy
   def _copy(self):
      return self.__class__(self._dict.copy())

   # Override of dict.setdefault
   def _setdefault(self, *args):
      if len(args) >= 1:
         self._check_reserved(args[0])
      if len(args) >= 2:
         args[1] = self._adapt_value(args[1])
      self._dict.setdefault(*args)

   # Override of dict.update
   def _update(self, *args, **kwargs):
      self._dict.update(*args, **kwargs)
      for k, v in self._dict.items():
         self._check_reserved(k)
         self._dict[k] = self._adapt_value(v)

   def _check_reserved(self, k):
      if hasattr(self.__class__, k):
         raise ReservedNameError(k)
      elif hasattr(self._dict, k):
         if "_" + k in self.__dict__:
            raise ReservedNameError(k)
         print("'%s' key conflicts with existing method of dict class, use '_%s()' to call it instead" % (k, k))
         self.__dict__["_" + k] = getattr(self._dict, k)

   def _adapt_value(self, value):
      if isinstance(value, dict):
         return Das(**value)
      elif isinstance(value, (tuple, list, set)):
         n = len(value)
         l = [None] * n
         i = 0
         for item in value:
            l[i] = self._adapt_value(item)
            i += 1
         return type(value)(l)
      else:
         return value

   def _validate(self, schema_type=None):
      if schema_type is None:
         schema_type = self.__dict__["_schema_type"]
      if schema_type is not None:
         schema_type.validate(self)
      self._set_schema_type(schema_type)

   def _set_schema_type(self, schema_type):
      self.__dict__["_schema_type"] = schema_type
      

# ---

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
      sch = das.validation.get_schema_type(schema_type)
      mod = das.validation.get_schema_module(schema_type)
      if mod is not None and hasattr(mod, "__all__"):
         for item in mod.__all__:
            funcs[item] = getattr(mod, item)
   else:
      sch, mod = None, None

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
      f.write("# version: %s\n" % das.__version__)
      f.write("# author: %s\n" % os.environ["USER" if sys.platform != "win32" else "USER"])
      f.write("# date: %s\n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
      if d._schema_type:
         st = das.validation.get_schema_type_name(d._schema_type)
         f.write("# schema_type: %s\n" % st)
      pprint(d, stream=f, indent=indent)

