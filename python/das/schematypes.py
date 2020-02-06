import re
import das
import imp


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   def __init__(self, default=None, description=None, editable=True, hidden=False, **kwargs):
      super(TypeValidator, self).__init__(**kwargs)
      self.default_validated = False
      self.default = default
      # UI related info
      self.description = ("" if description is None else description)
      self.editable = editable
      self.hidden = hidden

   def value_to_string(self, v):
      return repr(self._validate(v))

   def string_to_value(self, v):
      return self._validate(eval(v))

   def _validate_self(self, value):
      raise ValidationError("'_validate_self' method is not implemented")

   def _validate(self, value, key=None, index=None):
      raise ValidationError("'_validate' method is not implemented")

   def _is_compatible(self, value, key=None, index=None):
      try:
         self._validate(value, key=key, index=index)
         return True
      except:
         return False

   def _decode(self, encoding):
      if self.description is not None:
         self.description = das.decode(self.description, encoding)
      if self.default is not None:
         self.default = das.decode(self.default, encoding)
      return self

   def is_compatible(self, value, key=None, index=None):
      return self._is_compatible(value, key=key, index=index)

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

   def make_default(self):
      if not self.default_validated:
         self.default = self.validate(self.default)
         self.default_validated = True
      return das.copy(self.default)

   def make(self, *args, **kwargs):
      return self._validate(args[0])

   def partial_make(self, args):
      return self._validate(args)

   def conform(self, args, fill=False):
      return self.validate(args)

   def copy(self):
      return TypeValidator(default=self.default, description=self.description, editable=self.editable, hidden=self.hidden)

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   TrueExp = re.compile(r"^(1|yes|on|true)$", re.IGNORECASE)
   FalseExp = re.compile(r"^(0|no|off|false)$", re.IGNORECASE)

   def __init__(self, default=None, description=None, editable=True, hidden=False):
      super(Boolean, self).__init__(default=(False if default is None else default), description=description, editable=editable, hidden=hidden)

   def _validate_self(self, value):
      if not isinstance(value, bool):
         if isinstance(value, basestring):
            if self.TrueExp.match(value):
               return True
            elif self.FalseExp.match(value):
               return False
            else:
               raise ValidationError("String as boolean must match either '%s' or '%s'" % (self.TrueExp.pattern[2:-2], self.FalseExp.pattern[2:-2]))
         else:
            raise ValidationError("Expected a boolean or string value, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def value_to_string(self, v):
      return "true" if self._validate(v) else "false"

   def string_to_value(self, v):
      if v == "true":
         self._validate(True)
      elif v == "false":
         self._validate(False)

      return self._validate(v)

   def __repr__(self):
      s = "Boolean("
      sep = ""
      if self.default is not None:
         s += "default=%s" % self.default
         sep = ", "
      if self.description:
         s += "%sdescription=%s" % (sep, repr(self.description))
      return s + ")"

   def copy(self):
      return Boolean(default=self.default, description=self.description, editable=self.editable, hidden=self.hidden)


class Integer(TypeValidator):
   def __init__(self, default=None, min=None, max=None, enum=None, description=None, editable=True, hidden=False):
      super(Integer, self).__init__(default=(0 if default is None else default), description=description, editable=editable, hidden=hidden)
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
      super(Integer, self)._decode(encoding)
      if self.enum:
         e = {}
         for k, v in self.enum.iteritems():
            e[das.decode(k, encoding)] = v
         self.enum = e
         self.enumvals = set(self.enum.values())
      return self

   def value_to_string(self, v):
      return str(self._validate(v))

   def string_to_value(self, v):
      return self._validate(int(v))

   def __repr__(self):
      s = "Integer("
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

   def copy(self):
      return Integer(default=self.default, min=self.min, max=self.max, enum=self.enum, description=self.description, editable=self.editable, hidden=self.hidden)


class Real(TypeValidator):
   def __init__(self, default=None, min=None, max=None, description=None, editable=True, hidden=False):
      super(Real, self).__init__(default=(0.0 if default is None else default), description=description, editable=editable, hidden=hidden)
      self.min = min
      self.max = max

   def _validate_self(self, value):
      if not isinstance(value, (int, long, float)):
         raise ValidationError("Expected a real value, got %s" % type(value).__name__)
      if self.min is not None and value < self.min:
         raise ValidationError("Real value out of range, %d < %d" % (value, self.min))
      if self.max is not None and value > self.max:
         raise ValidationError("Real value out of range, %d > %d" % (value, self.max))
      return float(value)

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def value_to_string(self, v):
      return str(self._validate(v))

   def string_to_value(self, v):
      return self._validate(float(v))

   def __repr__(self):
      s = "Real("
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

   def copy(self):
      return Real(default=self.default, min=self.min, max=self.max, description=self.description, editable=self.editable, hidden=self.hidden)



class String(TypeValidator):
   def __init__(self, default=None, choices=None, matches=None, strict=True, description=None, editable=True, hidden=False):
      super(String, self).__init__(default=("" if default is None else default), description=description, editable=editable, hidden=hidden)
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
      super(String, self)._decode(encoding)
      if self.choices:
         if not callable(self.choices):
            self.choices = map(lambda x: das.decode(x, encoding), self.choices)
      if self.matches:
         self.matches = re.compile(das.decode(self.matches.pattern, encoding))
      return self

   def value_to_string(self, v):
      return str(self._validate(v))

   def string_to_value(self, v):
      return self._validate(v)

   def __repr__(self):
      s = "String("
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

   def copy(self):
      return String(default=self.default, choices=self.choices, matches=self.matches, strict=self.strict, description=self.description, editable=self.editable, hidden=self.hidden)


class Set(TypeValidator):
   def __init__(self, type, default=None, description=None, editable=True, hidden=False):
      super(Set, self).__init__(default=(set() if default is None else default), description=description, editable=editable, hidden=hidden)
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

   def _decode(self, encoding):
      super(Set, self)._decode(encoding)
      self.type = das.decode(self.type, encoding)
      return self

   def make(self, *args, **kwargs):
      return self._validate(args)

   def conform(self, args, fill=False):
      if not isinstance(args, (list, set, tuple)):
         raise ValidationError("Expected a sequence value, got %s" % type(args).__name__)

      rv = set()
      for arg in args:
         rv.add(self.type.conform(arg, fill=fill))

      return self.validate(rv)

   def partial_make(self, args):
      if not isinstance(args, (list, set, tuple)):
         raise ValidationError("Expected a sequence value, got %s" % type(args).__name__)

      rv = das.types.Set(map(lambda x: self.type.partial_make(x), args))
      rv._set_schema_type(self)
      return rv

   def __repr__(self):
      s = "Set(type=%s" % self.type
      if self.default:
         s += ", default=%s" % self.default
      if self.description:
         s += ", description=%s" % repr(self.description)
      return s + ")"

   def copy(self):
      return Set(self.type.copy(), default=self.default, description=self.description, editable=self.editable, hidden=self.hidden)


class Sequence(TypeValidator):
   def __init__(self, type, default=None, size=None, min_size=None, max_size=None, description=None, editable=True, hidden=False):
      super(Sequence, self).__init__(default=([] if default is None else default), description=description, editable=editable, hidden=hidden)
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

   def _decode(self, encoding):
      super(Sequence, self)._decode(encoding)
      self.type = das.decode(self.type, encoding)
      return self

   def make(self, *args, **kwargs):
      return self._validate(args)

   def conform(self, args, fill=False):
      if not isinstance(args, (list, set, tuple)):
         raise ValidationError("Expected a sequence value, got %s" % type(args).__name__)

      rv = list()
      for arg in args:
         rv.append(self.type.conform(arg, fill=fill))

      return self.validate(rv)

   def partial_make(self, args):
      if not isinstance(args, (list, set, tuple)):
         raise ValidationError("Expected a sequence value, got %s" % type(args).__name__)

      rv = das.types.Sequence(map(lambda x: self.type.partial_make(x), args))
      rv._set_schema_type(self)
      return rv

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

   def copy(self):
      return Sequence(self.type.copy(), default=self.default, size=self.size, min_size=self.min_size, max_size=self.max_size, description=self.description, editable=self.editable, hidden=self.hidden)


class Tuple(TypeValidator):
   def __init__(self, *args, **kwargs):
      super(Tuple, self).__init__(default=kwargs.get("default", None), description=kwargs.get("description", None), editable=kwargs.get("editable", True), hidden=kwargs.get("hidden", False))
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

   def _decode(self, encoding):
      super(Tuple, self)._decode(encoding)
      self.types = tuple(map(lambda x: das.decode(x, encoding), self.types))
      return self

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = tuple([t.make_default() for t in self.types])
      return super(Tuple, self).make_default()

   def make(self, *args, **kwargs):
      return self._validate(args)

   def conform(self, args, fill=False):
      if not isinstance(args, (list, set, tuple)):
         raise ValidationError("Expected a sequence value, got %s" % type(args).__name__)

      if len(args) != len(self.types):
         raise ValidationError("Expected a tuple of size %d, got %d" % (len(self.types), len(args)))

      rv = list()

      for i in range(len(args)):
         rv.append(self.types[i].conform(args[i], fill=fill))

      return self.validate(rv)

   def partial_make(self, args):
      if not isinstance(args, (list, set, tuple)):
         raise ValidationError("Expected a sequence value, got %s" % type(args).__name__)

      if len(args) != len(self.types):
         raise ValidationError("Expected a tuple of size %d, got %d" % (len(self.types), len(args)))

      rvs = []
      for i, arg in enumerate(args):
         rvs.append(self.types[i].partial_make(arg))
      rv = das.types.Tuple(rvs)
      rv._set_schema_type(self)
      return rv

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

   def copy(self):
      args = [t.copy() for t in self.types]
      kwargs = {"default": self.default,
                "description": self.description,
                "editable": self.editable,
                "hidden": self.hidden}
      return Tuple(*args, **kwargs)


class Struct(TypeValidator, dict):
   CompatibilityMode = False

   def __init__(self, __description__=None, __editable__=True, __hidden__=False, __order__=None, **kwargs):
      # MRO: TypeValidator, dict, object
      removedValues = {}
      for name in ("default", "description", "editable", "hidden"):
         if name in kwargs:
            removedValues[name] = kwargs[name]
            if das.__verbose__:
               das.print_once("[das] '%s' treated as a standard field for Struct type. Use '__%s__' to set schema type's attribute" % (name, name))
            del(kwargs[name])

      super(Struct, self).__init__(default=None, description=__description__, editable=__editable__, hidden=__hidden__, **kwargs)

      # Keep mapping of aliases
      aliases = {}
      for k, v in self.items():
         aliasname = Alias.Name(v)
         if aliasname is not None:
            aliases[k] = aliasname

      keys = [k for k, _ in self.items() if not k in aliases]
      if __order__ is not None:
         __order__ = filter(lambda x: x in keys, __order__)
         for n in keys:
            if not n in __order__:
               __order__.append(n)
      else:
         __order__ = sorted(keys)

      self.__dict__["_aliases"] = aliases
      self.__dict__["_order"] = __order__

      # As some fields were removed from kwargs to avoid conflict with
      #   TypeValidator class initializer, add them back

      for name, value in removedValues.iteritems():
         self[name] = value

   def _validate_self(self, value):
      if not isinstance(value, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
      allfound = True
      aliasvalues = {}
      for k, v in self.iteritems():
         aliasname = self.__dict__["_aliases"].get(k, None)
         if aliasname is not None and k in value:
            if aliasname in aliasvalues:
               if aliasvalues[aliasname] != value[k]:
                  raise ValidationError("Conflicting alias values for '%s'" % aliasname)
            else:
               aliasvalues[aliasname] = value[k]
      for k, v in self.iteritems():
         # Don't check aliases
         if k in self.__dict__["_aliases"]:
            continue
         if not k in value:
            if k in aliasvalues:
               value[k] = aliasvalues[k]
            elif not isinstance(v, Optional):
               allfound = False
               if self.CompatibilityMode:
                  # das.print_once("[das] Use default value for field '%s'" % k)
                  value[k] = v.make_default()
               else:
                  raise ValidationError("Missing key '%s'" % k)
         elif k in aliasvalues and value[k] != aliasvalues[k]:
            raise ValidationError("Conflicting alias values for '%s'" % k)
      # Ignore new keys only in compatibility mode if all base keys are fullfilled (forward compatibility)
      if not self.CompatibilityMode or not allfound:
         for k, _ in value.iteritems():
            if not k in self:
               raise ValidationError("Unknown key '%s'" % k)
      return value

   def _validate(self, value, key=None, index=None):
      if key is not None:
         vtype = self.get(key, None)
         if vtype is None:
            # return das.adapt_value(value)
            raise ValidationError("Invalid key '%s'" % key)
         else:
            deprecated = isinstance(vtype, Deprecated)
            aliasname = Alias.Name(vtype)
            if aliasname is not None:
               vtype = self[aliasname]
            vv = vtype.validate(value)
            if vv is not None and deprecated:
               message = ("[das] Field %s is deprecated" % repr(key) if not vtype.message else vtype.message)
               if aliasname is not None:
                  message += ", use %s instead" % aliasname
               das.print_once(message) 
            return vv
      else:
         self._validate_self(value)
         rv = das.types.Struct()
         # don't set schema type just yet
         for k, v in self.iteritems():
            # don't add aliases to dictionary
            deprecated = isinstance(v, Deprecated)
            aliasname = Alias.Name(v)
            if aliasname is not None:
               # Issue warning on deprecated field
               if deprecated:
                  message = "[das] Field %s is deprecated, use %s instead" % (repr(k), repr(aliasname))
                  das.print_once(message)
               continue
            try:
               vv = v.validate(value[k])
               if vv is not None and deprecated:
                  message = ("[das] Field %s is deprecated" % repr(k) if not v.message else v.message)
                  das.print_once(message)
               rv[k] = vv
            except KeyError, e:
               if not isinstance(v, Optional):
                  raise ValidationError("Invalid value for key '%s': %s" % (k, e))
            except ValidationError, e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))
         rv._set_schema_type(self)
         return rv

   def _decode(self, encoding):
      super(Struct, self)._decode(encoding)
      for k in self.keys():
         self[k] = das.decode(self[k], encoding)
      return self

   def ordered_keys(self):
      return self.__dict__["_order"]

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

   def conform(self, args, fill=False):
      if not isinstance(args, dict):
         raise ValidationError("Expected a dict value, got %s" % type(args).__name__)

      rv = type(args)()

      for k in self:
         if k in args:
            rv[k] = self[k].conform(args[k], fill=fill)
         elif fill:
            rv[k] = self[k].make_default()

      return self.validate(rv)

   def partial_make(self, args):
      if not isinstance(args, dict):
         raise ValidationError("Expected a dict value, got %s" % type(args).__name__)

      rv = self.make_default()
      for k, v in args.iteritems():
         rv[k] = self[k].partial_make(v)

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
      if self.description:
         s += "%s__description__=%s" % (sep, repr(self.description))
      return s + ")"

   def copy(self):
      kwargs = {}
      for k, v in self.iteritems():
         kwargs[k] = v.copy()
      return Struct(__description__=self.description, __editable__=self.editable,
                    __hidden__=self.hidden, __order__=self.__dict__["_order"], **kwargs)


