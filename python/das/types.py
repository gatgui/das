
class ReservedNameError(Exception):
   def __init__(self, name):
      super(ReservedNameError, self).__init__("'%s' is a reserved name" % name)


class Struct(object):
   def __init__(self, *args, **kwargs):
      super(Struct, self).__init__()
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
            raise AttributeError("'Struct' has not attribute '%s' (dict %s)" % (k, "has" if hasattr(self._dict, k) else "hasn't"))

   def __setattr__(self, k, v):
      self._check_reserved(k)
      # adapt value and validate it
      self._dict[k] = v

   def __delattr__(self, k):
      del(self._dict[k])

   def __getitem__(self, k):
      return self._dict.__getitem__(k)

   def __setitem__(self, k, v):
      self._check_reserved(k)
      # adapt value and validate it
      self._dict.__setitem__(k, v)

   def __delitem__(self, k):
      return self._dict.__delitem__(k)

   def __contains__(self, k):
      return self._dict.__contains__(k)

   def __cmp__(self, oth):
      return self._dict.__cmp__(oth._dict if isinstance(oth, Struct) else oth)

   def __eq__(self, oth):
      return self._dict.__eq__(oth._dict if isinstance(oth, Struct) else oth)

   def __ge__(self, oth):
      return self._dict.__ge__(oth._dict if isinstance(oth, Struct) else oth)

   def __le__(self, oth):
      return self._dict.__le__(oth._dict if isinstance(oth, Struct) else oth)

   def __gt__(self, oth):
      return self._dict.__gt__(oth._dict if isinstance(oth, Struct) else oth)

   def __lt__(self, oth):
      return self._dict.__lt__(oth._dict if isinstance(oth, Struct) else oth)

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
      st = self._get_schema_type()
      if isinstance(value, dict):
         if st is not None:
            # TODO
            return self.__class__(**value)
         else:
            return self.__class__(**value)
      elif isinstance(value, (tuple, list, set)):
         n = len(value)
         l = [None] * n
         i = 0
         for item in value:
            l[i] = self._adapt_value(item)
            i += 1
         if st is not None:
            # TODO
            return type(value)(l)
         else:
            return type(value)(l)
      else:
         return value

   def _validate(self, schema_type=None):
      if schema_type is None:
         schema_type = self._get_schema_type()
      if schema_type is not None:
         schema_type.validate(self)
      self._set_schema_type(schema_type)

   def _get_schema_type(self):
      return self.__dict__["_schema_type"]

   def _set_schema_type(self, schema_type):
      self.__dict__["_schema_type"] = schema_type


class Sequence(list):
   def __init__(self, *args):
      super(Sequence, self).__init__(*args)
      self._schema_type = None

   def __iadd__(self, y):
      return super(Sequence, self).__iadd__(y)

   def __add__(self, y):
      super(Sequence, self).__add__(y)

   def __setitem__(self, i, y):
      super(Sequence, self).__setitem__(i, y)

   def __setslice__(self, i, j, y):
      super(Sequence, self).__setslice__(i, j, y)

   def insert(self, i, y):
      super(Sequence, self).insert(i, y)

   def append(self, y):
      super(Sequence, self).append(y)

   def extend(self, y):
      super(Sequence, self).extend(y)

   def _validate(self, schema_type=None):
      if schema_type is None:
         schema_type = self._schema_type
      if schema_type is not None:
         schema_type.validate(self)
      self._set_schema_type(schema_type)

   def _get_schema_type(self, schema_type):
      return self._schema_type

   def _set_schema_type(self, schema_type):
      self._schema_type = schema_type


class Tuple(tuple):
   def __init__(self, *args):
      super(Tuple, self).__init__(*args)
      self._schema_type = None

   def __add__(self, y):
      return super(Tuple, self).__add__(y)

   def _validate(self, schema_type=None):
      if schema_type is None:
         schema_type = self._schema_type
      if schema_type is not None:
         schema_type.validate(self)
      self._set_schema_type(schema_type)

   def _get_schema_type(self, schema_type):
      return self._schema_type

   def _set_schema_type(self, schema_type):
      self._schema_type = schema_type


class Set(set):
   def __init__(self, *args):
      super(Set, self).__init__(*args)
      self._schema_type = None

   def __iand__(self, y):
      return super(Set, self).__iand__(y)

   def __isub__(self, y):
      return super(Set, self).__isub__(y)

   def __ior__(self, y):
      return super(Set, self).__ior__(y)

   def __ixor__(self, y):
      return super(Set, self).__ixor__(y)

   def add(self, e):
      super(Set, self).add(e)

   def update(self, *args):
      super(Set, self).update(args)

   def _validate(self, schema_type=None):
      if schema_type is None:
         schema_type = self._schema_type
      if schema_type is not None:
         schema_type.validate(self)
      self._set_schema_type(schema_type)

   def _get_schema_type(self, schema_type):
      return self._schema_type

   def _set_schema_type(self, schema_type):
      self._schema_type = schema_type


class Dict(dict):
   def __init__(self, *args, **kwargs):
      super(Dict, self).__init__(*args, **kwargs)
      self._schema_type = None

   def __setitem__(self, k, v):
      super(Dict, self).__setitem__(k, v)

   def setdefault(self, *args):
      super(Dict, self).setdefault(*args)

   def update(self, *args, **kwargs):
      super(Dict, self).update(*args, **kwargs)
      # if len(args) == 1:
      #    a0 = args[0]
      #    if hasattr(a0, "keys"):
      #       for k in a0.keys():
      #          # adapt values
      #          self[k] = a0[k]
      #    else:
      #       for k, v in a0:
      #          # adapt values
      #          self[k] = v
      # for k, v in kwargs.iteritems():
      #    # adapt values
      #    self[k] = v

   def _validate(self, schema_type=None):
      if schema_type is None:
         schema_type = self._schema_type
      if schema_type is not None:
         schema_type.validate(self)
      self._set_schema_type(schema_type)

   def _get_schema_type(self, schema_type):
      return self._schema_type

   def _set_schema_type(self, schema_type):
      self._schema_type = schema_type
