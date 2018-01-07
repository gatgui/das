import re
import das


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   def __init__(self, default=None):
      super(TypeValidator, self).__init__()
      if default is not None:
         # This is the only place where validate_default is call
         self.default = self.validate_default(default)
      else:
         self.default = None

   # Best effort type conversion method without validation
   # Once adapted, the value should pass the validate method without raising
   #   any exception
   def adapt(self, value, key=None, index=None):
      raise ValidationError("'adapt' method is not implemented")

   # This method must raise an exception if the default value set in the schema
   #   is not acceptable for the type being defined
   def validate_default(self, value):
      return value

   def validate(self, value):
      raise ValidationError("'validate' method is not implemented")

   def make_default(self):
      return self.adapt(self.default)

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   def __init__(self, default=None):
      super(Boolean, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      return (True if value else False)

   def validate_default(self, value):
      return bool(value)

   def validate(self, value):
      if not isinstance(value, bool):
         raise ValidationError("Expected a boolean value, got %s" % type(value).__name__)

   def __repr__(self):
      s = "Boolean(";
      if self.default is not None:
         s += "default=%s" % self.default
      return s + ")"


class Integer(TypeValidator):
   def __init__(self, default=None, min=None, max=None):
      self.min = min
      self.max = max
      super(Integer, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if isinstance(value, (bool, int, long)):
         return long(value)
      else:
         return 0

   def validate_default(self, value):
      return long(value)

   def validate(self, value):
      if not isinstance(value, (int, long)):
         raise ValidationError("Expected an integer value, got %s" % type(value).__name__)
      if self.min is not None and value < self.min:
         raise ValidationError("Integer value out of range, %d < %d" % (value, self.min))
      if self.max is not None and value > self.max:
         raise ValidationError("Integer value out of range, %d > %d" % (value, self.max))

   def __repr__(self):
      s = "Integer(";
      sep = ""
      if self.default is not None:
         s += "default=%s" % self.default
         sep = ", "
      if self.min is not None:
         s += "%smin=%d" % (sep, self.min)
         sep = ", "
      if self.max is not None:
         s += "%smax=%d" % (sep, self.max)
      return s + ")"


class Real(TypeValidator):
   def __init__(self, default=None, min=None, max=None):
      self.min = min
      self.max = max
      super(Real, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if isinstance(value, (bool, int, long, float)):
         return float(value)
      else:
         return 0.0

   def validate_default(self, value):
      return float(value)

   def validate(self, value):
      if not isinstance(value, (int, long, float)):
         raise ValidationError("Expected a real value, got %s" % type(value).__name__)
      if self.min is not None and value < self.min:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))
      if self.max is not None and value > self.max:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))

   def __repr__(self):
      s = "Real(";
      sep = ""
      if self.default is not None:
         s += "default=%s" % self.default
         sep = ", "
      if self.min is not None:
         s += "%smin=%d" % (sep, self.min)
         sep = ", "
      if self.max is not None:
         s += "%smax=%d" % (sep, self.max)
      return s + ")"