class StaticDict(Struct):
   def __init__(self, __description__=None, __editable__=True, __hidden__=False, __order__=None, **kwargs):
      super(StaticDict, self).__init__(__description__=__description__, __editable__=__editable__, __hidden__=__hidden__, __order__=__order__, **kwargs)
      if das.__verbose__:
         das.print_once("[das] Warning: Schema type 'StaticDict' is deprecated, use 'Struct' instead")


class Dict(TypeValidator):
   def __init__(self, ktype, vtype, __default__=None, __description__=None, __editable__=True, __hidden__=False, **kwargs):
      for name in ("default", "description", "editable", "hidden"):
         if name in kwargs:
            if das.__verbose__:
               das.print_once("[das] '%s' treated as a possible key name for Dict type overrides. Use '__%s__' to set schema type's attribute" % (name, name))
      super(Dict, self).__init__(default=({} if __default__ is None else __default__), description=__description__, editable=__editable__, hidden=__hidden__)
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

   def _decode(self, encoding):
      super(Dict, self)._decode(encoding)
      self.ktype = das.decode(self.ktype, encoding)
      self.vtype = das.decode(self.vtype, encoding)
      vtypeOverrides = {}
      for k, v in self.vtypeOverrides.iteritems():
         vtypeOverrides[das.decode(k, encoding)] = das.decode(v, encoding)
      self.vtypeOverrides = vtypeOverrides
      return self

   def make(self, *args, **kwargs):
      return self._validate(kwargs)

   def conform(self, args, fill=False):
      if not isinstance(args, dict):
         raise ValidationError("Expected a dict value, got %s" % type(args).__name__)

      rv = dict()

      for k, v in args.items():
         k = self.ktype.conform(k, fill=fill)
         rv[k] = self.vtype.conform(v, fill=fill)

      return self.validate(rv)

   def partial_make(self, args):
      if not isinstance(args, dict):
         raise ValidationError("Expected a dict value, got %s" % type(args).__name__)

      rv = das.types.Dict()

      for k, v in args.iteritems():
         rv[self.ktype.validate(k)] = self.vtype.partial_make(v)
      rv._set_schema_type(self)
      return rv

   def __repr__(self):
      s = "Dict(ktype=%s, vtype=%s" % (self.ktype, self.vtype)
      for k, v in self.vtypeOverrides.iteritems():
         s += ", %s=%s" % (k, v)
      if self.default is not None:
         s += ", __default__=%s" % self.default
      if self.description:
         s += ", __description__=%s" % repr(self.description)
      return s + ")"

   def copy(self):
      kwargs = {}
      for k, v in self.vtypeOverrides.iteritems():
         kwargs[k] = v.copy()
      return Dict(self.ktype.copy(), self.vtype.copy(),
                  __default__=self.default, __description__=self.description, __editable__=self.editable,
                  __hidden__=self.hidden, **kwargs)


