import re
import das
import imp


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   def __init__(self, default=None, description=None):
      super(TypeValidator, self).__init__()
      self.default_validated = False
      self.default = default
      self.description = ("" if description is None else description)

   def validate(self, value, key=None, index=None):
      mixins = (None if not das.has_bound_mixins(value) else das.get_bound_mixins(value))
      rv = self._validate(value, key=key, index=index)
      if mixins is not None:
         # Re-bind the same mixins that were found on original value
         das.mixin.bind(mixins, rv, reset=True)
      elif key is None and index is None and not das.has_bound_mixins(rv):
         # Bind registered mixins for return value type if nothing bound yet
         mixins = das.get_registered_mixins(das.get_schema_type_name(self))
         if mixins:
            das.mixin.bind(mixins, rv)
      # Try to call custom validation function
      return das.types.TypeBase.ValidateGlobally(rv)

   def _validate_self(self, value):
      raise ValidationError("'_validate_self' method is not implemented")

   def _validate(self, value, key=None, index=None):
      raise ValidationError("'_validate' method is not implemented")

   def make_default(self):
      if not self.default_validated:
         self.default = self.validate(self.default)
         self.default_validated = True
      return das.copy(self.default)

   def make(self, *args, **kwargs):
      return self._validate(args[0])

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   def __init__(self, default=None, description=None):
      super(Boolean, self).__init__(default=(False if default is None else default), description=description)

   def _validate_self(self, value):
      if not isinstance(value, bool):
         raise ValidationError("Expected a boolean value, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def __repr__(self):
      s = "Boolean("
      sep = ""
      if self.default is not None:
         s += "default=%s" % self.default
         sep = ", "
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"


class Integer(TypeValidator):
   def __init__(self, default=None, min=None, max=None, enum=None, description=None):
      super(Integer, self).__init__(default=(0 if default is None else default), description=description)
      self.min = min
      self.max = max
      self.enum = enum
      if self.enum is not None:
         self.enumvals = set(self.enum.values())

   def _validate_self(self, value):
      if self.enum is not None:
         if isinstance(value, basestring):
            v = das.ascii_or_unicode(value)
            if not v in self.enum:
               raise ValidationError("Expected a enumeration string in %s, got %s" % (self.enum.keys(), repr(value)))
            else:
               value = self.enum[v]
         elif isinstance(value, (int, long)):
            if not value in self.enumvals:
               raise ValidationError("Expected a enumeration value (string or integer) in %s, got %s" % (self.enum, value))
      if not isinstance(value, (int, long)):
         raise ValidationError("Expected an integer value, got %s" % type(value).__name__)
      if self.enum is None:
         if self.min is not None and value < self.min:
            raise ValidationError("Integer value out of range, %d < %d" % (value, self.min))
         if self.max is not None and value > self.max:
            raise ValidationError("Integer value out of range, %d > %d" % (value, self.max))
      return long(value)

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def _decode(self, encoding):
      if self.enum:
         e = {}
         for k, v in self.enum.iteritems():
            e[das.decode(k, encoding)] = v
         self.enum = e
      return self

   def __repr__(self):
      s = "Integer(";
      sep = ""
      if self.default is not None and self.default != 0:
         s += "default=%s" % self.default
         sep = ", "
      if self.min is not None:
         s += "%smin=%d" % (sep, self.min)
         sep = ", "
      if self.max is not None:
         s += "%smax=%d" % (sep, self.max)
         sep = ", "
      if self.enum is not None:
         s += "%senum={%s}" % (sep, ", ".join(map(lambda x: "'%s': %s" % x, self.enum.items())))
         sep = ", "
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"


class Real(TypeValidator):
   def __init__(self, default=None, min=None, max=None, description=None):
      super(Real, self).__init__(default=(0.0 if default is None else default), description=description)
      self.min = min
      self.max = max

   def _validate_self(self, value):
      if not isinstance(value, (int, long, float)):
         raise ValidationError("Expected a real value, got %s" % type(value).__name__)
      if self.min is not None and value < self.min:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))
      if self.max is not None and value > self.max:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))
      return float(value)

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def __repr__(self):
      s = "Real(";
      sep = ""
      if self.default is not None and self.default != 0.0:
         s += "default=%s" % self.default
         sep = ", "
      if self.min is not None:
         s += "%smin=%d" % (sep, self.min)
         sep = ", "
      if self.max is not None:
         s += "%smax=%d" % (sep, self.max)
         sep = ", "
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"


