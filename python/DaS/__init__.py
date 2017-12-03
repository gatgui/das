import os
import sys
import glob



ReservedNames = set(['_is_reserved',
                     '_adapt_value',
                     '_update',
                     '_has_key',
                     '_get',
                     '_keys',
                     '_iterkeys',
                     '_values',
                     '_itervalues',
                     '_items',
                     '_iteritems',
                     '_pop',
                     '_popitem',
                     '_clear',
                     '_copy',
                     '_setdefault'])

ExceptOnReservedNameUsage = True

Schemas = {}


class ReservedNameError(Exception):
   def __init__(self, name):
      super(ReservedNameError, self).__init__("'%s' is a reserved name" % name)

class UnknownSchemaError(Exception):
   def __init__(self, name):
      super(UnknownSchemaError, self).__init__("'%s' is not a known schema" % name)


class DaS(object):
   def __init__(self, *args, **kwargs):
      super(DaS, self).__init__()
      self.__dict__["_dict"] = {}
      self._update(*args, **kwargs)

   def __getattr__(self, k):
      #return self._dict.get(k, None)
      try:
         return self._dict[k]
      except KeyError:
         raise AttributeError("'DaS' has not attribute '%s'" % k)

   def __setattr__(self, k, v):
      if not self._is_reserved(k):
         self._dict[k] = v

   def __delattr__(self, k):
      del(self._dict[k])

   def __getitem__(self, k):
      return self._dict.__getitem__(k)

   def __setitem__(self, k, v):
      if not self._is_reserved(k):
         self._dict.__setitem__(k, v)

   def __delitem__(self, k):
      return self._dict.__delitem__(k)

   def __contains__(self, k):
      return self._dict.__contains__(k)

   def __cmp__(self, oth):
      return self._dict.__cmp__(oth._dict if isinstance(oth, DaS) else oth)

   def __eq__(self, oth):
      return self._dict.__eq__(oth._dict if isinstance(oth, DaS) else oth)

   def __ge__(self, oth):
      return self._dict.__ge__(oth._dict if isinstance(oth, DaS) else oth)

   def __le__(self, oth):
      return self._dict.__le__(oth._dict if isinstance(oth, DaS) else oth)

   def __gt__(self, oth):
      return self._dict.__gt__(oth._dict if isinstance(oth, DaS) else oth)

   def __lt__(self, oth):
      return self._dict.__lt__(oth._dict if isinstance(oth, DaS) else oth)

   def __iter__(self):
      return self._dict.__iter__()

   def __len__(self):
      return self._dict.__len__()

   def __str__(self):
      return self._dict.__str__()

   def __repr__(self):
      return self._dict.__repr__()

   def _has_key(self, k):
      return self._dict.has_key(k)

   def _get(self, k, default=None):
      return self._dict.get(k, default)

   def _keys(self):
      return self._dict.keys()

   def _iterkeys(self):
      return self._dict.iterkeys()

   def _values(self):
      return self._dict.values()

   def _itervalues(self):
      return self._dict.itervalues()

   def _items(self):
      return self._dict.items()

   def _iteritems(self):
      return self._dict.iteritems()

   def _pop(self, *args):
      return self._dict.pop(*args)

   def _popitem(self):
      return self._dict.popitem()

   def _clear(self):
      self._dict.clear()

   def _copy(self):
      return DaS(self._dict.copy())

   def _setdefault(self, *args):
      if len(args) >= 1:
         if self._is_reserved(args[0]):
            return
      if len(args) >= 2:
         args[1] = self._adapt_value(args[1])
      self._dict.setdefault(*args)

   def _update(self, *args, **kwargs):
      self._dict.update(*args, **kwargs)
      for k, v in self._dict.items():
         if not self._is_reserved(k):
            self._dict[k] = self._adapt_value(v)

   def _is_reserved(self, k):
      if k in ReservedNames:
         e = ReservedNameError(k)
         if ExceptOnReservedNameUsage:
            raise e
         else:
            print("[DaS] %s" % e)
            return True
      else:
         return False

   def _adapt_value(self, value):
      t = type(value)
      if t == dict:
         return DaS(**value)
      elif t in (list, set, tuple):
         n = len(value)
         l = [None] * n
         i = 0
         for item in value:
            l[i] = self._adapt_value(item)
            i += 1
         return t(l)
      else:
         return value

# ---

def Copy(d, deep=True):
   if not deep:
      return d._copy()
   else:
      rv = DaS(d._dict)
      for k, v in rv._dict.items():
         if isinstance(v, DaS):
            rv._dict[k] = Copy(v, deep=True)
      return rv

def PrettyPrint(d, stream=None, indent="  ", depth=0, inline=False, eof=True):
   if stream is None:
      stream = sys.stdout

   tindent = indent * depth

   if not inline:
      stream.write(tindent)

   t = type(d)

   if t in (DaS, dict):
      stream.write("{\n")
      n = len(d)
      i = 0
      for k in d:
         stream.write("%s%s'%s': " % (tindent, indent, k))
         v = d[k]
         PrettyPrint(v, stream, indent=indent, depth=depth+1, inline=True, eof=False)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s}" % tindent)

   elif t == list:
      stream.write("[\n")
      n = len(d)
      i = 0
      for v in d:
         PrettyPrint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s]" % tindent)

   elif t == set:
      stream.write("set([\n")
      n = len(d)
      i = 0
      for v in d:
         PrettyPrint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s])" % tindent)

   elif t in (str, unicode):
      stream.write("'%s'" % d)

   else:
      stream.write(str(d))

   if eof:
      stream.write("\n")

def Read(path, **funcs):
   rv = DaS()
   with open(path, "r") as f:
      rv._update(**eval(f.read(), globals(), funcs))
   return rv