class DynamicDict(Dict):
   def __init__(self, ktype, vtype, __default__=None, __description__=None, __editable__=True, __hidden__=False, **kwargs):
      super(DynamicDict, self).__init__(ktype, vtype, __default__=__default__, __description__=__description__, __editable__=__editable__, __hidden__=__hidden__, **kwargs)
      if das.__verbose__:
         das.print_once("[das] Warning: Schema type 'DynamicDict' is deprecated, use 'Dict' instead")


class Class(TypeValidator):
   def __init__(self, klass, default=None, description=None, editable=True, hidden=False):
      if not isinstance(klass, (str, unicode)):
         self.klass = self._validate_class(klass)
      else:
         self.klass = self._class(klass)
      super(Class, self).__init__(default=(self.klass() if default is None else default), description=description, editable=editable, hidden=hidden)

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
         if isinstance(value, basestring) and hasattr(self.klass, "string_to_value"):
            try:
               newval = self.klass()
               newval.string_to_value(value)
               return newval
            except Exception, e:
               raise ValidationError("Cannot instanciace class '%s' from string %s" % (self.klass.__name__, repr(value)))
         else:
            raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(value).__name__))
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   # No _decode?

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

   def copy(self):
      return Class(self.klass, default=self.default, description=self.description, editable=self.editable, hidden=self.hidden)