class String(TypeValidator):
   def __init__(self, default=None, choices=None, matches=None, strict=True, description=None):
      super(String, self).__init__(default=("" if default is None else default), description=description)
      self.choices = choices
      self.strict = strict
      self.matches = None
      if choices is None and matches is not None:
         if isinstance(matches, basestring):
            self.matches = re.compile(matches)
         elif isinstance(matches, re._pattern_type):
            self.matches = matches
         else:
            raise Exception("String schema type 'matches' option must be a string or a compiled regular expression")

   def _validate_self(self, value):
      if not isinstance(value, basestring):
         raise ValidationError("Expected a string value, got %s" % type(value).__name__)
      v = das.ascii_or_unicode(value)
      if self.choices is not None and self.strict:
         if callable(self.choices):
            choices = map(lambda x: das.ascii_or_unicode(x), self.choices())
         else:
            choices = self.choices
         if not v in choices:
            raise ValidationError("String value must be on of %s, got %s" % (repr(choices), repr(v)))
      if self.matches is not None and not self.matches.match(v):
         raise ValidationError("String value %s doesn't match pattern '%s'" % (repr(value), self.matches.pattern))
      return v

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def _decode(self, encoding):
      if self.default:
         self.default = das.decode(self.default, encoding)
      if self.choices:
         if not callable(self.choices):
            self.choices = map(lambda x: das.decode(x, encoding), self.choices)
      if self.matches:
         if isinstance(self.matches, basestring):
            self.matches = das.decode(self.matches, encoding)
      return self

   def __repr__(self):
      s = "String(";
      sep = ""
      if self.default is not None and self.default != "":
         s += "default=%s" % repr(self.default)
         sep = ", "
      if self.choices is not None:
         if callable(self.choices):
            if self.choices.__module__ != "__main__":
               s += "%schoices=%s" % (sep, self.choices.__name__)
            else:
               s += "%schoices=%s.%s" % (sep, self.choices.__module__, self.choices.__name__)
         else:
            s += "%schoices=[" % sep
            isep = ""
            for c in self.choices:
               s += "%s%s" % (isep, repr(c))
               isep = ", "
            s += "]"
         sep = ", "
         s += "%sstrict=%s" % (sep, self.strict)
      if self.matches is not None:
         s += "%smatches=%s" % (sep, repr(self.matches.pattern))
         sep = ", "
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"


