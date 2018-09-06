import das


class ReservedNameError(Exception):
   def __init__(self, name):
      super(ReservedNameError, self).__init__("'%s' is a reserved name" % name)


class VersionError(Exception):
   def __init__(self, msg=None, current_version=None, required_version=None):
      fullmsg = "ersion error"
      if required_version:
         fullmsg += ": %s required" % required_version
      else:
         fullmsg += ": no requirements"
      if current_version:
         fullmsg += ", %s in use" % current_version
      else:
         fullmsg += ", no version info"
      if msg:
         fullmsg = msg + " v" + fullmsg
      else:
         fullmsg = "V" + fullmsg
      super(VersionError, self).__init__(fullmsg)


class GlobalValidationDisabled(object):
   def __init__(self, data):
      super(GlobalValidationDisabled, self).__init__()
      self.data = data
      self.oldstate = None

   def __enter__(self):
      try:
         self.oldstate = self.data._is_global_validation_enabled()
         self.data._enable_global_validation(False)
      except:
         pass
      return self.data

   def __exit__(self, type, value, traceback):
      if self.oldstate is not None:
         self.data._enable_global_validation(self.oldstate)
         self.oldstate = None
      # Always re-raise exception
      return False


class TypeBase(object):
   @classmethod
   def TransferGlobalValidator(klass, src, dst):
      if isinstance(src, klass) and isinstance(dst, klass):
         dst._set_validate_globally_cb(src._gvalidate)
      return dst

   @classmethod
   def ValidateGlobally(klass, inst):
      if isinstance(inst, klass):
         inst._gvalidate()
      return inst

   def __init__(self):
      super(TypeBase, self).__init__()
      self.__dict__["_schema_type"] = None
      self.__dict__["_validate_globally_cb"] = None
      self.__dict__["_global_validation_enabled"] = True

   def _wrap(self, rhs):
      st = self._get_schema_type()
      rv = self.__class__(rhs if st is None else st._validate_self(rhs))
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

   def _gvalidate(self):
      if self._get_schema_type() is not None:
         if hasattr(self, "_is_global_validation_enabled"):
            if not self._is_global_validation_enabled():
               # Skip global validaton
               return
         gvcb = self._get_validate_globally_cb()
         if gvcb is not None:
            gvcb()
         if hasattr(self, "_validate_globally"):
            try:
               self._validate_globally()
            except Exception, e:
               fn = ""
               cm = self._validate_globally.im_class.__module__
               if cm != "__main__":
                  fn = cm + "."
               fn += self._validate_globally.im_class.__name__
               fn += "._validate_globally"
               raise das.ValidationError("'%s' failed (%s)" % (fn, e))

   def _get_schema_type(self):
      return self.__dict__["_schema_type"]

   def _set_schema_type(self, schema_type):
      self.__dict__["_schema_type"] = schema_type

   def _get_validate_globally_cb(self):
      return self.__dict__["_validate_globally_cb"]

   def _set_validate_globally_cb(self, cb):
      self.__dict__["_validate_globally_cb"] = cb

   def _is_global_validation_enabled(self):
      return self.__dict__["_global_validation_enabled"]

   def _enable_global_validation(self, on):
      self.__dict__["_global_validation_enabled"] = on


class Tuple(TypeBase, tuple):
   def __init__(self, *args):
      # Funny, we need to declare *args here, but at the time we reach
      # the core of the method, tuple is already created
      # Maybe because tuple is immutable?
      super(Tuple, self).__init__()

   def __add__(self, y):
      n = len(self)
      rv = super(Tuple, self).__add__(tuple([self._adapt_value(x, index=n+i) for i, x in enumerate(y)]))
      self._gvalidate()
      return self._wrap(rv)

   def __getitem__(self, i):
      return TypeBase.TransferGlobalValidator(self, super(Tuple, self).__getitem__(i))