class Or(TypeValidator):
   def __init__(self, *types, **kwargs):
      super(Or, self).__init__(default=kwargs.get("default", None), description=kwargs.get("description", None), editable=kwargs.get("editable", True), hidden=kwargs.get("hidden", False))
      if len(types) < 2:
         raise Exception("Schema type 'Or' requires at least two types") 
      self.types = types

   def _validate_self(self, value):
      # even in compat mode, look for an exact match first
      if Struct.CompatibilityMode:
         rv = None
         Struct.CompatibilityMode = False
         for typ in self.types:
            try:
               rv = typ._validate_self(value)
               break
            except ValidationError, e:
               continue
         Struct.CompatibilityMode = True
         if rv is not None:
            return rv
      for typ in self.types:
         try:
            return typ._validate_self(value)
         except ValidationError, e:
            continue
      raise ValidationError("Value of type %s doesn't match any of the allowed types" % type(value).__name__)
      return None

   def _validate(self, value, key=None, index=None):
      if Struct.CompatibilityMode:
         rv = None
         Struct.CompatibilityMode = False
         for typ in self.types:
            try:
               rv = typ.validate(value, key=key, index=index)
               break
            except ValidationError, e:
               continue
         Struct.CompatibilityMode = True
         if rv is not None:
            return rv
      for typ in self.types:
         try:
            return typ.validate(value, key=key, index=index)
         except ValidationError, e:
            continue
      raise ValidationError("Value of type %s doesn't match any of the allowed types" % type(value).__name__)
      return None

   def value_to_string(self, v):
      for typ in self.types:
         try:
            return typ.value_to_string(v)
         except:
            continue

   def string_to_value(self, v):
      for typ in self.types:
         try:
            return typ.string_to_value(v)
         except:
            continue

   def _decode(self, encoding):
      super(Or, self)._decode(encoding)
      self.types = tuple(map(lambda x: das.decode(x, encoding), self.types))
      return self

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = self.types[0].make_default()
      return super(Or, self).make_default()

   def make(self, *args, **kwargs):
      return self.types[0].make(*args, **kwargs)

   def conform(self, args, fill=False):
      for typ in self.types:
         try:
            return typ.conform(args, fill=fill)
         except ValidationError, e:
            continue

      raise ValidationError("Value of type %s doesn't match any of the allowed types" % type(args).__name__)

   def partial_make(self, args):
      for typ in self.types:
         try:
            return typ.partial_make(args)
         except:
            continue

      raise ValidationError("Value of type %s doesn't match any of the allowed types" % type(args).__name__)

   def __repr__(self):
      s = "Or(%s" % ", ".join(map(str, self.types))
      if self.default is not None:
         s += ", default=%s" % self.default
      if self.description:
         s += ", description=%s" % repr(self.description)
      return s + ")"

   def copy(self):
      types = [t.copy() for t in self.types]
      kwargs = {"default": self.default,
                "description": self.description,
                "editable": self.editable,
                "hidden": self.hidden}
      return Or(*types, **kwargs)


