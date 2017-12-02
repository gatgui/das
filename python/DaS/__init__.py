import sys
from pprint import pprint

class ODict(object):
   Reserved = set(['_adapt_value',
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

   def __init__(self, *args, **kwargs):
      super(ODict, self).__init__()
      self.__dict__["_dict"] = {}
      self._update(*args, **kwargs)

   def __getattr__(self, k):
      return self._dict.get(k, None)

   def __setattr__(self, k, v):
      self._dict[k] = v

   def __delattr__(self, k):
      del(self._dict[k])

   def __contains__(self, k):
      return self._dict.__contains__(k)

   def __cmp__(self, oth):
      return self._dict.__cmp__(oth._dict if isinstance(oth, ODict) else oth)

   def __eq__(self, oth):
      return self._dict.__eq__(oth._dict if isinstance(oth, ODict) else oth)

   def __ge__(self, oth):
      return self._dict.__ge__(oth._dict if isinstance(oth, ODict) else oth)

   def __le__(self, oth):
      return self._dict.__le__(oth._dict if isinstance(oth, ODict) else oth)

   def __gt__(self, oth):
      return self._dict.__gt__(oth._dict if isinstance(oth, ODict) else oth)

   def __lt__(self, oth):
      return self._dict.__lt__(oth._dict if isinstance(oth, ODict) else oth)

   def __getitem__(self, k):
      return self._dict.__getitem__(k)

   def __setitem__(self, k, v):
      return self._dict.__setitem__(k, v)

   def __delitem__(self, k):
      return self._dict.__delitem__(k)

   def __iter__(self):
      return self._dict.__iter__()

   def __len__(self):
      return self._dict.__len__()

   def __str__(self):
      return self._dict.__str__()

   def __repr__(self):
      return self._dict.__repr__()

   def _has_key(self, name):
      return self._dict.has_key(name)

   def _get(self, name, default=None):
      return self._dict.get(name, default)

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
      return self._dict.pop(key, *args)

   def _popitem(self):
      return self._dict.popitem()

   def _clear(self):
      self._dict.clear()

   def _copy(self):
      # Shallow copy
      return ODict(self._dict.copy())

   def _setdefault(self, *args):
      if len(args) >= 2:
         args[1] = self._adapt_value(args[1])
      self._dict.setdefault(*args)

   def _update(self, *args, **kwargs):
      self._dict.update(*args, **kwargs)
      for k, v in self._dict.items():
         if k in self.Reserved:
            print("'%s' is a reserved attribute name. Value will be ignored." % k)
            continue
         self._dict[k] = self._adapt_value(v)

   def _adapt_value(self, value):
      t = type(value)
      if t == dict:
         return ODict(**value)
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


def Read(path, **funcs):
   rv = ODict()
   with open(path, "r") as f:
      rv._update(**eval(f.read(), globals(), funcs))
   return rv

def Write(d, path):
   with open(path, "w") as f:
      pass

def Copy(d, deep=True):
   if not deep:
      return d._copy()
   else:
      rv = ODict(d._dict)
      for k, v in rv._dict.items():
         if isinstance(v, ODict):
            rv._dict[k] = Copy(v, deep=True)
      return rv

def PrettyPrint(d, stream=None, indent=2, depth=0, inline=False):
   if stream is None:
      stream = sys.stdout
   sindents = " " * indent
   indents = sindents * depth
   if not inline:
      stream.write(indents)
   t = type(d)
   if t in (ODict, dict):
      stream.write("{\n%s%s" % (indents, sindents))
      n = len(v)
      i = 0
      for k in d:
         ks = "%s: " % k
         stream.write(ks)
         v = d[k]
         PrettyPrint(v, stream, indent=indent, depth=depth+1, inline=True)
         i += 1
         if i >= n:
            stream.write("\n%s" % indents)
         else:
            stream.write(",\n%s " % indents)
      stream.write("}")
   elif t == list:
      stream.write("[\n%s%s" % (indents, sindents))
      n = len(d)
      i = 0
      for v in d:
         PrettyPrint(v, stream, indent=indent, depth=depth+1, inline=True)
         i += 1
         if i >= n:
            stream.write("\n%s" % indents)
         else:
            stream.write(",\n%s " % indents)
      stream.write("]")
   elif t == set:
      stream.write("set([\n%s%s" % (indents, sindents))
      n = len(d)
      i = 0
      for v in d:
         PrettyPrint(v, stream, indent=indent, depth=depth+1, inline=True)
         i += 1
         if i >= n:
            stream.write("\n%s" % indents)
         else:
            stream.write(",\n%s " % indents)
      stream.write("])")
   else:
      stream.write(str(d))
   print("\n")
