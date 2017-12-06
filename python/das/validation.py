import os
import re
import imp
import glob
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
           "SchemaType",
           "load_schemas",
           "list_schemas",
           "get_schema",
           "get_schema_path",
           "get_schema_module",
           "validate"]

# ---

# Value of DAS_SCHEMA_PATH when load_schemas was last called
gSchemaPath = ""
# Map schema file directory to list of loaded schema files
gDirSchemas = {}
# Map schema file path to list of defined schemas
gSchemaNames = {}
# Map schema file path to its associated python module (if any)
gSchemaModules = {}
# Map schema name to its validator instance and schema file path
gSchemas = {}
# Current schema scope
gCurrentSchema = ""

# ---

class UnknownSchemaError(Exception):
   def __init__(self, name):
      super(UnknownSchemaError, self).__init__("'%s' is not a known schema" % name)


class ValidationError(Exception):
   def __init__(self, msg):
      super(ValidationError, self).__init__(msg)


class TypeValidator(object):
   def __init__(self):
      super(TypeValidator, self).__init__()

   def _validate(self, data):
      raise ValidationError("'_validate' method is not implemented")

   def __str__(self):
      return self.__repr__()


class Boolean(TypeValidator):
   def __init__(self, default=False):
      super(Boolean, self).__init__()
      self.default = bool(default)

   def _validate(self, data):
      if not isinstance(data, bool):
         raise ValidationError("Expected a boolean value, got %s" % type(data))

   def __repr__(self):
      s = "Boolean(";
      if self.default is True:
         s += "default=%s" % self.default
      return s + ")"


class Integer(TypeValidator):
   def __init__(self, default=0, min=None, max=None):
      super(Integer, self).__init__()
      self.default = long(default)
      self.min = min
      self.max = max

   def _validate(self, data):
      if not type(data) in (int, long):
         raise ValidationError("Expected an integer value, got %s" % type(data))
      if self.min is not None and data < self.min:
         raise ValidationError("Integer value out of range, %d < %d" % (data, self.min))
      if self.max is not None and data > self.max:
         raise ValidationError("Integer value out of range, %d > %d" % (data, self.max))

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
      return s + ")"


class Real(TypeValidator):
   def __init__(self, default=0.0, min=None, max=None):
      super(Real, self).__init__()
      self.default = float(default)
      self.min = min
      self.max = max

   def _validate(self, data):
      if not type(data) in (int, long, float):
         raise ValidationError("Expected a real value, got %s" % type(data))
      if self.min is not None and data < self.min:
         raise ValidationError("Real value out of range, %d < %d" % (data, self.min))
      if self.max is not None and data > self.max:
         raise ValidationError("Real value out of range, %d < %d" % (data, self.min))

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
      return s + ")"


class String(TypeValidator):
   def __init__(self, default="", choices=None, matches=None):
      super(String, self).__init__()
      self.default = str(default)
      self.choices = choices
      self.matches = None
      if choices is None and matches is not None:
         if type(matches) in (str, unicode):
            self.matches = re.compile(matches)
         else:
            self.matches = matches

   def _validate(self, data):
      if not type(data) in (str, unicode):
         raise ValidationError("Expected a string value, got %s" % type(data))
      if self.choices is not None and not data in self.choices:
         raise ValidationError("String value must be on of %s, got '%s'" % (self.choices, data))
      if self.matches is not None and not self.matches.match(data):
         raise ValidationError("String value '%s' doesn't match pattern '%s'" % (data, self.matches.pattern))

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
   def __init__(self, type, default=[], size=None, min_size=None, max_size=None):
      super(Sequence, self).__init__()
      self.default = list(default)
      self.size = size
      self.min_size = min_size
      self.max_size = max_size
      self.type = type

   def _validate(self, data):
      if not type(data) in (tuple, list, set):
         raise ValidationError("Expected a sequence value, got %s" % type(data))
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
            self.type._validate(item)
         except ValidationError, e:
            raise ValidationError("Invalid sequence element: %s" % e)

   def __repr__(self):
      s = "Sequence(type=%s" % self.type
      sep = ", "
      if self.default is not None and len(self.default) > 0:
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
      super(Tuple, self).__init__()
      self.types = args
      self.default = kwargs.get("default", None)

   def _validate(self, data):
      if type(data) not in (list, tuple):
         raise ValidationError("Expected a tuple value, got %s" % type(data))
      n = len(data)
      if n != len(self.types):
         raise ValidationError("Expected a tuple of size %d, got %d", (len(self.types), n))
      for i in xrange(n):
         try:
            self.types[i]._validate(data[i])
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


class StaticDict(das.struct.Das, TypeValidator):
   def __init__(self, **kwargs):
      super(StaticDict, self).__init__(**kwargs)

   def _validate(self, data):
      if not type(data) in (dict, das.struct.Das):
         raise ValidationError("Expected a dict value, got %s" % type(data))
      for k, v in self._iteritems():
         if not k in data:
            if not isinstance(v, Optional):
               raise ValidationError("Missing key '%s'" % k)
         else:
            try:
               v._validate(data[k])
            except ValidationError, e:
               raise ValidationError("Invalid value for key '%s': %s" % (k, e))

   # redefine __str__ as the one from Das will be used
   def __str__(self):
      return self.__repr__()

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
      super(DynamicDict, self).__init__()
      self.ktype = ktype
      self.vtype = vtype
      self.default = default
      self.vtypeOverrides = {}
      for k, v in kwargs.iteritems():
         self.vtypeOverrides[k] = v

   def _validate(self, data):
      if not type(data) in (dict, das.struct.Das):
         raise ValidationError("Expected a dict value, got %s" % type(data))
      for k in data:
         try:
            self.ktype._validate(k)
         except ValidationError, e:
            raise ValidationError("Invalid key value '%s': %s" % (k, e))
         try:
            vtype = self.vtypeOverrides.get(k, self.vtype)
            vtype._validate(data[k])
         except ValidationError, e:
            raise ValidationError("Invalid value for key '%s': %s" % (k, e))

   def __repr__(self):
      s = "DynamicDict(ktype=%s, vtype=%s" % (self.ktype, self.vtype)
      if self.default is not None:
         s += ", default=%s" % self.default
      for k, v in self.vtypeOverrides:
         s += ", %s=%s" % (k, v)
      return s + ")"