class Optional(TypeValidator):
   def __init__(self, type, description=None, editable=True, hidden=False):
      super(Optional, self).__init__(description=description, editable=editable, hidden=hidden)
      self.type = type

   def _validate_self(self, value):
      return self.type._validate_self(value)

   def _validate(self, value, key=None, index=None):
      return self.type.validate(value, key=key, index=index)

   def _decode(self, encoding):
      super(Optional, self)._decode(encoding)
      self.type = das.decode(self.type, encoding)
      return self

   def make_default(self):
      return self.type.make_default()

   def make(self, *args, **kwargs):
      return self.type.make(*args, **kwargs)

   def conform(self, args, fill=False):
      return self.type.conform(args, fill=fill)

   def partial_make(self, args):
      return self.type.partial_make(args)

   def value_to_string(self, v):
      return self.type.value_to_string(v)

   def string_to_value(self, v):
      return self.type.string_to_value(v)

   def __repr__(self):
      return "Optional(type=%s)" % self.type

   def copy(self):
      return Optional(self.type.copy(), description=self.description, editable=self.editable, hidden=self.hidden)


class Deprecated(Optional):
   def __init__(self, type, message="", description=None, editable=True, hidden=False):
      super(Deprecated, self).__init__(type, description=description, editable=editable, hidden=hidden)
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

   def _decode(self, encoding):
      super(Deprecated, self)._decode(encoding)
      self.message = das.decode(self.message, encoding)
      return self

   def make_default(self):
      return None

   def __repr__(self):
      return "Deprecated(type=%s)" % self.type

   def copy(self):
      return Deprecated(self.type.copy(), message=self.message, description=self.description, editable=self.editable, hidden=self.hidden)


