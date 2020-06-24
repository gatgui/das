import das
import traceback


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
      st = self._get_schema_type()
      if st is not None:
         # run self validation first (container validation)
         st._validate_self(self)
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
               # fn = ""
               # cm = self._validate_globally.im_class.__module__
               # if cm != "__main__":
               #    fn = cm + "."
               # fn += self._validate_globally.im_class.__name__
               # fn += "._validate_globally"
               # raise das.ValidationError("'%s' failed (%s)" % (fn, e))
               emsg = "Global Validation Failed"
               for l in traceback.format_exc().split("\n"):
                  emsg += "\n  %s" % l.rstrip()
               raise das.ValidationError(emsg)

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
      tmp = super(Tuple, self).__add__(tuple([self._adapt_value(x, index=n+i) for i, x in enumerate(y)]))
      rv = self._wrap(tmp)
      rv._gvalidate()
      return rv

   def __getitem__(self, i):
      return TypeBase.TransferGlobalValidator(self, super(Tuple, self).__getitem__(i))


class Sequence(TypeBase, list):
   def __init__(self, *args):
      TypeBase.__init__(self)
      list.__init__(self, *args)

   def __iadd__(self, y):
      n = len(self)
      super(Sequence, self).__iadd__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      try:
         self._gvalidate()
      except Exception, e:
         super(Sequence, self).__setslice__(n, len(self), [])
         raise das.ValidationError(traceback.format_exc())
      return self

   def __add__(self, y):
      n = len(self)
      tmp = super(Sequence, self).__add__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      rv = self._wrap(rv)
      rv._gvalidate()
      return rv

   def __setitem__(self, i, y):
      super(Sequence, self).__setitem__(i, self._adapt_value(y, index=i))
      self._gvalidate()

   def __setslice__(self, i, j, y):
      oldvals = super(Sequence, self).__getslice__(i, j)
      newvals = [self._adapt_value(x, index=i+k) for k, x in enumerate(y)]
      super(Sequence, self).__setslice__(i, j, newvals)
      try:
         self._gvalidate()
      except Exception, e:
         n = len(newvals)
         ii = (n+i if i < 0 else i)
         super(Sequence, self).__setslice__(ii, ii+n, oldvals)
         raise das.ValidationError(traceback.format_exc())

   def insert(self, i, y):
      ii = (len(self)+i if i < 0 else i)
      super(Sequence, self).insert(i, self._adapt_value(y, index=i))
      try:
         self._gvalidate()
      except Exception, e:
         super(Sequence, self).__setslice__(ii, ii+1, [])
         raise das.ValidationError(traceback.format_exc())

   def append(self, y):
      n = len(self)
      super(Sequence, self).append(self._adapt_value(y, index=n))
      try:
         self._gvalidate()
      except Exception, e:
         super(Sequence, self).pop()
         raise das.ValidationError(traceback.format_exc())

   def extend(self, y):
      n = len(self)
      super(Sequence, self).extend([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      try:
         self._gvalidate()
      except Exception, e:
         super(Sequence, self).__setslice__(n, len(self), [])
         raise das.ValidationError(traceback.format_exc())

   def pop(self, *args):
      n = len(self)
      rv = super(Sequence, self).pop(*args)
      try:
         self._gvalidate()
      except Exception, e:
         if args:
            i = args[0]
            if i < 0:
               i += n
            super(Sequence, self).insert(i, rv)
         else:
            super(Sequence, self).append(rv)
         raise das.ValidationError(traceback.format_exc())
      return rv

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
      ae = self._adapt_value(e, index=len(self))
      if ae in self:
         return
      super(Set, self).add(ae)
      try:
         self._gvalidate()
      except Exception, e:
         self.remove(ae)
         raise das.ValidationError(traceback.format_exc())

   def update(self, *args):
      added = set()
      for y in args:
         #super(Set, self).update([self._adapt_value(x, index=i) for i, x in enumerate(y)])
         lst = [self._adapt_value(x, index=i) for i, x in enumerate(y)]
         for item in lst:
            if item in self:
               continue
            super(Set, self).add(item)
            added.add(item)
      try:
         self._gvalidate()
      except Exception, e:
         for item in added:
            self.remove(item)
         raise das.ValidationError(traceback.format_exc())

   def __iter__(self):
      for item in super(Set, self).__iter__():
         yield TypeBase.TransferGlobalValidator(self, item)


class Dict(TypeBase, dict):
   def __init__(self, *args, **kwargs):
      TypeBase.__init__(self)
      dict.__init__(self, *args, **kwargs)

   def _adapt_key(self, key):
      st = self._get_schema_type()
      return (key if st is None else das.adapt_value(key, schema_type=st.ktype))

   def __setitem__(self, k, v):
      k = self._adapt_key(k)
      wasset = (k in self)
      oldval = (self[k] if wasset else None)
      super(Dict, self).__setitem__(k, self._adapt_value(v, key=k))
      try:
         self._gvalidate()
      except Exception, e:
         if wasset:
            super(Dict, self).__setitem__(k, oldval)
         else:
            del(self[k])
         raise das.ValidationError(traceback.format_exc())

   def setdefault(self, *args):
      if len(args) >= 2:
         args[1] = self._adapt_value(args[1], key=args[0])
      super(Dict, self).setdefault(*args)

   def copy(self):
      return self._wrap(self)

   def update(self, *args, **kwargs):
      oldvals = {}
      remvals = set()
      if len(args) == 1:
         a0 = args[0]
         if hasattr(a0, "keys"):
            for k in a0.keys():
               k = self._adapt_key(k)
               if k in self:
                  oldvals[k] = self[k]
               else:
                  remvals.add(k)
               self[k] = self._adapt_value(a0[k], key=k)
         else:
            for k, v in a0:
               k = self._adapt_key(k)
               if k in self:
                  oldvals[k] = self[k]
               else:
                  remvals.add(k)
               self[k] = self._adapt_value(v, key=k)
      elif len(args) > 1:
         raise Exception("update expected at most 1 arguments, got %d" % len(args))
      for k, v in kwargs.iteritems():
         k = self._adapt_key(k)
         if k in self:
            if not k in oldvals:
               oldvals[k] = self[k]
         else:
            remvals.add(k)
         self[k] = self._adapt_value(v, key=k)
      try:
         self._gvalidate()
      except Exception, e:
         for k in remvals:
            del(self[k])
         for k, v in oldvals.iteritems():
            self[k] = v
         raise das.ValidationError(traceback.format_exc())

   def __getitem__(self, k):
      return TypeBase.TransferGlobalValidator(self, super(Dict, self).__getitem__(self._adapt_key(k)))

   # __delitem__?
   # pop?

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
            #raise AttributeError("'Struct' has no attribute '%s' (dict %s)" % (k, "has" if hasattr(self._dict, k) else "hasn't"))
            return self.__getattribute__(k)

   def __setattr__(self, k, v):
      # Special case for __class__ member that we may want to modify for 
      #   to enable dynamic function set binding
      if k == "__class__":
         super(Struct, self).__setattr__(k, v)
      else:
         k = self._get_alias(k)
         self._check_reserved(k)
         wasset = (k in self._dict)
         oldval = (self._dict[k] if wasset else None)
         self._dict[k] = self._adapt_value(v, key=k)
         try:
            self._gvalidate()
         except Exception, e:
            if wasset:
               self._dict[k] = oldval
            else:
               del(self._dict[k])
            raise das.ValidationError(traceback.format_exc())

   def __delattr__(self, k):
      _k = k
      k = self._get_alias(k)
      oldval = self._dict.get(k, None)
      # this will fail if key doesn't exists, as expected
      self._dict.__delitem__(k)
      try:
         self._gvalidate()
      except Exception, e:
         # Note: del(self._dict[k]) will have raised an exception if k is not set
         #       if we reach here, k was set
         self._dict[k] = oldval
         emsg = "Cannot delete key %s as it would lead to the following validation error" % repr(_k)
         emsg += "".join(map(lambda x: "\n  %s" % x, traceback.format_exc().split("\n")))
         raise das.ValidationError(emsg)

   def __getitem__(self, k):
      k = self._get_alias(k)
      return TypeBase.TransferGlobalValidator(self, self._dict.__getitem__(k))

   def __setitem__(self, k, v):
      k = self._get_alias(k)
      self._check_reserved(k)
      wasset = (k in self._dict)
      oldval = (self._dict[k] if wasset else None)
      self._dict.__setitem__(k, self._adapt_value(v, key=k))
      try:
         self._gvalidate()
      except Exception, e:
         if wasset:
            self._dict[k] = oldval
         else:
            del(self._dict[k])
         raise e

   def __delitem__(self, k):
      _k = k
      k = self._get_alias(k)
      oldval = self._dict.get(k, None)
      # this will fail if key doesn't exists, as expected
      self._dict.__delitem__(k)
      try:
         self._gvalidate()
      except Exception, e:
         # Note: same remark as in __delattr__
         self._dict[k] = oldval
         emsg = "Cannot delete item %s as it would lead to the following validation error" % repr(_k)
         emsg += "".join(map(lambda x: "\n  %s" % x, traceback.format_exc().split("\n")))
         raise das.ValidationError(emsg)

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

   # Override of dict.pop
   def _pop(self, k, *args):
      _k = k
      k = self._get_alias(k)
      wasset = (k in self._dict)
      oldval = self._dict.get(k, None)
      retval = self._dict.pop(k, *args)
      try:
         self._gvalidate()
      except Exception, e:
         if wasset:
            self._dict[k] = oldval
         emsg = "Cannot pop key %s as it would lead to the following validation error" % repr(_k)
         emsg += "".join(map(lambda x: "\n  %s" % x, traceback.format_exc().split("\n")))
         raise das.ValidationError(emsg)
      return retval

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
      oldvals = {}
      remvals = set()
      if len(args) == 1:
         a0 = args[0]
         if hasattr(a0, "keys"):
            for k in a0.keys():
               k = self._get_alias(k)
               self._check_reserved(k)
               if k in self._dict:
                  oldvals[k] = self._dict[k]
               else:
                  remvals.add(k)
               self._dict[k] = self._adapt_value(a0[k], key=k)
         else:
            for k, v in a0:
               k = self._get_alias(k)
               self._check_reserved(k)
               if k in self._dict:
                  oldvals[k] = self._dict[k]
               else:
                  remvals.add(k)
               self._dict[k] = self._adapt_value(v, key=k)
      elif len(args) > 1:
         raise Exception("update expected at most 1 arguments, got %d" % len(args))
      for k, v in kwargs.iteritems():
         k = self._get_alias(k)
         self._check_reserved(k)
         if k in self._dict:
            if not k in oldvals:
               oldvals[k] = self._dict[k]
         else:
            remvals.add(k)
         self._dict[k] = self._adapt_value(v, key=k)
      try:
         self._gvalidate()
      except Exception, e:
         for k in remvals:
            del(self._dict[k])
         for k, v in oldvals.iteritems():
            self._dict[k] = v
         emsg = "'update' failed as it would lead to the following validation error"
         emsg += "".join(map(lambda x: "\n  %s" % x, traceback.format_exc().split("\n")))
         raise das.ValidationError(emsg)

   def _get_alias(self, k):
      st = self._get_schema_type()
      if st is not None and st.has_key(k):
         aliasname = das.schematypes.Alias.Name(st[k])
         if aliasname is not None:
            if isinstance(st[k], das.schematypes.Deprecated):
               message = ("[das] Field %s is deprecated, use %s instead" % (repr(k), repr(aliasname)))
               das.print_once(message)
            return aliasname
      return k

   def _check_reserved(self, k):
      if hasattr(self.__class__, k):
         raise ReservedNameError(k)
      elif hasattr(self._dict, k):
         k2 = "_" + k
         if hasattr(self, k2):
            # don't need to create forwarding attribute (set __getattr__)
            return
         if k2 in self.__dict__:
            if self.__dict__[k2] != getattr(self._dict, k):
               raise ReservedNameError(k)
         else:
            msg = "[das] %s's '%s(...)' method conflicts with data field '%s', use '_%s(...)' to call it instead" % (type(self).__name__, k, k, k)
            st = self._get_schema_type()
            if st is not None:
               n = das.get_schema_type_name(st)
               if n:
                  msg = "[%s] %s" % (n, msg)
            das.print_once(msg)
            self.__dict__[k2] = getattr(self._dict, k)

   def ordered_keys(self):
      return filter(lambda x: x in self, self._get_schema_type().ordered_keys())

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