class Class(TypeValidator):
   def __init__(self, klass):
      super(Class, self).__init__()
      self.klass = klass

   def _validate(self, data):
      if not isinstance(data, self.klass):
         raise ValidationError("Expected a %s value, got %s" % (self.klass.__name__, type(data)))

   def __repr__(self):
      return "Class(%s)" % self.klass.__name__


class Or(TypeValidator):
   def __init__(self, type1, type2):
      super(Or, self).__init__()
      self.type1 = type1
      self.type2 = type2

   def _validate(self, data):
      try:
         self.type1._validate(data)
      except ValidationError, e1:
         self.type2._validate(data)

   def __repr__(self):
      return "Or(%s, %s)" % (self.type1, self.type2)


class Optional(TypeValidator):
   def __init__(self, type):
      super(Optional, self).__init__()
      self.type = type

   def _validate(self, data):
      self.type._validate(data)

   def __repr__(self):
      return "Optional(type=%s)" % self.type


class SchemaType(TypeValidator):
   def __init__(self, name):
      super(SchemaType, self).__init__()
      if not "." in name:
         self.name = gCurrentSchema + "." + name
      else:
         self.name = name

   def _validate(self, data):
      validate(data, self.name)

   def __repr__(self):
      return "SchemaType('%s')" % self.name


# ---

def load_schemas(paths=None):
   global gSchemaPath, gDirSchemas, gSchemaNames, gSchemaModules, gSchemas, gCurrentSchema

   schemaPath = (os.pathsep.join(paths) if paths is not None else os.environ.get("DAS_SCHEMA_PATH", ""))
   if schemaPath == gSchemaPath:
      return

   oldDirs = set(filter(lambda x: os.path.isdir, gSchemaPath.split(os.pathsep)))
   newDirs = set(filter(lambda x: os.path.isdir, schemaPath.split(os.pathsep)))

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
                  "SchemaType": SchemaType}

   # Remove schemas not in DAS_SCHEMA_PATH anymore
   for d in oldDirs:
      if d in newDirs or not d in gDirSchemas:
         continue

      for sf in gDirSchemas[d]:
         if sf in gSchemaNames:
            for sn in gSchemaNames[sf]:
               sch, _ = gSchemas.get(sn, (None, None))
               if sch is not None:
                  del(gSchemas[sn])
            del(gSchemaNames[sf])

         if sf in gSchemaModules:
            mod = gSchemaModules[sf]
            if mod is not None:
               delattr(das.schema, mod.__name__.split(".")[-1])
            del(gSchemaModules[sf])

      del(gDirSchemas[d])

   # Add schemas for new items in DAS_SCHEMA_PATH
   for d in newDirs:
      if d in oldDirs:
         continue

      dirSchemas = glob.glob(d+"/*.schema")

      for sf in dirSchemas:
         sn = os.path.splitext(os.path.basename(sf))[0]
         pp = os.path.splitext(sf)[0] + ".py"

         mod = None
         if os.path.isfile(pp):
            try:
               mod = imp.load_source("das.schema.%s" % sn, pp)
               setattr(das.schema, sn, mod)
            except Exception, e:
               print("[das] Failed to load schema module '%s' (%s)" % (pp, e))
         gSchemaModules[sf] = mod

         try:
            el = eval_locals.copy()
            if mod is not None and hasattr(mod, "__all__"):
               for an in mod.__all__:
                  el[an] = getattr(mod, an)

            names = []
            with open(sf, "r") as f:
               gCurrentSchema = sn
               rv = eval(f.read(), globals(), el)
               gCurrentSchema = ""
               for k, v in rv.iteritems():
                  k = "%s.%s" % (sn, k)
                  names.append(k)
                  if k in gSchemas:
                     print("[Das] Schema '%s' is already defined. Ignore definition from '%s'." % (k, sf))
                  else:
                     gSchemas[k] = (v, sf)
            gSchemaNames[sf] = names

         except Exception, e:
            print("[das] Failed to read schemas from '%s' (%s)" % (sf, e))
            raise e

      gDirSchemas[d] = dirSchemas

   gSchemaPath = schemaPath


def list_schemas():
   load_schemas()
   return gSchemas.keys()


def get_schema(schema):
   load_schemas()
   sch, _ = gSchemas.get(schema, (None, None))
   if sch is None:
      raise UnknownSchemaError(schema)
   return sch


def get_schema_path(schema):
   load_schemas()
   sch, sf = gSchemas.get(schema, (None, None))
   if sch is None:
      raise UnknownSchemaError(schema)
   return sf


def get_schema_module(schema):
   load_schemas()
   sch, sf = gSchemas.get(schema, (None, None))
   if sch is None:
      raise UnknownSchemaError(schema)
   return gSchemaModules.get(sf, None)


def validate(d, schema):
   s = get_schema(schema)
   s._validate(d)