class Empty(TypeValidator):
   def __init__(self, description=None, editable=True, hidden=False):
      super(Empty, self).__init__(description=description, editable=editable, hidden=hidden)

   def _validate_self(self, value):
      if value is not None:
         raise ValidationError("Expected None, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def make_default(self):
      return None

   def value_to_string(self, v):
      self._validate(v)

      return ""

   def string_to_value(self, v):
      if v:
         raise ValidationError("The value is not empty")

      return self._validate(None)

   def __repr__(self):
      return "Empty()"

   def copy(self):
      return Empty(description=self.description, editable=self.editable, hidden=self.hidden)


class Alias(TypeValidator):
   @staticmethod
   def Check(t):
      return (isinstance(t, Alias) or (isinstance(t, Deprecated) and isinstance(t.type, Alias)))

   @staticmethod
   def Name(t):
      if isinstance(t, Alias):
         return t.name
      elif isinstance(t, Deprecated) and isinstance(t.type, Alias):
         return t.type.name
      else:
         return None

   def __init__(self, name, description=None, editable=True, hidden=False):
      super(Alias, self).__init__(description=description, editable=editable, hidden=hidden)
      self.name = name

   def _validate_self(self, value):
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def make_default(self):
      return None

   def __repr__(self):
      return "Alias(%s)" % repr(self.name)

   def copy(self):
      return Alias(self.name, description=self.description, editable=self.editable, hidden=self.hidden)


class SchemaType(TypeValidator):
   CurrentSchema = ""

   def __init__(self, name, default=None, description=None, editable=True, hidden=False):
      super(SchemaType, self).__init__(default=default, description=description, editable=editable, hidden=hidden)
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

   def conform(self, args, fill=False):
      st = das.get_schema_type(self.name)
      return st.conform(args, fill=fill)

   def partial_make(self, args):
      st = das.get_schema_type(self.name)
      return st.partial_make(args)

   def __repr__(self):
      s = "SchemaType('%s'" % self.name
      if self.default is not None:
         s += ", default=%s" % str(self.default)
      return s + ")"

   def copy(self):
      return SchemaType(self.name, default=self.default, description=self.description, editable=self.editable)