class Set(TypeValidator):
   def __init__(self, type, default=None, description=None):
      super(Set, self).__init__(default=(set() if default is None else default), description=description)
      self.type = type

   def _validate_self(self, value):
      if not isinstance(value, (tuple, list, set)):
         raise ValidationError("Expected a set value, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      if index is not None:
         return self.type.validate(value)
      else:
         self._validate_self(value)
         tmp = [None] * len(value)
         i = 0
         for item in value:
            try:
               tmp[i] = self.type.validate(item)
            except ValidationError, e:
               raise ValidationError("Invalid set element: %s" % e)
            i += 1
         rv = das.types.Set(tmp)
         rv._set_schema_type(self)
         return rv

   def make(self, *args, **kwargs):
      return self._validate(args)

   def __repr__(self):
      s = "Set(type=%s" % self.type
      if self.default:
         s += ", default=%s" % self.default
      if self.description:
         s += ", description=%s" % repr(self.description)
      return s + ")"


class Sequence(TypeValidator):
   def __init__(self, type, default=None, size=None, min_size=None, max_size=None, description=None):
      super(Sequence, self).__init__(default=([] if default is None else default), description=description)
      self.size = size
      self.min_size = min_size
      self.max_size = max_size
      self.type = type

   def _validate_self(self, value):
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
      return value

   def _validate(self, value, key=None, index=None):
      if index is not None:
         return self.type.validate(value)
      else:
         self._validate_self(value)
         n = len(value)
         tmp = [None] * n
         for index, item in enumerate(value):
            try:
               tmp[index] = self.type.validate(item)
            except ValidationError, e:
               raise ValidationError("Invalid sequence element: %s" % e)
         rv = das.types.Sequence(tmp)
         rv._set_schema_type(self)
         return rv

   def make(self, *args, **kwargs):
      return self._validate(args)

   def __repr__(self):
      s = "Sequence(type=%s" % self.type
      sep = ", "
      if self.default:
         s += "%sdefault=%s" % (sep, self.default)
      if self.size is not None:
         s += "%ssize=%d" % (sep, self.size)
      else:
         if self.min_size is not None:
            s += "%smin_size=%d" % (sep, self.min_size)
         if self.max_size is not None:
            s += "%smax_size=%d" % (sep, self.max_size)
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"


class Tuple(TypeValidator):
   def __init__(self, *args, **kwargs):
      super(Tuple, self).__init__(default=kwargs.get("default", None), description=kwargs.get("description", None))
      self.types = args

   def _validate_self(self, value):
      if not isinstance(value, (list, tuple)):
         raise ValidationError("Expected a tuple value, got %s" % type(value).__name__)
      n = len(value)
      if n != len(self.types):
         raise ValidationError("Expected a tuple of size %d, got %d" % (len(self.types), n))
      return value

   def _validate(self, value, key=None, index=None):
      if index is not None:
         return self.types[index].validate(value)
      else:
         self._validate_self(value)
         n = len(value)
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

   def make(self, *args, **kwargs):
      return self._validate(args)

   def __repr__(self):
      s = "Tuple("
      sep = ""
      for t in self.types:
         s += "%s%s" % (sep, t)
         sep = ", "
      if self.default is not None:
         s += "%sdefault=%s" % (sep, self.default)
         sep = ", "
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"


class Struct(dict, TypeValidator):
   UseDefaultForMissingFields = False

   def __init__(self, **kwargs):
      hasdefault = ("default" in kwargs)
      default = None
      if hasdefault:
         default = kwargs["default"]
         print("[das] 'default' treated as a standard field for Struct type. Use '__default__' to set type's default value")
         del(kwargs["default"])
      
      hasdesc = ("description" in kwargs)
      desc = None
      if hasdesc:
         desc = kwargs["description"]
         print("[das] 'description' treated as standard field for Struct type. Use '__description__' to set type's description text")
         del(kwargs["description"])

      tdef = None
      if "__default__" in kwargs:
         tdef = kwargs["__default__"]
         del(kwargs["__default__"])

      tdesc = None
      if "__description__" in kwargs:
         tdesc = kwargs["__description__"]
         del(kwargs["__description__"])

      TypeValidator.__init__(self, default=tdef, description=tdesc)

      if hasdefault:
         kwargs["default"] = default

      if hasdesc:
         kwargs["description"] = desc

      dict.__init__(self, **kwargs)

   def _validate_self(self, value):
      if not isinstance(value, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
      for k, v in self.iteritems():
         # Don't check aliases
         if isinstance(v, Alias):
            continue
         if not k in value and not isinstance(v, Optional):
            if self.UseDefaultForMissingFields:
               # print("[das] Use default value for field '%s'" % k)
               value[k] = v.make_default()
            else:
               raise ValidationError("Missing key '%s'" % k)
      return value

   def _validate(self, value, key=None, index=None):
      if key is not None:
         vtype = self.get(key, None)
         if vtype is None:
            # return das.adapt_value(value)
            raise ValidationError("Invalid key '%s'" % key)
         else:
            if isinstance(vtype, Alias):
               vtype = self[vtype.name]
            vv = vtype.validate(value)
            if vv is not None and isinstance(vtype, Deprecated):
               message = ("[das] Field %s is deprecated" % repr(key) if not vtype.message else vtype.message)
               das.print_once(message) 
            return vv
      else:
         self._validate_self(value)
         rv = das.types.Struct()
         # don't set schema type just yet
         for k, v in self.iteritems():
            # don't add aliases to dictionary
            if isinstance(v, Alias):
               continue
            try:
               vv = v.validate(value[k])
               if vv is not None and isinstance(v, Deprecated):
                  message = ("[das] Field %s is deprecated" % repr(key) if not v.message else v.message)
                  das.print_once(message)
               rv[k] = vv
            except KeyError, e:
               if not isinstance(v, Optional):
                  raise ValidationError("Invalid value for key '%s': %s" % (k, e))
            except ValidationError, e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))
         rv._set_schema_type(self)
         return rv

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = das.types.Struct()
         for k, t in self.iteritems():
            if isinstance(t, (Alias, Optional)):
               continue
            self.default[k] = t.make_default()
         self.default._set_schema_type(self)
      return super(Struct, self).make_default()

   def make(self, *args, **kwargs):
      rv = self.make_default()
      for k, v in kwargs.iteritems():
         setattr(rv, k, v)
      return rv

   def __hash__(self):
      return object.__hash__(self)

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


