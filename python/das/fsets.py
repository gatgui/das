import das
import inspect


class BindError(Exception):
   def __init__(self, msg):
      super(BindError, self).__init__(msg)


class SchemaTypeError(Exception):
   def __init__(self, msg):
      super(SchemaTypeError, self).__init__(msg)


class Mixin(object):
   @classmethod
   def get_schema_type(klass):
      raise SchemaTypeError("No target schema type for mixin '%s'" % klass.__name__)

   def __init__(self, *args, **kwargs):
      super(Mixin, self).__init__()


_DynamicClasses = {}

def is_method(klass, name):
   return inspect.ismethod(getattr(klass, name, None))

def is_inherited_method(klass, name):
   if not is_method(klass, name):
      return False
   return any(getattr(klass, name) == getattr(c, name, None) for c in klass.mro()[1:])

def is_new_method(klass, name):
   if not is_method(klass, name):
      return False
   return (not any(hasattr(c, name) for c in klass.mro()[1:]))

def is_overridden_method(klass, name):
   if not is_method(klass, name):
      return False
   return (not is_inherited_method(klass, name) and not is_new_method(klass, name))

def is_class_method(klass, name):
   if not is_method(klass, name):
      return False
   else:
      return (getattr(klass, name).__self__ is klass)

def bind(fn, instance, reset=False, verbose=False):
   if not isinstance(instance, das.types.TypeBase):
      raise BindError("Mixin can only be bound to das override types")

   st = instance._get_schema_type()
   if st is None:
      raise BindError("Mixim can only be bound to objects with a schema type")
   else:
      st = das.get_schema_type_name(st)

   if isinstance(fn, (tuple, list, set)):
      for f in fn:
         if not issubclass(f, Mixin):
            raise Exception("'%s' must be a subclass of Mixin class" % f.__name__)
      fns = list(fn)
      fns.sort(key=lambda x: x.__name__)
   elif issubclass(fn, Mixin):
      fns = [fn]
   else:
      raise Exception("'%s' must be a subclass of Mixin class" % fn.__name__)

   for fn in fns:
      tst = fn.get_schema_type()
      if not das.has_schema_type(tst):
         raise SchemaTypeError("Invalid schema type '%s' for mixin '%s'" % (st, fn.__name__))
      elif tst != st:
         raise SchemaTypeError("Schema type mismatch for mixin '%s': Expected '%s', got '%s'" % (fn.__name__, tst, st))

   # Get the original class in use before any mixin were bound
   iclass = instance.__class__
   iclassname = iclass.__name__
   _, baseclass, addclass = _DynamicClasses.get(iclassname, (None, iclass, None))
   if not reset and addclass in fns:
      if verbose:
         print("[das] '%s' already bound" % addclass.__name__)
      return instance
   if baseclass != instance.__class__:
      cclass = baseclass
      while cclass is not None:
         baseclass = cclass
         _, cclass, addclass = _DynamicClasses.get(cclass.__name__, (None, None, None))
         if not reset and addclass in fns:
            if verbose:
               print("[das] '%s' already bound" % addclass.__name__)
            return instance

   klassname = "_".join([baseclass.__name__] + [x.__name__ for x in fns])
   klass = _DynamicClasses.get(klassname, (None, None, None))[0]

   if klass is None:
      cclass = baseclass

      for fn in fns:
         # # Give precedence to symbols in fn class,
         # # maybe check for possible conflicts
         # symbols = filter(lambda x: is_method(fn, x), dir(fn))
         # print("%s symbol(s): %s" % (fn.__name__, symbols))
         # tsymbols = filter(lambda x: not is_class_method(fn, x) and (is_overridden_method(fn, x) or is_new_method(fn, x)), symbols)
         # print("%s target symbol(s): %s" % (fn.__name__, tsymbols))
         cclassname = cclass.__name__ + "_" + fn.__name__
         klass = type(cclassname, (fn, cclass), {})
         _DynamicClasses[cclassname] = (klass, cclass, fn)
         cclass = klass

   instance.__class__ = klass
   return instance


class FunctionSet(object):
   def __init__(self, data=None, validate=True):
      super(FunctionSet, self).__init__()
      schema_type = self.get_schema_type()
      if schema_type is None:
         raise SchemaTypeError("Invalid schema type '%s'" % schema_type)
      if data is None:
         self.data = schema_type.make_default()
      elif validate:
         self.bind(data)
      else:
         self.data = data

   def get_schema_type(self):
      raise None

   def bind(self, data):
      rv = self.get_schema_type().validate(data)
      if isinstance(rv, FunctionSet):
         self.data = rv.data
      else:
         self.data = rv

   def read(self, path):
      self.bind(das.read(path, ignore_meta=True))

   def write(self, path):
      das.write(self.data, path)

   def pprint(self):
      das.pprint(self.data)

   def copy(self):
      rv = self.__class__()
      rv.bind(das.copy(self.data))
      return rv

   def __repr__(self):
      return self.data.__repr__()

   def __str__(self):
      return self.data.__str__()

   # The two following method are to impersonate TypeBase type

   def _validate(self, schema_type=None):
      if schema_type is not None and schema_type != self.get_schema_type():
         raise das.ValidationError("FunctionSet schema type mismatch")
      self.data._validate(schema_type=schema_type)

   def _get_schema_type(self):
      return self.get_schema_type()
