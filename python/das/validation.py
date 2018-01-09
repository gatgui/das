import os
import re
import sys
import imp
import glob
import copy
import das


class UnknownSchemaError(Exception):
   def __init__(self, name):
      super(UnknownSchemaError, self).__init__("'%s' is not a known schema%s" % (name, " type" if "." in name else ""))


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

      eval_locals = {"Boolean": das.schematypes.Boolean,
                     "Integer": das.schematypes.Integer,
                     "Real": das.schematypes.Real,
                     "String": das.schematypes.String,
                     "Sequence": das.schematypes.Sequence,
                     "Tuple": das.schematypes.Tuple,
                     "StaticDict": das.schematypes.Struct, # Deprecated: -> use Struct instead
                     "DynamicDict": das.schematypes.Dict,  # Deprecated: -> use Dict instead
                     "Struct": das.schematypes.Struct,
                     "Dict": das.schematypes.Dict,
                     "Class": das.schematypes.Class,
                     "Or": das.schematypes.Or,
                     "Optional": das.schematypes.Optional,
                     "Empty": das.schematypes.Empty,
                     "SchemaType": das.schematypes.SchemaType}
      if self.module is not None and hasattr(self.module, "__all__"):
         for an in self.module.__all__:
            eval_locals[an] = getattr(self.module, an)

      names = []
      with open(self.path, "r") as f:
         das.schematypes.SchemaType.CurrentSchema = self.name
         rv = eval(f.read(), globals(), eval_locals)
         das.schematypes.SchemaType.CurrentSchema = ""
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
      self.properties = {}
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
      # Not all types are named!
      return ""

   def set_schema_type_property(self, name, pname, pvalue):
      props = self.properties.get(name, {})
      if pname == "function_set":
         if not issubclass(pvalue, das.FunctionSet):
            raise Exception("'function_set' property value must be a subclass of das.fsets.FunctionSet")
      props[pname] = pvalue
      self.properties[name] = props

   def get_schema_type_property(self, name, pname):
      return self.properties.get(name, {}).get(pname, None)

   def make_default(self, name):
      st = self.get_schema_type(name)
      fn = self.get_schema_type_property(name, "function_set")
      rv = st.make_default()
      if fn is not None and issubclass(fn, das.FunctionSet) and not isinstance(rv, das.FunctionSet):
         rv = fn(data=rv, validate=False)
      return rv

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


# Initialize registry
SchemaTypesRegistry()