def Write(d, path, indent="  "):
   with open(path, "w") as f:
      PrettyPrint(d, stream=f, indent=indent)

# === Validation 

class TypeValidator(object):
   def __init__(self):
      super(TypeValidator, self).__init__()

   def validate(self, data):
      return False

   def __str__(self):
      return self.__repr__()

class Boolean(TypeValidator):
   def __init__(self, default=False):
      super(Boolean, self).__init__()
      self.default = bool(default)

   def validate(self, data):
      return isinstance(data, bool)

   def __repr__(self):
      s = "Boolean(";
      if self.default is True:
         s += "default=%s" % self.default
      return s + ")"

class Integer(TypeValidator):
   def __init__(self, default=0, min=None, max=None):
      super(Integer, self).__init__()
      self.default = long(default)
      self.min = min
      self.max = max

   def validate(self, data):
      if not type(data) in (int, long):
         return False
      if self.min is not None and data < self.min:
         return False
      if self.max is not None and data > self.max:
         return False
      return True

   def __repr__(self):
      s = "Integer(";
      sep = ""
      if self.default is not None and self.default != 0:
         s += "default=%s" % self.default
         sep = ", "
      if self.min is not None:
         s += "%smin=%d" % (sep, self.min)
         sep = ", "
      if self.max is not None:
         s += "%smax=%d" % (sep, self.max)
      return s + ")"

class Real(TypeValidator):
   def __init__(self, default=0.0, min=None, max=None):
      super(Real, self).__init__()
      self.default = float(default)
      self.min = min
      self.max = max

   def validate(self, data):
      if not type(data) in (int, long, float):
         return False
      if self.min is not None and data < self.min:
         return False
      if self.max is not None and data > self.max:
         return False
      return True

   def __repr__(self):
      s = "Real(";
      sep = ""
      if self.default is not None and self.default != 0.0:
         s += "default=%s" % self.default
         sep = ", "
      if self.min is not None:
         s += "%smin=%d" % (sep, self.min)
         sep = ", "
      if self.max is not None:
         s += "%smax=%d" % (sep, self.max)
      return s + ")"

class String(TypeValidator):
   def __init__(self, default="", choices=None):
      super(String, self).__init__()
      self.default = str(default)
      self.choices = choices

   def validate(self, data):
      if not type(data) in (str, unicode):
         return False
      if self.choices is not None and not data in self.choices:
         return False
      return True

   def __repr__(self):
      s = "String(";
      sep = ""
      if self.default is not None and self.default != "":
         s += "default='%s'" % self.default
         sep = ", "
      if self.choices is not None:
         s += "%schoices=[" % sep
         sep = ""
         for c in self.choices:
            s += "%s'%s'" % (sep, c)
            sep = ", "
      return s + ")"

class Sequence(TypeValidator):
   def __init__(self, type, default=[], size=None, min_size=None, max_size=None):
      super(Sequence, self).__init__()
      self.default = list(default)
      self.size = size
      self.min_size = min_size
      self.max_size = max_size
      self.elementType = type

   def validate(self, data):
      if not type(data) in (tuple, list, set):
         return False
      n = len(data)
      if self.size is not None:
         if n != self.size:
            return False
      else:
         if self.min_size is not None and n < self.min_size:
            return False
         if self.max_size is not None and n > self.max_size:
            return False
      return True

   def __repr__(self):
      s = "Sequence(type=%s" % self.elementType
      sep = ", "
      if self.default is not None and len(self.default) > 0:
         s += "%sdefault=%s" % (sep, self.default)
      if self.size is not None:
         s += "%ssize=%d" % (sep, self.size)
      else:
         if self.min_size is not None:
            s += "%smin_size=%d" % (sep, self.min_size)
         if self.max_size is not None:
            s += "%smax_size=%d" % (sep, self.max_size)
      return s + ")"

class Class(TypeValidator):
   def __init__(self, klass):
      super(Class, self).__init__()
      self.klass = klass

   def validate(self, data):
      return isinstance(data, self.klass)

   def __repr__(self):
      return "Class(%s)" % self.klass.__name__

class Or(TypeValidator):
   def __init__(self, type1, type2):
      super(Or, self).__init__()
      self.type1 = type1
      self.type2 = type2

   def validate(self, data):
      return (self.type1.validate(data) or self.type2.validate(data))

   def __repr__(self):
      return "Or(%s, %s)" % (self.type1, self.type2)


def Validate(d, schema):
   found = Schemas.get(schema)
   if found is None:
      p = os.environ.get("DAS_SCHEMA_PATH", None)
      if p is None:
         raise UnknownSchemaError(schema)
      else:
         pl = filter(lambda x: os.path.isdir, p.split(os.pathsep))
         for d in pl:
            for s in glob.glob(d+"/*.schema"):
               sn = os.path.splitext(os.path.basename(s))[0]
               if sn in Schemas:
                  print("[DaS] Skip schema in '%s'" % s)
                  continue
               try:
                  with open(s, "r") as f:
                     d = eval(f.read(), globals(), {"Boolean": Boolean,
                                                    "Integer": Integer,
                                                    "Real": Real,
                                                    "String": String,
                                                    "Sequence": Sequence,
                                                    "Class": Class,
                                                    "Or": Or})
                     Schemas[sn] = DaS(d)
                     if sn == schema:
                        found = Schemas[sn]
               except Exception, e:
                  print("[DaS] Failed to read schema '%s' (%s)" % (s, e))
      if found is None:
         raise UnknownSchemaError(schema)
   # Now validates!
   for k, v in d._iteritems():
      if not k in found:
         return False
