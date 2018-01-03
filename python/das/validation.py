import os
import re
import sys
import imp
import glob
import copy
import das

__all__ = ["UnknownSchemaError",
           "ValidationError",
           "TypeValidator",
           "Boolean",
           "Integer",
           "Real",
           "String",
           "Sequence",
           "Tuple",
           "StaticDict",
           "DynamicDict",
           "Class",
           "Or",
           "Optional",
           "Empty",
           "SchemaType",
           "load_schemas",
           "list_schemas",
           "get_schema",
           "has_schema",
           "list_schema_types",
           "has_schema_type",
           "get_schema_type",
           "get_schema_type_name",
           "get_schema_path",
           "get_schema_module",
           "validate",
           "make_default"]

# ---

class UnknownSchemaError(Exception):
   def __init__(self, name):
      super(UnknownSchemaError, self).__init__("'%s' is not a known schema%s" % (name, " type" if "." in name else ""))


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   def __init__(self, **kwargs):
      super(TypeValidator, self).__init__()
      if "default" in kwargs:
         default = kwargs["default"]
         self.default = (self.validate_default(default) if default is not None else None)

   def validate_default(self, value):
      return value

   def validate(self, data):
      raise ValidationError("'validate' method is not implemented")

   def make_default(self):
      return None

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   def __init__(self, default=None):
      super(Boolean, self).__init__(default=default)

   def validate_default(self, value):
      return bool(value)

   def validate(self, data):
      if not isinstance(data, bool):
         raise ValidationError("Expected a boolean value, got %s" % type(data).__name__)

   def make_default(self):
      return (False if self.default is None else self.default)

   def __repr__(self):
      s = "Boolean(";
      if self.default is not None:
         s += "default=%s" % self.default
      return s + ")"


class Integer(TypeValidator):
   def __init__(self, default=None, min=None, max=None):
      super(Integer, self).__init__(default=default)
      self.min = min
      self.max = max

   def validate_default(self, value):
      return long(value)

   def validate(self, data):
      if not isinstance(data, (int, long)):
         raise ValidationError("Expected an integer value, got %s" % type(data).__name__)
      if self.min is not None and data < self.min:
         raise ValidationError("Integer value out of range, %d < %d" % (data, self.min))
      if self.max is not None and data > self.max:
         raise ValidationError("Integer value out of range, %d > %d" % (data, self.max))

   def make_default(self):
      return (0 if self.default is None else self.default)

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
      super(Real, self).__init__(default=default)
      self.min = min
      self.max = max

   def validate_default(self, value):
      return float(value)

   def validate(self, data):
      if not isinstance(data, (int, long, float)):
         raise ValidationError("Expected a real value, got %s" % type(data).__name__)
      if self.min is not None and data < self.min:
         raise ValidationError("Real value out of range, %d < %d" % (data, self.min))
      if self.max is not None and data > self.max:
         raise ValidationError("Real value out of range, %d < %d" % (data, self.min))

   def make_default(self):
      return (0.0 if self.default is None else self.default)

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
      super(String, self).__init__(default=default)
      self.choices = choices
      self.matches = None
      if choices is None and matches is not None:
         if type(matches) in (str, unicode):
            self.matches = re.compile(matches)
         else:
            self.matches = matches

   def validate_default(self, value):
      return str(value)

   def validate(self, data):
      if not isinstance(data, (str, unicode)):
         raise ValidationError("Expected a string value, got %s" % type(data).__name__)
      if self.choices is not None and not data in self.choices:
         raise ValidationError("String value must be on of %s, got '%s'" % (self.choices, data))
      if self.matches is not None and not self.matches.match(data):
         raise ValidationError("String value '%s' doesn't match pattern '%s'" % (data, self.matches.pattern))

   def make_default(self):
      return ("" if self.default is None else self.default)

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
      super(Sequence, self).__init__(default=default)
      self.size = size
      self.min_size = min_size
      self.max_size = max_size
      self.type = type

   def validate_default(self, value):
      return list(value)

   def validate(self, data):
      if not isinstance(data, (tuple, list, set)):
         raise ValidationError("Expected a sequence value, got %s" % type(data).__name__)
      n = len(data)
      if self.size is not None:
         if n != self.size:
            raise ValidationError("Expected a sequence of fixed size %d, got %d" % (self.size, n))
      else:
         if self.min_size is not None and n < self.min_size:
            raise ValidationError("Expected a sequence of minimum size %d, got %d" % (self.min_size, n))
         if self.max_size is not None and n > self.max_size:
            raise ValidationError("Expected a sequence of maximum size %d, got %d" % (self.max_size, n))
      for item in data:
         try:
            self.type.validate(item)
         except ValidationError, e:
            raise ValidationError("Invalid sequence element: %s" % e)

   def make_default(self):
      return ([] if self.default is None else (self.default[:] if self.size is None else tuple(self.default)))

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

   def validate_default(self, value):
      if not isinstance(value, tuple):
         raise Exception("Tuple default value must be a tuple, got %s" % type(value).__name__)
      return value

   def validate(self, data):
      if not isinstance(data, (list, tuple)):
         raise ValidationError("Expected a tuple value, got %s" % type(data).__name__)
      n = len(data)
      if n != len(self.types):
         raise ValidationError("Expected a tuple of size %d, got %d", (len(self.types), n))
      for i in xrange(n):
         try:
            self.types[i].validate(data[i])
         except ValidationError, e:
            raise ValidationError("Invalid tuple element: %s" % e)

   def make_default(self):
      if self.default is None:
         return tuple([x.make_default() for x in self.types])
      else:
         return tuple(self.default)

   def __repr__(self):
      s = "Tuple("
      sep = ""
      for t in self.types:
         s += "%s%s" % (sep, t)
         sep = ", "
      if self.default is not None:
         s += "%sdefault=%s" % (sep, self.default)
      return s + ")"


