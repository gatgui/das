import re
import das
import imp


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   CurrentSchema = ""

   def __init__(self, default=None, description=None, editable=True, hidden=False,
                __properties__=None, **kwargs):
      super(TypeValidator, self).__init__(**kwargs)
      self.default_validated = False
      self.default = default
      # UI related info
      self.description = ("" if description is None else description)
      self.editable = editable
      self.hidden = hidden
      self._properties = {}
      if __properties__:
         for k, v in __properties__.iteritems():
            self._properties[k] = v
      # if not "mixins" in self._properties:
      #    self._properties["mixins"] = []

   def has_property(self, name):
      return name in self._properties

   def get_property(self, name, default=None):
      return self._properties.get(name, default)

   def get_properties(self):
      return self._properties.copy()

   def set_property(self, name, value):
      self._properties[name] = value

   def set_properties(self, props):
      self._properties = props

   def remove_property(self, name):
      if name in self._properties:
         del self._properties[name]

   def value_to_string(self, v):
      return repr(self.validate(v))

   def string_to_value(self, v):
      return self.validate(eval(v))

   def _validate_self(self, value):
      raise ValidationError("'_validate_self' method is not implemented")

   def _validate(self, value, key=None, index=None):
      raise ValidationError("'_validate' method is not implemented")

   def _decode(self, encoding):
      if self.description is not None:
         self.description = das.decode(self.description, encoding)
      if self.default is not None:
         self.default = das.decode(self.default, encoding)
      return self

   def is_compatible(self, value, key=None, index=None):
      try:
         self.validate(value, key=key, index=index)
         return True
      except:
         return False

   def real_type(self, parent=None):
      return self

   def is_type_compatible(self, st, key=None, index=None):
      return isinstance(st.real_type(), self.__class__)

   def validate(self, value, key=None, index=None):
      mixins = (None if not das.has_bound_mixins(value) else das.get_bound_mixins(value))
      rv = self._validate(value, key=key, index=index)
      if mixins is not None:
         # Re-bind the same mixins that were found on original value
         das.mixin.bind(mixins, rv, reset=True)
      elif key is None and index is None and not das.has_bound_mixins(rv):
         # Bind registered mixins for return value type if nothing bound yet
         #   (give precedence to registry query as it might hanled the case
         #    schema type objects with yet no mixins bound)
         stn = das.get_schema_type_name(self)
         if stn:
            mixins = das.get_registered_mixins(stn)
         else:
            mixins = self.get_property("mixins", None)
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
      return self.validate(args[0])

   def partial_make(self, args):
      return self.validate(args)

   def conform(self, args, fill=False):
      return self.validate(args)

   def copy(self):
      return TypeValidator(default=self.default, description=self.description,
                           editable=self.editable, hidden=self.hidden,
                           __properties__=self.get_properties())

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   TrueExp = re.compile(r"^(1|yes|on|true)$", re.IGNORECASE)
   FalseExp = re.compile(r"^(0|no|off|false)$", re.IGNORECASE)

   def __init__(self, default=None, description=None, editable=True, hidden=False,
                __properties__=None):
      super(Boolean, self).__init__(default=(False if default is None else default),
                                    description=description, editable=editable,
                                    hidden=hidden, __properties__=__properties__)

   def _validate_self(self, value):
      if not isinstance(value, bool):
         if isinstance(value, basestring):
            if self.TrueExp.match(value):
               return True
            elif self.FalseExp.match(value):
               return False
            else:
               raise ValidationError("String as boolean must match either '%s' or '%s'" %
                  (self.TrueExp.pattern[2:-2], self.FalseExp.pattern[2:-2]))
         else:
            raise ValidationError("Expected a boolean or string value, got %s" %
               type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   # No need to override is_type_compatible here, a Boolean matches another Boolean only

   def value_to_string(self, v):
      return "true" if self.validate(v) else "false"

   def string_to_value(self, v):
      return self.validate(v)

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
      return Boolean(default=self.default, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Integer(TypeValidator):
   def __init__(self, default=None, min=None, max=None, enum=None, description=None, editable=True, hidden=False, __properties__=None):
      super(Integer, self).__init__(default=(0 if default is None else default), description=description, editable=editable, hidden=hidden, __properties__=__properties__)
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

   def is_type_compatible(self, st, key=None, index=None):
      if not super(Integer, self).is_type_compatible(st, key=key, index=index):
         return False

      _st = st.real_type()

      if self.enum is not None:
         return (_st.enum is not None and _st.enum == self.enum)
      elif _st.enum is not None:
         return False

      if self.min is not None and (_st.min is None or _st.min < self.min):
         return False

      if self.max is not None and (_st.max is None or _st.max > self.max):
         return False

      return True

   def value_to_string(self, v):
      return str(self.validate(v))

   def string_to_value(self, v):
      return self.validate(int(v))

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
      return Integer(default=self.default, min=self.min, max=self.max, enum=self.enum, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Real(TypeValidator):
   def __init__(self, default=None, min=None, max=None, description=None, editable=True, hidden=False, __properties__=None):
      super(Real, self).__init__(default=(0.0 if default is None else default), description=description, editable=editable, hidden=hidden, __properties__=__properties__)
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

   def is_type_compatible(self, st, key=None, index=None):
      if not super(Real, self).is_type_compatible(st, key=key, index=index):
         return False

      _st = st.real_type()

      if self.min is not None and (_st.min is None or _st.min < self.min):
         return False

      if self.max is not None and (_st.max is None or _st.max > self.max):
         return False

      return True

   def value_to_string(self, v):
      return str(self.validate(v))

   def string_to_value(self, v):
      return self.validate(float(v))

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
      return Real(default=self.default, min=self.min, max=self.max, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class String(TypeValidator):
   def __init__(self, default=None, choices=None, matches=None, strict=True, description=None, editable=True, hidden=False, __properties__=None):
      super(String, self).__init__(default=("" if default is None else default), description=description, editable=editable, hidden=hidden, __properties__=__properties__)
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

   def _expand_choices(self, asSet=False):
      if self.choices is None:
         return None
      if callable(self.choices):
         rv = map(lambda x: das.ascii_or_unicode(x), self.choices())
      else:
         rv = self.choices
      return (set(rv) if asSet else rv)

   def _validate_self(self, value):
      if not isinstance(value, basestring):
         raise ValidationError("Expected a string value, got %s" % type(value).__name__)
      v = das.ascii_or_unicode(value)
      if self.choices is not None and self.strict:
         choices = self._expand_choices()
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

   def is_type_compatible(self, st, key=None, index=None):
      if not super(String, self).is_type_compatible(st, key=key, index=index):
         return False

      _st = st.real_type()

      if self.choices is not None and self.strict:
         if _st.choices is None or not _st.strict:
            return False
         else:
            s0 = self._expand_choices(asSet=True)
            s1 = _st._expand_choices(asSet=True)
            return (len(s0.symmetric_difference(s1)) == 0)

      if self.matches is not None:
         if _st.matches is None:
            if _st.choices and _st.strict:
               allchoicesmatch = all([self.matches.match(x) is not None for x in _st._expand_choices()])
               if not allchoicesmatch:
                  return False
            else:
               return False
         elif _st.matches.pattern != self.matches.pattern:
            return False

      return True

   def value_to_string(self, v):
      return str(self.validate(v))

   def string_to_value(self, v):
      return self.validate(v)

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
      return String(default=self.default, choices=self.choices, matches=self.matches, strict=self.strict, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Set(TypeValidator):
   def __init__(self, type, default=None, description=None, editable=True, hidden=False, __properties__=None):
      super(Set, self).__init__(default=(set() if default is None else default), description=description, editable=editable, hidden=hidden, __properties__=__properties__)
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
            except ValidationError as e:
               raise ValidationError("Invalid set element: %s" % e)
            i += 1
         rv = das.types.Set(tmp)
         rv._set_schema_type(self)
         return rv

   def _decode(self, encoding):
      super(Set, self)._decode(encoding)
      self.type = das.decode(self.type, encoding)
      return self

   def is_type_compatible(self, st, key=None, index=None):
      if index is not None:
         return self.type.is_type_compatible(st)
      else:
         if not super(Set, self).is_type_compatible(st, key=key, index=index):
            return False
         else:
            return self.type.is_type_compatible(st.real_type().type)

   def make(self, *args, **kwargs):
      return self.validate(args)

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
      return Set(self.type.copy(), default=self.default, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Sequence(TypeValidator):
   def __init__(self, type, default=None, size=None, min_size=None, max_size=None, description=None, editable=True, hidden=False, __properties__=None):
      super(Sequence, self).__init__(default=([] if default is None else default), description=description, editable=editable, hidden=hidden, __properties__=__properties__)
      self.size = size
      self.min_size = None
      self.max_size = None
      if size is None:
         if min_size is not None and max_size is not None and min_size == max_size:
            self.size = min_size
         else:
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
            except ValidationError as e:
               raise ValidationError("Invalid sequence element: %s" % e)
         rv = das.types.Sequence(tmp)
         rv._set_schema_type(self)
         return rv

   def _decode(self, encoding):
      super(Sequence, self)._decode(encoding)
      self.type = das.decode(self.type, encoding)
      return self

   def is_type_compatible(self, st, key=None, index=None):
      if index is not None:
         return self.type.is_type_compatible(st)
      else:
         if not super(Sequence, self).is_type_compatible(st, key=key, index=index):
            return False
         _st = st.real_type()
         if not self.type.is_type_compatible(_st.type):
            return False
         elif self.size is not None and (_st.size is None or _st.size != self.size):
            return False
         elif self.min_size is not None and (_st.min_size is None or _st.min_size < self.min_size):
            return False
         elif self.max_size is not None and (_st.max_size is None or _st.max_size > self.max_size):
            return False
         else:
            return True

   def make(self, *args, **kwargs):
      return self.validate(args)

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
      return Sequence(self.type.copy(), default=self.default, size=self.size, min_size=self.min_size, max_size=self.max_size, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Tuple(TypeValidator):
   def __init__(self, *args, **kwargs):
      super(Tuple, self).__init__(default=kwargs.get("default", None), description=kwargs.get("description", None), editable=kwargs.get("editable", True), hidden=kwargs.get("hidden", False), __properties__=kwargs.get("__properties__", None))
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
            except ValidationError as e:
               raise ValidationError("Invalid tuple element: %s" % e)
         rv = das.types.Tuple(tmp)
         rv._set_schema_type(self)
         return rv

   def _decode(self, encoding):
      super(Tuple, self)._decode(encoding)
      self.types = tuple(map(lambda x: das.decode(x, encoding), self.types))
      return self

   def is_type_compatible(self, st, key=None, index=None):
      if index is not None:
         return self.types[index].is_type_compatible(st)
      else:
         if not super(Tuple, self).is_type_compatible(st, key=key, index=index):
            return False
         _st = st.real_type()
         if len(_st.types) != len(self.types):
            return False
         else:
            for i in xrange(len(self.types)):
               if not self.types[i].is_type_compatible(_st.types[i]):
                  return False
            else:
               return True

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = tuple([t.make_default() for t in self.types])
      return super(Tuple, self).make_default()

   def make(self, *args, **kwargs):
      return self.validate(args)

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
                "hidden": self.hidden,
                "__properties__": self.get_properties()}
      return Tuple(*args, **kwargs)


class Struct(TypeValidator, dict):
   CompatibilityMode = False

   def __init__(self, __description__=None, __editable__=True, __hidden__=False, __order__=None, __extends__=None, __properties__=None, **kwargs):
      # MRO: TypeValidator, dict, object
      removedValues = {}
      for name in ("default", "description", "editable", "hidden"):
         if name in kwargs:
            removedValues[name] = kwargs[name]
            if das.__verbose__:
               das.print_once("[das] '%s' treated as a standard field for Struct type. Use '__%s__' to set schema type's attribute" % (name, name))
            del(kwargs[name])
      removedItems = removedValues.items()

      super(Struct, self).__init__(default=None, description=__description__, editable=__editable__, hidden=__hidden__, __properties__=__properties__, **kwargs)

      # Keep mapping of aliases
      self._aliases = {}
      for k, v in (self.items() + removedItems):
         aliasname = Alias.Name(v)
         if aliasname is not None:
            self._aliases[k] = aliasname

      # Build fields ordering
      self._fix_order(__order__, extraItems=removedItems)

      # Track schema to extend
      exttypes = ([] if not self.has_property("extensions") else self.get_property("extensions").keys())

      tmp = []
      if isinstance(__extends__, (list, tuple, set, dict)):
         tmp = [x for x in __extends__]
      elif __extends__:
         tmp = [__extends__]
      for exttype in tmp:
         _exttype = str(exttype)
         if not "." in _exttype:
            _exttype = self.CurrentSchema + "." + _exttype
         if not _exttype in exttypes:
            exttypes.append(_exttype)

      self.set_property("extensions", dict([(et, False) for et in exttypes]))

      # As some fields were removed from kwargs to avoid conflict with
      #   TypeValidator class initializer, add them back at last
      # Adding them before may cause problems as __setitem__ is triggered
      for name, value in removedValues.iteritems():
         self[name] = value

   def _fix_order(self, order, extraItems=None):
      keys = [k for k, _ in (self.items() + (extraItems or [])) if not k in self._aliases]
      if order is not None:
         self._original_order = list(order)
         self._order = filter(lambda x: x in keys, self._original_order)
         for n in keys:
            if not n in order:
               self._order.append(n)
      else:
         self._original_order = None
         self._order = sorted(keys)

   def _extend(self, name):
      st = das.get_schema_type(name)

      # Check for Struct schema type
      if not isinstance(st, Struct):
         raise Exception("Cannot inherit from %s schema types %s ()" % (type(st).__name__, repr(name)))

      # Check for conflicting fields but allow overrides
      for k in st.ordered_keys():
         if k in self:
            t0 = st[k].real_type(parent=st)
            t1 = self[k].real_type(parent=self)
            override = True
            if not t0.is_type_compatible(t1):
               override = False
            else:
               if not st._is_optional(k) and self._is_optional(k):
                  override = False
            if not override:
               raise Exception("Cannot inherit schema type %s (conflicting field %s)" % (repr(name), repr(k)))

      # Check for conflicting aliases
      aliases = self._aliases.copy()
      for n, a in st._aliases.iteritems():
         if n in self.ordered_keys():
            raise Exception("Cannot inherit schema type %s (alias %s -> %s conflicting with field)" % (repr(name), repr(n), repr(a)))
         if n in aliases:
            if aliases[n] != a:
               raise Exception("Cannot inherit schema type %s (conflicting alias %s -> %s / %s)" % (repr(name), repr(n), repr(a), aliases[n]))
         aliases[n] = a
      self._aliases = aliases

      if st._original_order or self._original_order:
         if st._original_order:
            _original_order = st._original_order[:]
            _tmp = (self._order[:] if not self._original_order else self._original_order[:])
         else:
            _original_order = self._original_order[:]
            _tmp = (st._order[:] if not st._original_order else st._original_order[:])
         for item in _tmp:
            if not item in _original_order:
               _original_order.append(item)
         self._original_order = _original_order

      # Merge fields
      for k in st.keys():
         # if we reach here and k is defined in self, it is a compatible override, keep it
         if not k in self:
            self[k] = st[k].copy()

      # Register and apply extra mixins
      mixins = das.get_registered_mixins(name)
      if mixins:
         das.register_mixins(*mixins, schema_type=self)

      # Reset default value
      self.default_validated = False
      self.default = None

   def _validate_self(self, value):
      if not isinstance(value, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(value).__name__)
      allfound = True
      aliasvalues = {}
      for k, v in self.iteritems():
         aliasname = self._aliases.get(k, None)
         if aliasname is not None and k in value:
            if aliasname in aliasvalues:
               if aliasvalues[aliasname] != value[k]:
                  raise ValidationError("Conflicting alias values for '%s'" % aliasname)
            else:
               aliasvalues[aliasname] = value[k]
      for k, v in self.iteritems():
         # Don't check aliases
         if k in self._aliases:
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
         actualkeys = set([item for item in value])
         rv = das.types.Struct()
         # don't set schema type just yet
         for k, v in self.iteritems():
            # don't add aliases to dictionary
            deprecated = isinstance(v, Deprecated)
            aliasname = Alias.Name(v)
            if aliasname is not None:
               # Issue warning on deprecated field
               if deprecated and k in actualkeys:
                  message = "[das] Field %s is deprecated, use %s instead" % (repr(k), repr(aliasname))
                  das.print_once(message)
               continue
            try:
               vv = v.validate(value[k])
               if vv is not None and deprecated:
                  message = ("[das] Field %s is deprecated" % repr(k) if not v.message else v.message)
                  das.print_once(message)
               rv[k] = vv
            except KeyError as e:
               if not isinstance(v, Optional):
                  raise ValidationError("Invalid value for key '%s': %s" % (k, e))
            except ValidationError as e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))
         rv._set_schema_type(self)
         return rv

   def _decode(self, encoding):
      super(Struct, self)._decode(encoding)
      for k in self.keys():
         self[k] = das.decode(self[k], encoding)
      return self

   def _aliased_type(self, nameOrType):
      if isinstance(nameOrType, basestring):
         vt = self[nameOrType]
      elif isinstance(nameOrType, TypeValidator):
         vt = nameOrType
      else:
         raise Exception("Expected 'str' or 'TypeValidator' instance got '%s'" % type(nameOrType).__name__)
      an = Alias.Name(vt)
      return (vt if an is None else self[an])

   def _is_alias(self, nameOrType):
      if isinstance(nameOrType, basestring):
         vt = self[nameOrType]
      elif isinstance(nameOrType, TypeValidator):
         vt = nameOrType
      else:
         raise Exception("Expected 'str' or 'TypeValidator' instance got '%s'" % type(nameOrType).__name__)
      an = Alias.Name(vt)
      return (an is not None)

   def _is_optional(self, name):
      return isinstance(self._aliased_type(name), Optional)

   def is_type_compatible(self, st, key=None, index=None):
      if key is not None:
         vtype = self.get(key, None)
         if vtype is None:
            return False
         else:
            # st is supposedly the type of the key
            return vtype.real_type(parent=self).is_type_compatible(st)
      else:
         if not super(Struct, self).is_type_compatible(st, key=key, index=index):
            return False
         _st = st.real_type()
         for k, v in self.iteritems():
            # don't add aliases to dictionary
            _vt0 = v.real_type(parent=self)
            if not k in _st:
               # only error if k is not an optional field
               if not self._is_optional(v):
                  return False
            else:
               _vt1 = _st[k].real_type(parent=_st)
               if not _vt0.is_type_compatible(_vt1):
                  return False
               # Non optional fields are not compatible with optional ones
               if not self._is_optional(v) and _st._is_optional(_st[k]):
                  return False
         # check for any fields in _st not in self
         for k, v in _st.iteritems():
            if _st._is_alias(v):
               continue
            if not k in self:
               # allow if it is optional? -> no
               return False
         return True

   def load_extensions(self):
      for et, ld in self._properties["extensions"].items():
         if not ld:
            self._extend(et)
            self._properties["extensions"][et] = True

   def has_extension(self, name):
      return (name in self._properties["extensions"])

   def extend(self, name):
      if self._properties["extensions"].get(name, False):
         return

      self._extend(name)

      self._properties["extensions"][name] = True

   def ordered_keys(self):
      return self._order

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
      if not isinstance(args, (dict, das.types.Struct)):
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
      if self._original_order:
         s += "%s__order__=%s" % (sep, repr(self._original_order))
      if self._properties["extensions"]:
         s += "%s__extends__=%s" % (sep, repr(self._properties["extensions"].keys()))
      if self.description:
         s += "%s__description__=%s" % (sep, repr(self.description))
      return s + ")"

   def _update_internals(self):
      keys = [k for k, _ in self.items() if not k in self._aliases]
      if self._original_order:
         self._order = filter(lambda x: x in keys, self._original_order)
         for n in keys:
            if not n in self._original_order:
               self._order.append(n)
      else:
         self._order = sorted(keys)

      self.default_validated = False
      self.default = None

   def __setitem__(self, k, v):
      super(Struct, self).__setitem__(k, v)
      self._update_internals()

   def __delitem__(self, k):
      super(Struct, self).__delitem__(k)
      self._update_internals()

   def update(self, *args, **kwargs):
      super(Struct, self).update(*args, **kwargs)
      self._update_internals()

   def pop(self, k, *args):
      rv = super(Struct, self).pop(k, *args)
      self._update_internals()
      return rv

   def popitem(self):
      rv = super(Struct, self).popitem(self)
      self._update_internals()
      return rv

   def clear(self):
      super(Struct, self).clear()
      self._update_internals()

   def copy(self):
      # self.load_extensions()
      kwargs = {}
      for k, v in self.iteritems():
         kwargs[k] = v.copy()
      return Struct(__description__=self.description, __editable__=self.editable,
                    __hidden__=self.hidden, __order__=self._original_order,
                    __properties__=self.get_properties(),
                    **kwargs)


class StaticDict(Struct):
   def __init__(self, __description__=None, __editable__=True, __hidden__=False, __order__=None, __properties__=None, **kwargs):
      super(StaticDict, self).__init__(__description__=__description__, __editable__=__editable__, __hidden__=__hidden__, __order__=__order__, __properties__=__properties__, **kwargs)
      if das.__verbose__:
         das.print_once("[das] Warning: Schema type 'StaticDict' is deprecated, use 'Struct' instead")


class Dict(TypeValidator):
   def __init__(self, ktype, vtype, __default__=None, __description__=None, __editable__=True, __hidden__=False, __properties__=None, **kwargs):
      for name in ("default", "description", "editable", "hidden"):
         if name in kwargs:
            if das.__verbose__:
               das.print_once("[das] '%s' treated as a possible key name for Dict type overrides. Use '__%s__' to set schema type's attribute" % (name, name))
      super(Dict, self).__init__(default=({} if __default__ is None else __default__), description=__description__, editable=__editable__, hidden=__hidden__, __properties__=__properties__)
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
            except ValidationError as e:
               raise ValidationError("Invalid key value '%s': %s" % (k, e))
            try:
               sk = str(ak)
               rv[ak] = self.vtypeOverrides.get(sk, self.vtype).validate(value[k])
            except ValidationError as e:
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

   def is_type_compatible(self, st, key=None, index=None):
      if key is not None:
         return self.vtypeOverrides.get(str(key), self.vtype).is_type_compatible(st)
      else:
         if not super(Dict, self).is_type_compatible(st, key=key, index=index):
            return False
         _st = st.real_type()
         if not self.ktype.is_type_compatible(_st.ktype):
            return False
         if not self.vtype.is_type_compatible(_st.vtype):
            return False
         for k, v in self.vtypeOverrides.iteritems():
            if not v.is_type_compatible(_st.vtypeOverrides.get(k, _st.vtype)):
               return False
         for k, v in _st.vtypeOverrides.iteritems():
            if k in self.vtypeOverrides:
               continue
            elif not self.vtype.is_type_compatible(v):
               return False
         return True

   def make(self, *args, **kwargs):
      return self.validate(kwargs)

   def conform(self, args, fill=False):
      if not isinstance(args, (dict, das.types.Struct)):
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
                  __default__=self.default, __description__=self.description,
                  __editable__=self.editable, __hidden__=self.hidden,
                  __properties__=self.get_properties(), **kwargs)


class DynamicDict(Dict):
   def __init__(self, ktype, vtype, __default__=None, __description__=None, __editable__=True, __hidden__=False, __properties__=None, **kwargs):
      super(DynamicDict, self).__init__(ktype, vtype, __default__=__default__, __description__=__description__, __editable__=__editable__, __hidden__=__hidden__, __properties__=__properties__, **kwargs)
      if das.__verbose__:
         das.print_once("[das] Warning: Schema type 'DynamicDict' is deprecated, use 'Dict' instead")


class Class(TypeValidator):
   def __init__(self, klass, default=None, description=None, editable=True, hidden=False, __properties__=None):
      if not isinstance(klass, (str, unicode)):
         self.klass = self._validate_class(klass)
      else:
         self.klass = self._class(klass)
      super(Class, self).__init__(default=(self.klass() if default is None else default), description=description, editable=editable, hidden=hidden, __properties__=__properties__)

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
            except Exception as e:
               raise ValidationError("Cannot instanciate class '%s' from string %s (%s)" % (self.klass.__name__, repr(value), e))
         elif hasattr(self.klass, "any_to_value"):
            try:
               newval = self.klass()
               newval.any_to_value(value)
               return newval
            except Exception as e:
               raise ValidationError("Cannot instanciate class '%s' from value %s (%s)" % (self.klass.__name__, repr(value), e))
         else:
            raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(value).__name__))
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   # No _decode?

   def is_type_compatible(self, st, key=None, index=None):
      if not super(Class, self).is_type_compatible(st, key=key, index=index):
         return False
      else:
         return issubclass(st.real_type().klass, self.klass)

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
      return Class(self.klass, default=self.default, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Or(TypeValidator):
   def __init__(self, *types, **kwargs):
      super(Or, self).__init__(default=kwargs.get("default", None), description=kwargs.get("description", None), editable=kwargs.get("editable", True), hidden=kwargs.get("hidden", False), __properties__=kwargs.get("__properties__", None))
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
            except ValidationError as e:
               continue
         Struct.CompatibilityMode = True
         if rv is not None:
            return rv
      emsgs = []
      for typ in self.types:
         try:
            return typ._validate_self(value)
         except ValidationError as e:
            emsgs.append(str(e))
            continue
      emsg = "Value of type %s doesn't match any of the allowed types" % type(value).__name__
      emsg += "".join(["\n  Type %d error: %s" % (x, emsgs[x]) for x in xrange(len(emsgs))])
      raise ValidationError(emsg)

   def _validate(self, value, key=None, index=None):
      if Struct.CompatibilityMode:
         rv = None
         Struct.CompatibilityMode = False
         for typ in self.types:
            try:
               rv = typ.validate(value, key=key, index=index)
               break
            except ValidationError as e:
               continue
         Struct.CompatibilityMode = True
         if rv is not None:
            return rv
      emsgs = []
      for typ in self.types:
         try:
            return typ.validate(value, key=key, index=index)
         except ValidationError as e:
            emsgs.append(str(e))
            continue
      emsg = "Value of type %s doesn't match any of the allowed types" % type(value).__name__
      emsg += "".join(["\n  Type %d error: %s" % (x, emsgs[x]) for x in xrange(len(emsgs))])
      raise ValidationError(emsg)

   def is_type_compatible(self, st, key=None, index=None):
      _st = st.real_type()
      if _st is None:
         return False
      else:
         if isinstance(_st, Or):
            for typ in _st.types:
               if not self.is_type_compatible(typ):
                  return False
            return True
         else:
            for typ in self.types:
               if typ.is_type_compatible(_st):
                  return True
            return False

   def value_to_string(self, v):
      for typ in self.types:
         try:
            return typ.value_to_string(v)
         except:
            continue
      return None

   def string_to_value(self, v):
      for typ in self.types:
         try:
            return typ.string_to_value(v)
         except:
            continue
      return None

   def _decode(self, encoding):
      super(Or, self)._decode(encoding)
      self.types = tuple(map(lambda x: das.decode(x, encoding), self.types))
      return self

   def make_default(self):
      if not self.default_validated and self.default is None:
         self.default = self.types[0].make_default()
      return super(Or, self).make_default()

   def make(self, *args, **kwargs):
      emsgs = []
      for typ in self.types:
         try:
            return typ.make(*args, **kwargs)
         except ValidationError as e:
            emsgs.append(str(e))

      emsg = "Cannot make any of the allowed types from arguments (args=%s, kwargs=%s)" % (repr(args), repr(kwargs))
      emsg += "".join(["\n  Type %d error: %s" % (x, emsgs[x]) for x in xrange(len(emsgs))])
      raise ValidationError(emsg)

   def conform(self, args, fill=False):
      emsgs = []
      for typ in self.types:
         try:
            return typ.conform(args, fill=fill)
         except ValidationError as e:
            emsgs.append(str(e))

      emsg = "Cannot conform to any of the allowed types (args=%s, fill=%s)" % (repr(args), repr(fill))
      emsg += "".join(["\n  Type %d error: %s" % (x, emsgs[x]) for x in xrange(len(emsgs))])
      raise ValidationError(emsg)

   def partial_make(self, args):
      emsgs = []
      for typ in self.types:
         try:
            return typ.partial_make(args)
         except Exception as e:
            emsgs.append(str(e))

      emsg = "Value of type %s doesn't match any of the allowed types" % type(args).__name__
      emsg += "".join(["\n  Type %d error: %s" % (x, emsgs[x]) for x in xrange(len(emsgs))])
      raise ValidationError(emsg)

   def __repr__(self):
      s = "Or(%s" % ", ".join(map(str, self.types))
      if self.default is not None:
         s += ", default=%s" % repr(self.default)
      if self.description:
         s += ", description=%s" % repr(self.description)
      return s + ")"

   def copy(self):
      types = [t.copy() for t in self.types]
      kwargs = {"default": self.default,
                "description": self.description,
                "editable": self.editable,
                "hidden": self.hidden,
                "__properties__": self.get_properties()}
      return Or(*types, **kwargs)


class Optional(TypeValidator):
   def __init__(self, type, description=None, editable=True, hidden=False, __properties__=None):
      super(Optional, self).__init__(description=description, editable=editable, hidden=hidden, __properties__=__properties__)
      self.type = type

   def _validate_self(self, value):
      return self.type._validate_self(value)

   def _validate(self, value, key=None, index=None):
      return self.type.validate(value, key=key, index=index)

   def _decode(self, encoding):
      super(Optional, self)._decode(encoding)
      self.type = das.decode(self.type, encoding)
      return self

   def real_type(self, parent=None):
      return self.type.real_type(parent=parent)

   def is_type_compatible(self, st, key=None, index=None):
      return self.type.is_type_compatible(st, key=key, index=index)

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
      return Optional(self.type.copy(), description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Deprecated(Optional):
   def __init__(self, type, message="", description=None, editable=True, hidden=False, __properties__=None):
      super(Deprecated, self).__init__(type, description=description, editable=editable, hidden=hidden, __properties__=__properties__)
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

   # Do not override is_type_compatible, already re-defined in Optional

   def make_default(self):
      return None

   def __repr__(self):
      return "Deprecated(type=%s)" % self.type

   def copy(self):
      return Deprecated(self.type.copy(), message=self.message, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Empty(TypeValidator):
   def __init__(self, description=None, editable=True, hidden=False, __properties__=None):
      super(Empty, self).__init__(description=description, editable=editable, hidden=hidden, __properties__=__properties__)

   def _validate_self(self, value):
      if value is not None:
         raise ValidationError("Expected None, got %s" % type(value).__name__)
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   # no need to override is_type_compatible, Empty only matches another Empty

   def make_default(self):
      return None

   def value_to_string(self, v):
      self.validate(v)
      return ""

   def string_to_value(self, v):
      if v:
         raise ValidationError("The value is not empty")
      return self.validate(None)

   def __repr__(self):
      return "Empty()"

   def copy(self):
      return Empty(description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class Alias(TypeValidator):
   @staticmethod
   def Check(t):
      return (isinstance(t, Alias) or (isinstance(t, Deprecated) and isinstance(t.type, Alias)))

   @staticmethod
   def Name(t):
      if isinstance(t, Alias):
         return t.name
      # Can't this be optional too?
      #elif isinstance(t, Deprecated) and isinstance(t.type, Alias):
      elif isinstance(t, Optional) and isinstance(t.type, Alias):
         return t.type.name
      else:
         return None

   def __init__(self, name, description=None, editable=True, hidden=False, __properties__=None):
      super(Alias, self).__init__(description=description, editable=editable, hidden=hidden, __properties__=__properties__)
      self.name = name

   def _validate_self(self, value):
      return value

   def _validate(self, value, key=None, index=None):
      return self._validate_self(value)

   def real_type(self, parent=None):
      if parent is not None:
         return parent[self.name].real_type(parent=parent)
      else:
         return super(Alias, self).real_type(parent=parent)

   def is_type_compatible(self, st, key=None, index=None):
      _st = st.real_type()
      if not isinstance(_st, Alias):
         return False
      else:
         return (self.name == _st.name)

   def make_default(self):
      return None

   def __repr__(self):
      return "Alias(%s)" % repr(self.name)

   def copy(self):
      return Alias(self.name, description=self.description, editable=self.editable, hidden=self.hidden, __properties__=self.get_properties())


class SchemaType(TypeValidator):
   def __init__(self, name, default=None, description=None, editable=True, hidden=False, __properties__=None):
      super(SchemaType, self).__init__(default=default, description=description, editable=editable, hidden=hidden, __properties__=__properties__)
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

   def real_type(self, parent=None):
      return das.get_schema_type(self.name).real_type(parent=parent)

   def is_type_compatible(self, st, key=None, index=None):
      return das.get_schema_type(self.name).is_type_compatible(st, key=key, index=index)

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
      return SchemaType(self.name, default=self.default, description=self.description, editable=self.editable, __properties__=self.get_properties())
