import os
import sys
import das
import inspect
try:
   import importlib
except:
   # Python 2.6 doesn't come with import lib, use our own copy
   importlibdir = os.path.join(os.path.dirname(das.__file__), "importlib-1.0.4")
   sys.path.append(importlibdir)
   import importlib


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
_IgnoreMethods = set(["__init__", "__del__"])

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

def is_instance_method(klass, name):
   if not is_method(klass, name):
      return False
   else:
      return (getattr(klass, name).__self__ is not klass)

def is_class_method(klass, name):
   if not is_method(klass, name):
      return False
   else:
      return (getattr(klass, name).__self__ is klass)

def list_methods(klass):
   return filter(lambda x: is_instance_method(klass, x) and x not in _IgnoreMethods, dir(klass))


def get_bound_mixins(instance):
   iclass = instance.__class__
   iclassname = iclass.__name__
   rv = []

   cclassname = iclassname
   _, b, m = _DynamicClasses.get(cclassname, (None, None, None))
   while b is not None:
      rv.append(m)
      cclassname = b.__name__
      _, b, m = _DynamicClasses.get(cclassname, (None, None, None))

   rv.reverse()

   return rv


def has_bound_mixins(instance):
   return (instance.__class__.__name__ in _DynamicClasses)


def bind(mixins, instance, reset=False, verbose=False):
   if instance is None or not mixins:
      return instance

   if not isinstance(instance, das.types.TypeBase):
      raise BindError("Mixin can only be bound to das override types, got %s" % (type(instance).__name__))

   st = instance._get_schema_type()
   if st is None:
      raise BindError("Mixim can only be bound to objects with a schema type")
   else:
      st = das.get_schema_type_name(st)

   if isinstance(mixins, (tuple, list, set)):
      for mixin in mixins:
         if not issubclass(mixin, Mixin):
            raise BindError("'%s' must be a subclass of Mixin class" % mixin.__name__)
      mixins = list(mixins)
      mixins.sort(key=lambda x: x.__name__)
   else:
      if issubclass(mixins, Mixin):
         mixins = [mixins]
      else:
         raise BindError("'%s' must be a subclass of Mixin class" % mixins)

   for mixin in mixins:
      tst = mixin.get_schema_type()
      if not das.has_schema_type(tst):
         raise SchemaTypeError("Invalid schema type '%s' for mixin '%s'" % (st, mixin.__name__))
      elif tst != st:
         raise SchemaTypeError("Schema type mismatch for mixin '%s': Expected '%s', got '%s'" % (mixin.__name__, tst, st))

   # Get the original class in use before any mixin were bound
   iclass = instance.__class__
   iclassname = iclass.__name__
   _, baseclass, addclass = _DynamicClasses.get(iclassname, (None, iclass, None))
   if not reset and addclass in mixins:
      if verbose:
         print("[das] '%s' already bound" % addclass.__name__)
      return instance
   if baseclass != instance.__class__:
      cclass = baseclass
      while cclass is not None:
         baseclass = cclass
         _, cclass, addclass = _DynamicClasses.get(cclass.__name__, (None, None, None))
         if not reset and addclass in mixins:
            if verbose:
               print("[das] '%s' already bound" % addclass.__name__)
            return instance

   klassname = "_".join([baseclass.__name__] + [x.__name__ for x in mixins])
   klass = _DynamicClasses.get(klassname, (None, None, None))[0]

   if klass is None:
      cclass = baseclass
      bmeths = set(list_methods(cclass))

      for mixin in mixins:
         fmeths = set(list_methods(mixin))
         i = bmeths.intersection(fmeths)
         if i:
            for n in i:
               das.print_once("[das] Method '%s' from mixin '%s' is shadowed" % (n, mixin.__name__))
         bmeths = bmeths.union(fmeths)

         cclassname = cclass.__name__ + "_" + mixin.__name__
         klass = type(cclassname, (cclass, mixin), {})
         _DynamicClasses[cclassname] = (klass, cclass, mixin)

         # Also add class to the module the mixin is coming from
         mod = importlib.import_module(mixin.__module__)
         setattr(mod, klass.__name__, klass)
         setattr(klass, "__module__", mixin.__module__)

         cclass = klass

   instance.__class__ = klass
   return instance