class StaticDict(Struct):
   def __init__(self, **kwargs):
      super(StaticDict, self).__init__(**kwargs)
      das.print_once("[das] Warning: Schema type 'StaticDict' is deprecated, use 'Struct' instead")


class Dict(TypeValidator):
   def __init__(self, ktype, vtype, **kwargs):
      if "default" in kwargs:
         print("[das] 'default' treated as a possible key name for Dict type overrides. Use '__default__' to set type's default value")
      if "description" in kwargs:
         print("[das] 'description' treated as a possible key name for Dict type overrides. Use '__description__' to set type's description text")
      default = kwargs.get("__default__", None)
      description = kwargs.get("__description__", None)
      super(Dict, self).__init__(default=({} if default is None else default), description=description)
      self.ktype = ktype
      self.vtype = vtype
      self.vtypeOverrides = {}
      for k, v in kwargs.iteritems():
         self.vtypeOverrides[k] = v

   def _validate_self(self, value):
      if not isinstance(value, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      if key is not None:
         sk = str(key)
         return self.vtypeOverrides.get(sk, self.vtype).validate(value)
      else:
         self._validate_self(value)
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

   def make(self, *args, **kwargs):
      return self._validate(kwargs)

   def __repr__(self):
      s = "Dict(ktype=%s, vtype=%s" % (self.ktype, self.vtype)
      if self.default is not None:
         s += ", __default__=%s" % self.default
      for k, v in self.vtypeOverrides.iteritems():
         s += ", %s=%s" % (k, v)
      if self.description:
         s += ", __description__=%s" % repr(self.description)
      return s + ")"


class DynamicDict(Dict):
   def __init__(self, ktype, vtype, **kwargs):
      super(DynamicDict, self).__init__(ktype, vtype, **kwargs)
      das.print_once("[das] Warning: Schema type 'DynamicDict' is deprecated, use 'Dict' instead")


class Class(TypeValidator):
   def __init__(self, klass, default=None, description=None):
      if not isinstance(klass, (str, unicode)):
         self.klass = self._validate_class(klass)
      else:
         self.klass = self._class(klass)
      super(Class, self).__init__(default=(self.klass() if default is None else default), description=description)

   def _validate_class(self, c):
      if not hasattr(c, "copy"):
         raise Exception("Schema class '%s' has no 'copy' method" % c.__name__)
      try:
         c()
      except:
         raise Exception("Schema class '%s' constructor cannot be used without arguments" % c.__name__)
      return c

   def _class(self, class_name):
      c = None
      for i in class_name.split("."):
         if c is None:
            g = globals()
            if not i in g:
               c = imp.load_module(i, *imp.find_module(i))
            else:
               c = globals()[i]
         else:
            c = getattr(c, i)
      return self._validate_class(c)

   def _validate_self(self, value):
      if not isinstance(value, self.klass):
         raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(value).__name__))
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def __repr__(self):
      cmod = self.klass.__module__
      if cmod != "__main__":
         cmod += "."
      else:
         cmod = ""
      s = "Class(\"%s%s\"" % (cmod, self.klass.__name__)
      if self.description:
         s += ", description=%s" % repr(self.description)
      s += ")"
      return s


