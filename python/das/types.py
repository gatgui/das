import das


class ReservedNameError(Exception):
   def __init__(self, name):
      super(ReservedNameError, self).__init__("'%s' is a reserved name" % name)


class TypeBase(object):
   def __init__(self):
      super(TypeBase, self).__init__()
      self.__dict__["_schema_type"] = None

   def _wrap(self, rhs):
      rv = self.__class__(rhs)
      rv._set_schema_type(self._get_schema_type())
      return rv

   def _adapt_value(self, value, key=None, index=None):
      return das.adapt_value(value, schema_type=self._get_schema_type(), key=key, index=index)

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


class Tuple(TypeBase, tuple):
   def __init__(self, *args):
      TypeBase.__init__(self)
      tuple.__init__(self, *args)

   def __add__(self, y):
      n = len(self)
      rv = super(Tuple, self).__add__(tuple([self._adapt_value(x, index=n+i) for i, x in enumerate(y)]))
      return self._wrap(rv)


class Sequence(TypeBase, list):
   def __init__(self, *args):
      TypeBase.__init__(self)
      list.__init__(self, *args)

   def __iadd__(self, y):
      n = len(self)
      rv = super(Sequence, self).__iadd__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      return self._wrap(rv)

   def __add__(self, y):
      n = len(self)
      rv = super(Sequence, self).__add__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      return self._wrap(rv)

   def __setitem__(self, i, y):
      super(Sequence, self).__setitem__(i, self._adapt_value(y, index=i))

   def __setslice__(self, i, j, y):
      super(Sequence, self).__setslice__(i, j, [self._adapt_value(x, index=i+k) for k, x in enumerate(y)])

   def insert(self, i, y):
      super(Sequence, self).insert(i, self._adapt_value(y, index=i))

   def append(self, y):
      n = len(self)
      super(Sequence, self).append(self._adapt_value(y, index=n))

   def extend(self, y):
      n = len(self)
      super(Sequence, self).extend([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])


class Set(TypeBase, set):
   def __init__(self, *args):
      TypeBase.__init__(self)
      set.__init__(self, *args)

   def __iand__(self, y):
      rv = super(Set, self).__iand__(map(lambda x: self._adapt_value(x), y))
      return self._wrap(rv)

   def __isub__(self, y):
      rv = super(Set, self).__isub__(map(lambda x: self._adapt_value(x), y))
      return self._wrap(rv)

   def __ior__(self, y):
      rv = super(Set, self).__ior__(map(lambda x: self._adapt_value(x), y))
      return self._wrap(rv)

   def __ixor__(self, y):
      rv = super(Set, self).__ixor__(map(lambda x: self._adapt_value(x), y))
      return self._wrap(rv)

   def add(self, e):
      super(Set, self).add(self._adapt_value(e))

   def update(self, *args):
      for y in args:
         super(Set, self).update(map(lambda x: self._adapt_value(x), y))


class Dict(TypeBase, dict):
   def __init__(self, *args, **kwargs):
      TypeBase.__init__(self)
      dict.__init__(self, *args, **kwargs)

   def __setitem__(self, k, v):
      super(Dict, self).__setitem__(k, self._adapt_value(v, key=k))

   def setdefault(self, *args):
      if len(args) >= 2:
         args[1] = self._adapt_value(args[1], key=args[0])
      super(Dict, self).setdefault(*args)

   def update(self, *args, **kwargs):
      if len(args) == 1:
         a0 = args[0]
         if hasattr(a0, "keys"):
            for k in a0.keys():
               self[k] = self._adapt_value(a0[k], key=k)
         else:
            for k, v in a0:
               self[k] = self._adapt_value(v, key=k)
      for k, v in kwargs.iteritems():
         self[k] = self._adapt_value(v, key=k)


class Struct(TypeBase):
   def __init__(self, *args, **kwargs):
      TypeBase.__init__(self)
      self.__dict__["_dict"] = {}
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
      self._dict[k] = self._adapt_value(v, key=k)

   def __delattr__(self, k):
      del(self._dict[k])

   def __getitem__(self, k):
      return self._dict.__getitem__(k)

   def __setitem__(self, k, v):
      self._check_reserved(k)
      self._dict.__setitem__(k, self._adapt_value(v, key=k))

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
         args[1] = self._adapt_value(args[1], key=args[0])
      self._dict.setdefault(*args)

   # Override of dict.update
   def _update(self, *args, **kwargs):
      self._dict.update(*args, **kwargs)
      for k, v in self._dict.items():
         self._check_reserved(k)
         self._dict[k] = self._adapt_value(v, key=k)

   def _check_reserved(self, k):
      if hasattr(self.__class__, k):
         raise ReservedNameError(k)
      elif hasattr(self._dict, k):
         if "_" + k in self.__dict__:
            raise ReservedNameError(k)
         msg = "'%s' key conflicts with existing method of dict class, use '_%s()' to call it instead" % (k, k)
         st = self._get_schema_type()
         if st is not None:
            n = das.get_schema_type_name(st)
            if n:
               msg = "[%s] %s" % (n, msg)
         das.print_once(msg)
         self.__dict__["_" + k] = getattr(self._dict, k)