class Sequence(TypeBase, list):
   def __init__(self, *args):
      TypeBase.__init__(self)
      list.__init__(self, *args)

   def __iadd__(self, y):
      n = len(self)
      rv = super(Sequence, self).__iadd__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      self._gvalidate()
      return self._wrap(rv)

   def __add__(self, y):
      n = len(self)
      rv = super(Sequence, self).__add__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      self._gvalidate()
      return self._wrap(rv)

   def __setitem__(self, i, y):
      super(Sequence, self).__setitem__(i, self._adapt_value(y, index=i))
      self._gvalidate()

   def __setslice__(self, i, j, y):
      super(Sequence, self).__setslice__(i, j, [self._adapt_value(x, index=i+k) for k, x in enumerate(y)])
      self._gvalidate()

   def insert(self, i, y):
      super(Sequence, self).insert(i, self._adapt_value(y, index=i))
      self._gvalidate()

   def append(self, y):
      n = len(self)
      super(Sequence, self).append(self._adapt_value(y, index=n))
      self._gvalidate()

   def extend(self, y):
      n = len(self)
      super(Sequence, self).extend([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      self._gvalidate()

   def __getitem__(self, i):
      return TypeBase.TransferGlobalValidator(self, super(Sequence, self).__getitem__(i))

   def __getslice__(self, i, j):
      return self._wrap(super(Sequence, self).__getslice__(i, j))


class Set(TypeBase, set):
   def __init__(self, args):
      TypeBase.__init__(self)
      set.__init__(self, args)

   def __iand__(self, y):
      rv = super(Set, self).__iand__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      self._gvalidate()
      return self._wrap(rv)

   def __isub__(self, y):
      rv = super(Set, self).__isub__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      self._gvalidate()
      return self._wrap(rv)

   def __ior__(self, y):
      rv = super(Set, self).__ior__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      self._gvalidate()
      return self._wrap(rv)

   def __ixor__(self, y):
      rv = super(Set, self).__ixor__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      self._gvalidate()
      return self._wrap(rv)

   def __cmp__(self, oth):
      if len(self.symmetric_difference(oth)) == 0:
         return 0
      elif len(self) <= len(oth):
         return -1
      else:
         return 1

   def add(self, e):
      super(Set, self).add(self._adapt_value(e, index=len(self)))
      self._gvalidate()

   def update(self, *args):
      for y in args:
         super(Set, self).update([self._adapt_value(x, index=i) for i, x in enumerate(y)])
      self._gvalidate()

   def __iter__(self):
      for item in super(Set, self).__iter__():
         yield TypeBase.TransferGlobalValidator(self, item)


class Dict(TypeBase, dict):
   def __init__(self, *args, **kwargs):
      TypeBase.__init__(self)
      dict.__init__(self, *args, **kwargs)

   def __setitem__(self, k, v):
      super(Dict, self).__setitem__(k, self._adapt_value(v, key=k))
      self._gvalidate()

   def setdefault(self, *args):
      if len(args) >= 2:
         args[1] = self._adapt_value(args[1], key=args[0])
      super(Dict, self).setdefault(*args)

   def copy(self):
      return self._wrap(self)

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
      self._gvalidate()

   def __getitem__(self, k):
      return TypeBase.TransferGlobalValidator(self, super(Dict, self).__getitem__(k))

   def itervalues(self):
      for v in super(Dict, self).itervalues():
         yield TypeBase.TransferGlobalValidator(self, v)

   def values(self):
      return [x for x in self.itervalues()]

   def iteritems(self):
      for k, v in super(Dict, self).iteritems():
         yield k, TypeBase.TransferGlobalValidator(self, v)

   def items(self):
      return [x for x in self.iteritems()]


class Struct(TypeBase):
   def __init__(self, *args, **kwargs):
      TypeBase.__init__(self)
      self.__dict__["_dict"] = {}
      self._update(*args, **kwargs)

   def __getattr__(self, k):
      try:
         k = self._get_alias(k)
         return TypeBase.TransferGlobalValidator(self, self._dict[k])
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
            raise AttributeError("'Struct' has no attribute '%s' (dict %s)" % (k, "has" if hasattr(self._dict, k) else "hasn't"))

   def __setattr__(self, k, v):
      # Special case for __class__ member that we may want to modify for 
      #   to enable dynamic function set binding
      if k == "__class__":
         super(Struct, self).__setattr__(k, v)
      else:
         k = self._get_alias(k)
         self._check_reserved(k)
         self._dict[k] = self._adapt_value(v, key=k)
         self._gvalidate()

   def __delattr__(self, k):
      del(self._dict[self._get_alias(k)])
      self._gvalidate()

   def __getitem__(self, k):
      k = self._get_alias(k)
      return TypeBase.TransferGlobalValidator(self, self._dict.__getitem__(k))

   def __setitem__(self, k, v):
      k = self._get_alias(k)
      self._check_reserved(k)
      self._dict.__setitem__(k, self._adapt_value(v, key=k))
      self._gvalidate()

   def __delitem__(self, k):
      self._dict.__delitem__(self._get_alias(k))
      self._gvalidate()

   def __contains__(self, k):
      return self._dict.__contains__(self._get_alias(k))

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
      return self._wrap(self)

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
         k = self._get_alias(k)
         self._check_reserved(k)
         self._dict[k] = self._adapt_value(v, key=k)
      self._gvalidate()

   def _get_alias(self, k):
      st = self._get_schema_type()
      if st is not None:
         if isinstance(st[k], das.schematypes.Alias):
            return st[k].name
      return k

   def _check_reserved(self, k):
      if hasattr(self.__class__, k):
         raise ReservedNameError(k)
      elif hasattr(self._dict, k):
         if "_" + k in self.__dict__:
            raise ReservedNameError(k)
         msg = "[das] %s's '%s(...)' method conflicts with data field '%s', use '_%s(...)' to call it instead" % (type(self).__name__, k, k, k)
         st = self._get_schema_type()
         if st is not None:
            n = das.get_schema_type_name(st)
            if n:
               msg = "[%s] %s" % (n, msg)
         das.print_once(msg)
         self.__dict__["_" + k] = getattr(self._dict, k)

   def _itervalues(self):
      for v in self._dict.itervalues():
         yield TypeBase.TransferGlobalValidator(self, v)

   def _values(self):
      return [x for x in self.itervalues()]

   def _iteritems(self):
      for k, v in self._dict.iteritems():
         yield k, TypeBase.TransferGlobalValidator(self, v)

   def _items(self):
      return [x for x in self.iteritems()]