class StaticDict(dict, TypeValidator):
   def __init__(self, **kwargs):
      if "default" in kwargs:
         del(kwargs["default"])
      super(StaticDict, self).__init__(**kwargs)

   def validate(self, data):
      if not isinstance(data, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(data).__name__)
      for k, v in self.iteritems():
         if not k in data:
            if not isinstance(v, Optional):
               raise ValidationError("Missing key '%s'" % k)
         else:
            try:
               v.validate(data[k])
            except ValidationError, e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))

   def make_default(self):
      dct = {}
      for k, v in self.iteritems():
         dv = v.make_default()
         if isinstance(v, Optional) and not dv:
            continue
         dct[k] = dv
      rv = das.types.Struct(dct)
      rv._set_schema_type(self)
      return rv

   def __repr__(self):
      s = "StaticDict("
      sep = ""
      keys = [k for k in self]
      keys.sort()
      for k in keys:
         v = self[k]
         s += "%s%s=%s" % (sep, k, v)
         sep = ", "
      return s + ")"


class DynamicDict(TypeValidator):
   def __init__(self, ktype, vtype, default=None, **kwargs):
      super(DynamicDict, self).__init__(default=default)
      self.ktype = ktype
      self.vtype = vtype
      self.default = default
      self.vtypeOverrides = {}
      for k, v in kwargs.iteritems():
         self.vtypeOverrides[k] = v

   def validate_default(self, value):
      if not isinstance(value, dict):
         raise Exception("DynamicDict default value must be a dict, got %s" % type(value).__name__)
      return value

   def validate(self, data):
      if not isinstance(data, (dict, das.types.Struct)):
         raise ValidationError("Expected a dict value, got %s" % type(data).__name__)
      for k in data:
         try:
            self.ktype.validate(k)
         except ValidationError, e:
            raise ValidationError("Invalid key value '%s': %s" % (k, e))
         try:
            vtype = self.vtypeOverrides.get(k, self.vtype)
            vtype.validate(data[k])
         except ValidationError, e:
            raise ValidationError("Invalid value for key '%s': %s" % (k, e))

   def make_default(self):
      if self.default is None:
         rv = das.types.Struct({})
      else:
         rv = das.types.Struct(self.default)
      rv._set_schema_type(self)
      return rv

   def __repr__(self):
      s = "DynamicDict(ktype=%s, vtype=%s" % (self.ktype, self.vtype)
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

   def validate_default(self, value):
      if not isinstance(value, self.klass):
         raise Exception("Class default value must be a %s, got %s" % (self.klass.__name__, type(value).__name__))

   def validate(self, data):
      if not isinstance(data, self.klass):
         raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(data).__name__))

   def make_default(self):
      return (self.klass() if self.default is None else self.default.copy())

   def __repr__(self):
      return "Class(%s)" % self.klass.__name__


class Or(TypeValidator):
   def __init__(self, type1, type2, default=None):
      self.type1 = type1
      self.type2 = type2
      super(Or, self).__init__(default=default)

   def validate_default(self, value):
      try:
         self.type1.validate_default(value)
      except:
         self.type2.validate_default(value)

   def validate(self, data):
      try:
         self.type1.validate(data)
      except ValidationError, e1:
         self.type2.validate(data)

   def make_default(self):
      return self.type1.make_default()

   def __repr__(self):
      s = "Or(%s, %s" % (self.type1, self.type2)
      if self.default is not None:
         s += ", default=%s" % self.default
      return s + ")"