class String(TypeValidator):
   def __init__(self, default=None, choices=None, matches=None):
      self.choices = choices
      self.matches = None
      if choices is None and matches is not None:
         if type(matches) in (str, unicode):
            self.matches = re.compile(matches)
         else:
            self.matches = matches
      super(String, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if value is None:
         return ""
      else:
         return str(value)

   def validate_default(self, value):
      return str(value)

   def validate(self, value):
      if not isinstance(value, (str, unicode)):
         raise ValidationError("Expected a string value, got %s" % type(value).__name__)
      if self.choices is not None and not value in self.choices:
         raise ValidationError("String value must be on of %s, got '%s'" % (self.choices, value))
      if self.matches is not None and not self.matches.match(value):
         raise ValidationError("String value '%s' doesn't match pattern '%s'" % (value, self.matches.pattern))

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
         s += "]"
      return s + ")"


class Sequence(TypeValidator):
   def __init__(self, type, default=None, size=None, min_size=None, max_size=None):
      self.size = size
      self.min_size = min_size
      self.max_size = max_size
      self.type = type
      super(Sequence, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if index is not None:
         return self.type.adapt(value)
      else:
         if self.size is None:
            rv = das.types.Sequence()
         else:
            rv = das.types.Tuple()
         if isinstance(value, (tuple, list, set)):
            avalue = [self.type.adapt(x) for x in value]
            if self.size is None:
               if self.min_size is not None:
                  while len(avalue) < self.min_size:
                     avalue.append(self.type.make_default())
               if self.max_size is not None:
                  if len(avalue) > self.max_size:
                     avalue = avalue[:self.max_size]
               rv += avalue
            else:
               if len(avalue) > self.size:
                  avalue = avalue[:self.size]
               else:
                  while len(avalue) < self.size:
                     avalue.append(self.type.make_default())
               rv += tuple(avalue)
         else:
            if self.size is not None:
               avalue = [self.type.make_default()] * self.size
               rv += tuple(avalue)
         rv._set_schema_type(self)
         return rv

   def validate_default(self, value):
      lst = das.types.Sequence(value)
      for index, item in enumerate(lst):
         lst[index] = self.type.validate_default(item)
      lst._set_schema_type(self)
      return lst

   def validate(self, value):
      if not isinstance(value, (tuple, list, set)):
         raise ValidationError("Expected a sequence value, got %s" % type(value).__name__)
      n = len(value)
      if self.size is not None:
         if n != self.size:
            raise ValidationError("Expected a sequence of fixed size %d, got %d" % (self.size, n))
      else:
         if self.min_size is not None and n < self.min_size:
            raise ValidationError("Expected a sequence of minimum size %d, got %d" % (self.min_size, n))
         if self.max_size is not None and n > self.max_size:
            raise ValidationError("Expected a sequence of maximum size %d, got %d" % (self.max_size, n))
      for item in value:
         try:
            self.type.validate(item)
         except ValidationError, e:
            raise ValidationError("Invalid sequence element: %s" % e)

   def __repr__(self):
      s = "Sequence(type=%s" % self.type
      sep = ", "
      if self.default is not None:
         s += "%sdefault=%s" % (sep, self.default)
      if self.size is not None:
         s += "%ssize=%d" % (sep, self.size)
      else:
         if self.min_size is not None:
            s += "%smin_size=%d" % (sep, self.min_size)
         if self.max_size is not None:
            s += "%smax_size=%d" % (sep, self.max_size)
      return s + ")"


class Tuple(TypeValidator):
   def __init__(self, *args, **kwargs):
      self.types = args
      super(Tuple, self).__init__(default=kwargs.get("default", None))

   def adapt(self, value, key=None, index=None):
      if index is not None:
         return self.type.adapt(value)
      else:
         rv = das.types.Tuple()
         avalue = []
         n = 0
         if isinstance(value, (tuple, list, set)):
            n = len(value)
         for i in xrange(len(self.types)):
            if i < n:
               avalue.append(self.types[i].adapt(value[i]))
            else:
               avalue.append(self.types[i].make_default())
         rv += tuple(avalue)
         rv._set_schema_type(self)
         return rv

   def validate_default(self, value):
      tup = das.types.Tuple()
      n = len(value)
      for i, t in enumerate(self.types):
         v = (t.validate_default(value[i]) if i < n else t.make_default())
         tup += tuple([v])
      tup._set_schema_type(self)
      return tup

   def validate(self, value):
      if not isinstance(value, (list, tuple)):
         raise ValidationError("Expected a tuple value, got %s" % type(value).__name__)
      n = len(value)
      if n != len(self.types):
         raise ValidationError("Expected a tuple of size %d, got %d", (len(self.types), n))
      for i in xrange(n):
         try:
            self.types[i].validate(value[i])
         except ValidationError, e:
            raise ValidationError("Invalid tuple element: %s" % e)

   def __repr__(self):
      s = "Tuple("
      sep = ""
      for t in self.types:
         s += "%s%s" % (sep, t)
         sep = ", "
      if self.default is not None:
         s += "%sdefault=%s" % (sep, self.default)
      return s + ")"


class Struct(dict, TypeValidator):
   def __init__(self, **kwargs):
      hasdefault = ("default" in kwargs)
      default = None
      if hasdefault:
         default = kwargs["default"]
         print("[das] 'default' treated as a standard field for Struct type")
         del(kwargs["default"])
      TypeValidator.__init__(self)
      if hasdefault:
         kwargs["default"] = default
      dict.__init__(self, **kwargs)

   def adapt(self, value, key=None, index=None):
      if key is not None:
         vtype = self.get(key, None)
         if vtype is None:
            return das.types.adapt_value(value)
         else:
            return vtype.adapt(value)
      else:
         rv = das.types.Struct()
         dct = {}
         # populate all keys with defaults first
         for k, v in self.iteritems():
            dct[k] = v.make_default()
         try:
            for k in value:
               vtype = self.get(k, None)
               if vtype is None:
                  dct[k] = das.types.adapt_value(value[k])
               else:
                  dct[k] = vtype.adapt(value[k])
         except Exception, e:
            try:
               for k, v in value:
                  vtype = self.get(k, None)
                  if vtype is None:
                     dct[k] = das.types.adapt_value(v)
                  else:
                     dct[k] = vtype.adapt(v)
            except:
               dct = {}
         rv._update(**dct)
         rv._set_schema_type(self)
         return rv

   # no 'validate_default'

   def validate(self, value):
      if not isinstance(value, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
      for k, v in self.iteritems():
         if not k in value:
            if not isinstance(v, Optional):
               raise ValidationError("Missing key '%s'" % k)
         else:
            try:
               v.validate(value[k])
            except ValidationError, e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))

   def make_default(self):
      return self.adapt({})

   def __repr__(self):
      s = "Struct("
      sep = ""
      keys = [k for k in self]
      keys.sort()
      for k in keys:
         v = self[k]
         s += "%s%s=%s" % (sep, k, v)
         sep = ", "
      return s + ")"


class Dict(TypeValidator):
   def __init__(self, ktype, vtype, default=None, **kwargs):
      self.ktype = ktype
      self.vtype = vtype
      self.default = default
      self.vtypeOverrides = {}
      for k, v in kwargs.iteritems():
         self.vtypeOverrides[k] = v
      super(Dict, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if key is not None:
         ak = self.ktype.adapt(key)
         vtype = self.vtypeOverrides.get(ak, self.vtype)
         return vtype.adapt(value)
      else:
         rv = das.types.Dict()
         dct = {}
         try:
            for k in value:
               ak = self.ktype.adapt(k)
               vtype = self.vtypeOverrides.get(ak, self.vtype)
               if vtype is None:
                  dct[ak] = das.types.adapt_value(value[k])
               else:
                  dct[ak] = vtype.adapt(value[k])
         except:
            try:
               for k, v in value:
                  ak = self.ktype.adapt(k)
                  vtype = self.vtypeOverrides.get(ak, self.vtype)
                  if vtype is None:
                     dct[ak] = das.types.adapt_value(v)
                  else:
                     dct[ak] = vtype.adapt(v)
            except:
               dct = {}
         rv.update(**dct)
         rv._set_schema_type(self)
         return rv

   def validate_default(self, value):
      rv = das.types.Dict()
      for k, v in value.iteritems():
         ak = self.ktype.validate_default(k)
         av = self.vtypeOverrides.get(ak, self.vtype).validate_default(v)
         rv[ak] = av
      rv._set_schema_type(self)
      return rv

   def validate(self, value):
      if not isinstance(value, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
      for k in value:
         try:
            self.ktype.validate(k)
         except ValidationError, e:
            raise ValidationError("Invalid key value '%s': %s" % (k, e))
         try:
            ak = self.ktype.adapt(k)
            self.vtypeOverrides.get(ak, self.vtype).validate(value[k])
         except ValidationError, e:
            raise ValidationError("Invalid value for key '%s': %s" % (k, e))

   def __repr__(self):
      s = "Dict(ktype=%s, vtype=%s" % (self.ktype, self.vtype)
      if self.default is not None:
         s += ", default=%s" % self.default
      for k, v in self.vtypeOverrides.iteritems():
         s += ", %s=%s" % (k, v)
      return s + ")"


class Class(TypeValidator):
   def __init__(self, klass, default=None):
      if not hasattr(klass, "copy"):
         raise Exception("Schema class '%s' has no 'copy' method")
      try:
         klass()
      except:
         raise Exception("Schema class '%s' constructor cannot be used without arguments")
      self.klass = klass
      # Only call base class constructor once 'klass' member is set
      super(Class, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if value is None or not isinstance(value, self.klass):
         return self.klass()
      else:
         return value

   def validate_default(self, value):
      if not isinstance(value, self.klass):
         raise Exception("Class default value must be a %s, got %s" % (self.klass.__name__, type(value).__name__))

   def validate(self, value):
      if not isinstance(value, self.klass):
         raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(value).__name__))

   def make_default(self):
      return (self.klass() if self.default is None else self.default.copy())

   def __repr__(self):
      return "Class(%s)" % self.klass.__name__


class Or(TypeValidator):
   def __init__(self, type1, type2, default=None):
      self.type1 = type1
      self.type2 = type2
      super(Or, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      if value is not None:
         try:
            self.type1.validate(value)
            return self.type1.adapt(value)
         except:
            try:
               self.type2.validate(value)
               return self.type2.adapt(value)
            except:
               pass
      return self.type1.make_default()

   def validate_default(self, value):
      try:
         self.type1.validate_default(value)
      except:
         self.type2.validate_default(value)

   def validate(self, value):
      try:
         self.type1.validate(value)
      except ValidationError, e1:
         self.type2.validate(value)

   def make_default(self):
      return self.type1.make_default()

   def __repr__(self):
      s = "Or(%s, %s" % (self.type1, self.type2)
      if self.default is not None:
         s += ", default=%s" % self.default
      return s + ")"


class Optional(TypeValidator):
   def __init__(self, type):
      self.type = type
      super(Optional, self).__init__()

   def adapt(self, value, key=None, index=None):
      if value is not None:
         return self.type.adapt(value)

   def validate(self, value):
      self.type.validate(value)

   def make_default(self):
      return self.type.make_default()

   def __repr__(self):
      return "Optional(type=%s)" % self.type


class Empty(TypeValidator):
   def __init__(self):
      super(Empty, self).__init__()

   def adapt(self, value, key=None, index=None):
      return None

   def validate_default(self, value):
      if value is not None:
         raise Exception("Empty only accepts None as default value, got %s" % type(value).__name__)

   def validate(self, value):
      if value is not None:
         raise ValidationError("Expected None, got %s" % type(value).__name__)

   def make_default(self):
      return None

   def __repr__(self):
      return "Empty()"


class SchemaType(TypeValidator):
   CurrentSchema = ""

   def __init__(self, name, default=None):
      if not "." in name:
         self.name = self.CurrentSchema + "." + name
      else:
         self.name = name
      super(SchemaType, self).__init__(default=default)

   def adapt(self, value, key=None, index=None):
      st = das.get_schema_type(self.name)
      return st.adapt(value, key=key, index=index)

   def validate_default(self, value):
      # Can't really call in the referenced type to validate default can we?
      # get_schema_type may not return a valid value just yet
      return value

   def validate(self, value):
      st = das.get_schema_type(self.name)
      st.validate(value)

   def make_default(self):
      st = das.get_schema_type(self.name)
      if self.default is None:
         return st.make_default()
      else:
         if (hasattr(st, "default")):
            old_default = st.default
            st.default = self.default
            exc = None
            try:
               rv = st.make_default()
            except Exception, e:
               exc = e
            st.default = old_default
            if exc:
               raise exc
            return rv
         else:
            print("[das] Ignore default value for SchemaType '%s'" % self.name)
            return st.make_default()

   def __repr__(self):
      s = "SchemaType('%s'" % self.name
      if self.default is not None:
         s += ", default=%s" % str(self.default)
      return s + ")"
