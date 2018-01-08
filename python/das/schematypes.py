import re
import das


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   def __init__(self, default=None):
      super(TypeValidator, self).__init__()
      self.default_validated = False
      self.default = default

   def validate(self, value, key=None, index=None):
      raise ValidationError("'validate' method is not implemented")

   def make_default(self):
      if not self.default_validated:
         self.default = self.validate(self.default)
         self.default_validated = True
      return self.default

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   def __init__(self, default=None):
      super(Boolean, self).__init__(default=(False if default is None else default))

   def validate(self, value, key=None, index=None):
      if not isinstance(value, bool):
         raise ValidationError("Expected a boolean value, got %s" % type(value).__name__)
      return value

   def __repr__(self):
      s = "Boolean(";
      if self.default is not None:
         s += "default=%s" % self.default
      return s + ")"


class Integer(TypeValidator):
   def __init__(self, default=None, min=None, max=None):
      super(Integer, self).__init__(default=(0 if default is None default))
      self.min = min
      self.max = max

   def validate(self, value, key=None, index=None):
      if not isinstance(value, (int, long)):
         raise ValidationError("Expected an integer value, got %s" % type(value).__name__)
      if self.min is not None and value < self.min:
         raise ValidationError("Integer value out of range, %d < %d" % (value, self.min))
      if self.max is not None and value > self.max:
         raise ValidationError("Integer value out of range, %d > %d" % (value, self.max))
      return long(value)

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
      super(Real, self).__init__(default=(0.0 if default is None else default))
      self.min = min
      self.max = max

   def validate(self, value, key=None, index=None):
      if not isinstance(value, (int, long, float)):
         raise ValidationError("Expected a real value, got %s" % type(value).__name__)
      if self.min is not None and value < self.min:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))
      if self.max is not None and value > self.max:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))
      return float(value)

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
      super(String, self).__init__(default=("" if default is None else default))
      self.choices = choices
      self.matches = None
      if choices is None and matches is not None:
         if type(matches) in (str, unicode):
            self.matches = re.compile(matches)
         else:
            self.matches = matches

   def validate(self, value, key=None, index=None):
      if not isinstance(value, (str, unicode)):
         raise ValidationError("Expected a string value, got %s" % type(value).__name__)
      if self.choices is not None and not value in self.choices:
         raise ValidationError("String value must be on of %s, got '%s'" % (self.choices, value))
      if self.matches is not None and not self.matches.match(value):
         raise ValidationError("String value '%s' doesn't match pattern '%s'" % (value, self.matches.pattern))
      return str(value)

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
      super(Sequence, self).__init__(default=([] if default is None else default))
      self.size = size
      self.min_size = min_size
      self.max_size = max_size
      self.type = type

   def validate(self, value, key=None, index=None):
      if index is not None:
         return self.type.validate(value)
      else:
         klass = (das.types.Sequence if self.size is None else das.types.Tuple)
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
         tmp = [None] * n
         for index, item in enumerate(value):
            try:
               tmp[index] = self.type.validate(item)
            except ValidationError, e:
               raise ValidationError("Invalid sequence element: %s" % e)
         rv = klass(tmp)
         rv._set_schema_type(self)
         return rv

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
      super(Tuple, self).__init__(default=kwargs.get("default", None))
      self.types = args

   def validate(self, value, key=None, index=None):
      if index is not None:
         return self.types[index].validate(value)
      else:
         if not isinstance(value, (list, tuple)):
            raise ValidationError("Expected a tuple value, got %s" % type(value).__name__)
         n = len(value)
         if n != len(self.types):
            raise ValidationError("Expected a tuple of size %d, got %d", (len(self.types), n))
         tmp = [None] * n
         for i in xrange(n):
            try:
               tmp[i] = self.types[i].validate(value[i])
            except ValidationError, e:
               raise ValidationError("Invalid tuple element: %s" % e)
         rv = das.types.Tuple(tmp)
         rv._set_schema_type(self)
         return rv

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = tuple([t.make_default() for t in self.types])
      return super(Tuple, self).make_default()

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
      TypeValidator.__init__(self, default={})
      if hasdefault:
         kwargs["default"] = default
      dict.__init__(self, **kwargs)

   def validate(self, value, key=None, index=None):
      if key is not None:
         if not key in self:
            return das.adapt_value(value)
         else:
            return self[key].validate(value)
      else:
         if not isinstance(value, (dict, das.types.Struct)):
            raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
         rv = das.types.Struct()
         for k, v in self.iteritems():
            if not k in value:
               if not isinstance(v, Optional):
                  raise ValidationError("Missing key '%s'" % k)
            else:
               try:
                  rv[k] = v.validate(value[k])
               except ValidationError, e:
                  raise ValidationError("Invalid value for key '%s': %s" % (k, e))
         rv._set_schema_type(self)
         return rv

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
      super(Dict, self).__init__(default=({} if default is None else default))
      self.ktype = ktype
      self.vtype = vtype
      self.vtypeOverrides = {}
      for k, v in kwargs.iteritems():
         self.vtypeOverrides[k] = v

   def validate(self, value, key=None, index=None):
      if key is not None:
         sk = str(key)
         return self.vtypeOverrides.get(sk, self.vtype).validate(value)
      else:
         if not isinstance(value, (dict, das.types.Struct)):
            raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
         rv = das.types.Dict()
         for k in value:
            try:
               ak = self.ktype.validate(k)
            except ValidationError, e:
               raise ValidationError("Invalid key value '%s': %s" % (k, e))
            try:
               sk = str(ak)
               rv[ak] = self.vtypeOverrides.get(sk, self.vtype).validate(value[k])
            except ValidationError, e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))
         rv._set_schema_type(self)
         return rv

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
      super(Class, self).__init__(default=(klass() if default is None else default))
      self.klass = klass

   def validate(self, value, key=None, index=None):
      if not isinstance(value, self.klass):
         raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(value).__name__))
      return value

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