class Optional(TypeValidator):
   def __init__(self, type):
      super(Optional, self).__init__()
      self.type = type

   def validate(self, data):
      self.type.validate(data)

   def make_default(self):
      return self.type.make_default()

   def __repr__(self):
      return "Optional(type=%s)" % self.type


class Empty(TypeValidator):
   def __init__(self):
      super(Empty, self).__init__()

   def validate_default(self, value):
      if value is not None:
         raise Exception("Empty only accepts None as default value, got %s" % type(value).__name__)

   def validate(self, data):
      if data is not None:
         raise ValidationError("Expected None, got %s" % type(data).__name__)

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

   def validate_default(self, value):
      # Can't really call in the referenced type to validate default can we?
      # get_schema_type may not return a valid value just yet
      return value

   def validate(self, data):
      st = SchemaTypesRegistry.instance.get_schema_type(self.name)
      st.validate(data)

   def make_default(self):
      st = SchemaTypesRegistry.instance.get_schema_type(self.name)
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


# ---


class Schema(object):
   def __init__(self, location, path, dont_load=False):
      super(Schema, self).__init__()
      name = os.path.splitext(os.path.basename(path))[0]
      if "." in name:
         raise Exception("Schema file base name must not contain '.'")
      self.name = name
      self.path = path
      self.location = location
      self.module = None
      self.types = {}
      if not dont_load:
         self.load()

   def load(self):
      if not self.path:
         return

      self.unload()

      pmp = os.path.splitext(self.path)[0] + ".py"
      if os.path.isfile(pmp):
         try:
            self.module = imp.load_source("das.schema.%s" % self.name, pmp)
            setattr(das.schema, self.name, self.module)
         except Exception, e:
            print("[das] Failed to load schema module '%s' (%s)" % (pmp, e))

      eval_locals = {"Boolean": Boolean,
                     "Integer": Integer,
                     "Real": Real,
                     "String": String,
                     "Sequence": Sequence,
                     "Tuple": Tuple,
                     "StaticDict": StaticDict,
                     "DynamicDict": DynamicDict,
                     "Class": Class,
                     "Or": Or,
                     "Optional": Optional,
                     "Empty": Empty,
                     "SchemaType": SchemaType}
      if self.module is not None and hasattr(self.module, "__all__"):
         for an in self.module.__all__:
            eval_locals[an] = getattr(self.module, an)

      names = []
      with open(self.path, "r") as f:
         SchemaType.CurrentSchema = self.name
         rv = eval(f.read(), globals(), eval_locals)
         SchemaType.CurrentSchema = ""
         for typename, validator in rv.iteritems():
            k = "%s.%s" % (self.name, typename)
            if SchemaTypesRegistry.instance.has_schema_type(k):
               raise Exception("[das] Schema type '%s' already registered in another schema")
            else:
               self.types[k] = validator

   def unload(self):
      if self.module is not None:
         delattr(das.schema, self.module.__name__.split(".")[-1])
         self.module = None
      self.types = {}

   def list_types(self, sort=True):
      rv = self.types.keys()
      if sort:
         rv.sort()
      return rv

   def has_type(self, name):
      return (name in self.types)

   def get_type(self, name):
      return self.types.get(name, None)

   def get_type_name(self, typ):
      for k, v in self.types.iteritems():
         if type(v) != type(typ):
            continue
         if v == typ:
            return k
      return ""


class SchemaLocation(object):
   def __init__(self, path=None, dont_load=False):
      super(SchemaLocation, self).__init__()
      if path:
         self.path = os.path.abspath(path).replace("\\", "/")
         if sys.path == "win32":
            self.path = self.path.lower()
      else:
         self.path = None
      self.schemas = {}
      if not dont_load:
         self.load_schemas()

   def load_schemas(self):
      if not self.path:
         return

      self.unload_schemas()

      schema_files = glob.glob(self.path + "/*.schema")
      for schema_file in schema_files:
         # try:
            schema = Schema(self, schema_file, dont_load=True)
            if SchemaTypesRegistry.instance.has_schema(schema.name):
               raise Exception("[das] Schema '%s' already registered in another schema")
            else:
               schema.load()
               self.schemas[schema.name] = schema
         # except Exception, e:
         #    print("[das] Failed to read schemas from '%s' (%s)" % (schema_file, e))
         #    raise e

   def unload_schemas(self):
      for _, schema in self.schemas.iteritems():
         schema.unload()
      self.schemas = {}

   def list_schemas(self, sort=True):
      rv = self.schemas.keys()
      if sort:
         rv.sort()
      return rv

   def has_schema(self, name):
      return (name in self.schemas)

   def get_schema(self, name):
      return self.schemas.get(name, None)

   def list_schema_types(self, schema=None, sort=True):
      rv = set()
      for n, s in self.schemas.iteritems():
         if schema is not None and n != schema:
            continue
         rv = rv.union(s.list_types(sort=False))
      rv = list(rv)
      if sort:
         rv.sort()
      return rv

   def has_schema_type(self, name):
      for sname, schema in self.schemas.iteritems():
         if schema.has_type(name):
            return True
      return False

   def get_schema_type(self, name):
      for sname, schema in self.schemas.iteritems():
         if name.startswith(sname+"."):
            rv = schema.get_type(name)
            if rv is not None:
               return rv
      return None

   def get_schema_type_name(self, typ):
      for sname, schema in self.schemas.iteritems():
         rv = schema.get_type_name(typ)
         if rv:
            return rv
      return ""

   def __hash__(self):
      return hash(self.path)