class Or(TypeValidator):
   def __init__(self, *types, **kwargs):
      super(Or, self).__init__(default=kwargs.get("default", None), description=kwargs.get("description", None))
      if len(types) < 2:
         raise Exception("Schema type 'Or' requires at least two types") 
      self.types = types

   def _validate_self(self, value):
      for typ in self.types:
         try:
            return typ._validate_self(value)
         except ValidationError, e:
            continue
      raise ValidationError("Value of type %s doesn't match any of the allowed types" % type(value).__name__)
      return None

   def _validate(self, value, key=None, index=None):
      for typ in self.types:
         try:
            return typ.validate(value, key=key, index=index)
         except ValidationError, e:
            continue
      raise ValidationError("Value of type %s doesn't match any of the allowed types" % type(value).__name__)
      return None

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = self.types[0].make_default()
      return super(Or, self).make_default()

   def make(self, *args, **kwargs):
      return self.types[0].make(*args, **kwargs)

   def __repr__(self):
      s = "Or(%s" % ", ".join(map(str, self.types))
      if self.default is not None:
         s += ", default=%s" % self.default
      if self.description:
         s += ", description=%s" % repr(self.description)
      return s + ")"


class Optional(TypeValidator):
   def __init__(self, type):
      super(Optional, self).__init__()
      self.type = type

   def _validate_self(self, value):
      return self.type._validate_self(value)

   def _validate(self, value, key=None, index=None):
      return self.type.validate(value, key=key, index=index)

   def make_default(self):
      return self.type.make_default()

   def make(self, *args, **kwargs):
      return self.type.make(*args, **kwargs)

   def __repr__(self):
      return "Optional(type=%s)" % self.type


class Deprecated(Optional):
   def __init__(self, type, message=""):
      super(Deprecated, self).__init__(type)
      self.message = message

   def _validate_self(self, value):
      if value is None:
         return True
      else:
         return super(Deprecated, self)._validate_self(value)

   def _validate(self, value, key=None, index=None):
      if value is None:
         return True
      else:
         return super(Deprecated, self)._validate(value, key=key, index=index)

   def make_default(self):
      return None

   def __repr__(self):
      return "Deprecated(type=%s)" % self.type


class Empty(TypeValidator):
   def __init__(self):
      super(Empty, self).__init__()

   def _validate_self(self, value):
      if value is not None:
         raise ValidationError("Expected None, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def make_default(self):
      return None

   def __repr__(self):
      return "Empty()"


class Alias(TypeValidator):
   def __init__(self, name):
      super(Alias, self).__init__()
      self.name = name

   def _validate_self(self, value):
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def make_default(self):
      return None

   def __repr__(self):
      return "Alias(%s)" % repr(self.name)


class SchemaType(TypeValidator):
   CurrentSchema = ""

   def __init__(self, name, default=None):
      super(SchemaType, self).__init__(default=default)
      if not "." in name:
         self.name = self.CurrentSchema + "." + name
      else:
         self.name = name

   def _validate_self(self, value):
      st = das.get_schema_type(self.name)
      return st._validate_self(value)

   def _validate(self, value, key=None, index=None):
      st = das.get_schema_type(self.name)
      return st.validate(value, key=key, index=index)

   def make_default(self):
      if not self.default_validated and self.default is None:
         st = das.get_schema_type(self.name)
         self.default = st.make_default()
      return super(SchemaType, self).make_default()

   def make(self, *args, **kwargs):
      st = das.get_schema_type(self.name)
      return st.make(*args, **kwargs)

   def __repr__(self):
      s = "SchemaType('%s'" % self.name
      if self.default is not None:
         s += ", default=%s" % str(self.default)
      return s + ")"
