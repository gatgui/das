import sys
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
            except:
               _, ei, tb = sys.exc_info()
               ei = das.ValidationError("Global Validation Failed (%s)" % str(ei))
               raise ei.__class__, ei, tb

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
      raise das.ValidationError("Expected a tuple of size %d, got %d" % (len(self), len(self) + len(y)))

   def __getitem__(self, i):
      return TypeBase.TransferGlobalValidator(self, super(Tuple, self).__getitem__(i))


class Sequence(TypeBase, list):
   def __init__(self, *args):
      TypeBase.__init__(self)
      list.__init__(self, *args)

   def _wrap_index(self, i, n=None, clamp=False):
      if i < 0:
         if n is None:
            n = len(self)
         ii = i + n
         if ii < 0:
            if clamp:
               return 0
            else:
               raise IndexError("list index out of range")
         else:
            return ii
      else:
         return i

   def __imul__(self, n):
      oldlen = len(self)
      super(Sequence, self).__imul__(n)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).__setslice__(oldlen, len(self), [])
         except Exception, e:
            print("das.types.Sequence.__imul__: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb
      return self

   def __mul__(self, n):
      rv = self[:]
      rv.__imul__(n)
      return rv

   def __rmul__(self, n):
      return self.__mul__(n)

   def __iadd__(self, y):
      n = len(self)
      super(Sequence, self).__iadd__([self._adapt_value(x, index=n+i) for i, x in enumerate(y)])
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).__setslice__(n, len(self), [])
         except Exception, e:
            print("das.types.Sequence.__iadd__: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb
      return self

   def __add__(self, y):
      rv = self[:]
      rv.__iadd__(y)
      return rv

   def __setitem__(self, i, y):
      super(Sequence, self).__setitem__(i, self._adapt_value(y, index=i))
      self._gvalidate()

   def __getitem__(self, i):
      return TypeBase.TransferGlobalValidator(self, super(Sequence, self).__getitem__(i))

   def __delitem__(self, i):
      # TODO: slice objects?
      ii = self._wrap_index(i, clamp=False)
      item = super(Sequence, self).__getitem__(ii)
      super(Sequence, self).__delitem__(i)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).insert(ii, item)
         except Exception, e:
            print("das.types.Sequence.__delitem__: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb

   def __iter__(self):
      for item in super(Sequence, self).__iter__():
         yield TypeBase.TransferGlobalValidator(self, item)

   def __setslice__(self, i, j, y):
      oldvals = super(Sequence, self).__getslice__(i, j)
      newvals = [self._adapt_value(x, index=i+k) for k, x in enumerate(y)]
      super(Sequence, self).__setslice__(i, j, newvals)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            ii = self._wrap_index(i, clamp=True)
            super(Sequence, self).__setslice__(ii, ii+len(newvals), oldvals)
         except Exception, e:
            print("das.types.Sequence.__setslice__: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb

   def __getslice__(self, i, j):
      return self._wrap(super(Sequence, self).__getslice__(i, j))

   def __delslice__(self, i, j):
      oldvals = super(Sequence, self).__getslice__(i, j)
      super(Sequence, self).__delslice__(i, j)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            ii = self._wrap_index(i, clamp=True)
            super(Sequence, self).__setslice__(ii, ii, oldvals)
         except Exception, e:
            print("das.types.Sequence.__setslice__: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb

   # def __contains__(self, y):
   #    try:
   #       _v = self._adapt_value(y, index=0)
   #       return super(Sequence, self).__contains__(_v)
   #    except:
   #       return False

   def index(self, y):
      return super(Sequence, self).index(self._adapt_value(y, index=0))

   def insert(self, i, y):
      super(Sequence, self).insert(i, self._adapt_value(y, index=i))
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).pop(self._wrap_index(i, n=len(self)-1, clamp=True))
         except Exception, e:
            print("das.types.Sequence.insert: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb

   def append(self, y):
      n = len(self)
      super(Sequence, self).append(self._adapt_value(y, index=n))
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).pop()
         except Exception, e:
            print("das.types.Sequence.append: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb

   def extend(self, y):
      newvals = [self._adapt_value(x, index=len(self)+i) for i, x in enumerate(y)]
      super(Sequence, self).extend(newvals)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).__setslice__(len(self) - len(newvals), len(self), [])
         except Exception, e:
            print("das.types.Sequence.extend: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb

   def pop(self, *args):
      rv = super(Sequence, self).pop(*args)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            if args:
               super(Sequence, self).insert(self._wrap_index(args[0], n=len(self)+1, clamp=False), rv)
            else:
               super(Sequence, self).append(rv)
         except Exception, e:
            print("das.types.Sequence.pop: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb
      return rv

   def remove(self, y):
      idx = self.index(y)
      item = self[idx]
      super(Sequence, self).remove(item)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Sequence, self).insert(idx, item)
         except Exception, e:
            print("das.types.Sequence.remove: Failed to recover sequence data (%s)" % e)
         raise ec, ei, tb


class Set(TypeBase, set):
   def __init__(self, args):
      TypeBase.__init__(self)
      set.__init__(self, args)

   def __iand__(self, y):
      oldvals = super(Set, self).copy()
      super(Set, self).__iand__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).clear()
            super(Set, self).__ior__(oldvals)
         except Exception, e:
            print("das.types.Set.__iand__: Failed to recover set data (%s)" % e)
         raise ec, ei, tb
      return self

   def __and__(self, y):
      rv = self.copy()
      rv &= y
      return rv

   def __rand__(self, y):
      return self.__and__(y)

   def __isub__(self, y):
      oldvals = super(Set, self).copy()
      super(Set, self).__isub__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).clear()
            super(Set, self).__ior__(oldvals)
         except Exception, e:
            print("das.types.Set.__isub__: Failed to recover set data (%s)" % e)
         raise ec, ei, tb
      return self

   def __sub__(self, y):
      rv = self.copy()
      rv -= y
      return rv

   def __rsub__(self, y):
      return self.__sub__(y)

   def __ior__(self, y):
      oldvals = super(Set, self).copy()
      super(Set, self).__ior__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).clear()
            super(Set, self).__ior__(oldvals)
         except Exception, e:
            print("das.types.Set.__ior__: Failed to recover set data (%s)" % e)
         raise ec, ei, tb
      return self

   def __or__(self, y):
      rv = self.copy()
      rv |= y
      return rv

   def __ror__(self, y):
      return self.__or__(y)

   def __ixor__(self, y):
      oldvals = super(Set, self).copy()
      super(Set, self).__ixor__(set([self._adapt_value(x, index=i) for i, x in enumerate(y)]))
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).clear()
            super(Set, self).__ior__(oldvals)
         except Exception, e:
            print("das.types.Set.__ixor__: Failed to recover set data (%s)" % e)
         raise ec, ei, tb
      return self

   def __xor__(self, y):
      rv = self.copy()
      rv ^= y
      return rv

   def __rxor__(self, y):
      rv = self.copy()
      rv ^= y
      return rv

   def __cmp__(self, oth):
      # base set class doesn't implement __cmp__
      #   but we need it for some other purpose
      if len(self.symmetric_difference(oth)) == 0:
         return 0
      elif len(self) <= len(oth):
         return -1
      else:
         return 1

   def __iter__(self):
      for item in super(Set, self).__iter__():
         yield TypeBase.TransferGlobalValidator(self, item)

   def clear(self):
      oldvals = super(Set, self).copy()
      super(Set, self).clear()
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).__ior__(oldvals)
         except Exception, e:
            print("das.types.Set.clear: Failed to recover set data (%s)" % e)
         raise ec, ei, tb

   def copy(self):
      return self._wrap(self)

   def add(self, e):
      ae = self._adapt_value(e, index=len(self))
      if ae in self:
         return
      super(Set, self).add(ae)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).remove(ae)
         except Exception, e:
            print("das.types.Set.add: Failed to recover set data (%s)" % e)
         raise ec, ei, tb

   def update(self, *args):
      added = set()
      for y in args:
         lst = [self._adapt_value(x, index=i) for i, x in enumerate(y)]
         for item in lst:
            if item in self:
               continue
            super(Set, self).add(item)
            added.add(item)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            for item in added:
               super(Set, self).remove(item)
         except Exception, e:
            print("das.types.Set.update: Failed to recover set data (%s)" % e)
         raise ec, ei, tb

   def pop(self):
      item = super(Set, self).pop()
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Set, self).add(item)
         except Exception, e:
            print("das.types.Set.pop: Failed to recover set data (%s)" % e)
         raise ec, ei, tb
      return item

   def difference(self, rhs):
      return self.__sub__(rhs)

   def union(self, rhs):
      return self.__or__(rhs)

   def intersection(self, rhs):
      return self.__and__(rhs)

   def symmetric_difference(self, rhs):
      return self.__xor__(rhs)


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
      except:
         ec, ei, tb = sys.exc_info()
         try:
            if wasset:
               super(Dict, self).__setitem__(k, oldval)
            else:
               del(self[k])
         except Exception, e:
            print("das.types.Dict.__setitem__: Failed to recover dict data (%s)" % e)
         raise ec, ei, tb

   def __getitem__(self, k):
      return TypeBase.TransferGlobalValidator(self, super(Dict, self).__getitem__(self._adapt_key(k)))

   def __delitem__(self, k):
      _k = self._adapt_key(k)
      _v = super(Dict, self).__getitem__(_k)
      super(Dict, self).__delitem__(_k)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Dict, self).__setitem__(_k, _v)
         except Exception, e:
            print("das.types.Dict.popitem: Failed to recover dict data (%s)" % e)
         raise ec, ei, tb

   # def __contains__(self, k):
   #    try:
   #       _k = self._adapt_key(k)
   #       return super(Dict, self).__contains__(_k)
   #    except:
   #       return False

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
      except:
         ec, ei, tb = sys.exc_info()
         try:
            for k in remvals:
               super(Dict, self).__delitem__(k)
            for k, v in oldvals.iteritems():
               super(Dict, self).__setitem__(k, v)
         except Exception, e:
            print("das.types.Dict.update: Failed to recover dict data (%s)" % e)
         raise ec, ei, tb

   def pop(self, k, *args):
      _k = self._adapt_key(k)
      _v = super(Dict, self).pop(_k, *args)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            # if _k i not defined but a default value is provided, we should not reach here
            #   as dict is actually unchanged
            # -> no need to check if _k was a valid key
            super(Dict, self).__setitem__(_k, _v)
         except Exception, e:
            print("das.types.Dict.popitem: Failed to recover dict data (%s)" % e)
         raise ec, ei, tb
      return _v

   def popitem(self):
      item = super(Dict, self).popitem()
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Dict, self).__setitem__(item[0], item[1])
         except Exception, e:
            print("das.types.Dict.popitem: Failed to recover dict data (%s)" % e)
         raise ec, ei, tb
      return item

   def clear(self):
      items = super(Dict, self).items()
      super(Dict, self).clear()
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            super(Dict, self).update(items)
         except Exception, e:
            print("das.types.Dict.clear: Failed to recover dict data (%s)" % e)
         raise ec, ei, tb

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

   # def __contains__(self, k):
   #    return self._dict.__contains__(self._get_alias(k))

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
      oldval = self._dict.get(k, None)
      retval = self._dict.pop(k, *args)
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            self._dict[k] = oldval
         except Exception, e:
            print("das.types.Struct.pop: Failed to recover struct data (%s)" % e)
         raise ec, ei, tb
      return retval

   # Override of dict.popitem
   def _popitem(self):
      k, v = self._dict.popitem()
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            self._dict[k] = v
         except Exception, e:
            print("das.types.Struct.popitem: Failed to recover struct data (%s)" % e)
         raise ec, ei, tb

   # Override of dict.clear
   def _clear(self):
      items = self._dict.items()
      self._dict.clear()
      try:
         self._gvalidate()
      except:
         ec, ei, tb = sys.exc_info()
         try:
            self._dict.update(items)
         except Exception, e:
            print("das.types.Struct.clear: Failed to recover struct data (%s)" % e)
         raise ec, ei, tb

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
      if len(args) > 1:
         raise Exception("update expected at most 1 arguments, got %d" % len(args))

      oldvals = self._dict.copy()

      try:
         if len(args) == 1:
            a0 = args[0]
            if hasattr(a0, "keys"):
               for k in a0.keys():
                  k = self._get_alias(k)
                  self._check_reserved(k)
                  self._dict[k] = self._adapt_value(a0[k], key=k)
            else:
               for k, v in a0:
                  k = self._get_alias(k)
                  self._check_reserved(k)
                  self._dict[k] = self._adapt_value(v, key=k)

         for k, v in kwargs.iteritems():
            k = self._get_alias(k)
            self._check_reserved(k)
            self._dict[k] = self._adapt_value(v, key=k)

         self._gvalidate()

      except:
         ec, ei, tb = sys.exc_info()
         try:
            self._dict.clear()
            self._dict.update(oldvals)
         except Exception, e:
            print("das.types.Struct.update: Failed to recover struct data (%s)" % e)
         raise ec, ei, tb

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