class SchemaTypesRegistry(object):
   instance = None

   def __init__(self):
      super(SchemaTypesRegistry, self).__init__()
      if SchemaTypesRegistry.instance is not None:
         raise Exception("SchemaTypesRegistry must be globally unique")
      self.path = ""
      self.locations = set()
      SchemaTypesRegistry.instance = self

   def load_schemas(self, paths=None):
      path = (os.pathsep.join(paths) if paths is not None else os.environ.get("DAS_SCHEMA_PATH", ""))
      if path == self.path:
         return

      locations = set()
      for d in path.split(os.pathsep):
         if not os.path.isdir(d):
            continue
         location = SchemaLocation(d, dont_load=True)
         if not location in self.locations:
            locations.add(location)

      for location in self.locations:
         if not location in locations:
            location.unload_schemas()

      # Load schemas after removing the unncessary ones
      for location in locations:
         location.load_schemas()

      self.locations = locations
      self.path = path

   def list_schemas(self, sort=True):
      self.load_schemas()
      rv = set()
      for location in self.locations:
         rv = rv.union(location.list_schemas(sort=False))
      rv = list(rv)
      if sort:
         rv.sort()
      return rv

   def list_schema_types(self, schema=None, sort=True):
      self.load_schemas()
      rv = set()
      for location in self.locations:
         rv = rv.union(location.list_schema_types(schema=schema, sort=False))
      rv = list(rv)
      if sort:
         rv.sort()
      return rv

   def has_schema(self, name):
      for location in self.locations:
         if location.has_schema(name):
            return True
      return False

   def get_schema(self, name):
      self.load_schemas()
      for location in self.locations:
         rv = location.get_schema(name)
         if rv is not None:
            return rv
      raise UnknownSchemaError(name)

   def has_schema_type(self, name):
      for location in self.locations:
         if location.has_schema_type(name):
            return True
      return False

   def get_schema_type(self, name):
      self.load_schemas()
      for location in self.locations:
         rv = location.get_schema_type(name)
         if rv is not None:
            return rv
      raise UnknownSchemaError(name)

   def get_schema_type_name(self, typ):
      self.load_schemas()
      for location in self.locations:
         rv = location.get_schema_type_name(typ)
         if rv:
            return rv
      raise UnknownSchemaError(name)

   def get_schema_path(self, name):
      self.load_schemas()
      if "." in name:
         name = name.split(".")[0]
      return self.get_schema(name).path

   def get_schema_module(self, name):
      self.load_schemas()
      if "." in name:
         name = name.split(".")[0]
      return self.get_schema(name).module

   def make_default(self, name):
      st = self.get_schema_type(name)
      return st.make_default()


# Initialize registry
SchemaTypesRegistry()

# ---


def load_schemas(paths=None):
   SchemaTypesRegistry.instance.load_schemas(paths=paths)


def list_schemas():
   return SchemaTypesRegistry.instance.list_schemas()


def has_schema():
   return SchemaTypesRegistry.instance.has_schema()


def get_schema(name):
   return SchemaTypesRegistry.instance.get_schema(name)


def list_schema_types(schema=None):
   return SchemaTypesRegistry.instance.list_schema_types(schema)


def has_schema_type(name):
   return SchemaTypesRegistry.instance.has_schema_type(name)


def get_schema_type(name):
   return SchemaTypesRegistry.instance.get_schema_type(name)


def get_schema_type_name(typ):
   return SchemaTypesRegistry.instance.get_schema_type_name(typ)


def get_schema_path(name):
   return SchemaTypesRegistry.instance.get_schema_path(name)


def get_schema_module(name):
   return SchemaTypesRegistry.instance.get_schema_module(name)


def make_default(name):
   return SchemaTypesRegistry.instance.make_default(name)


def validate(d, schema):
   get_schema_type(schema).validate(d)
