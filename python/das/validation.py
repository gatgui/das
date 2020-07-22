import os
import re
import sys
import imp
import glob
import copy
import das


class UnknownSchemaError(Exception):
   def __init__(self, name):
      super(UnknownSchemaError, self).__init__("%s is not a known schema or schema type" % repr(name))


class SchemaVersionError(das.VersionError):
   def __init__(self, name, current_version=None, required_version=None):
      super(SchemaVersionError, self).__init__("Schema %s" % repr(name), current_version, required_version)


class Schema(object):
   def __init__(self, location, path, dont_load=False):
      super(Schema, self).__init__()
      self.path = path
      self.location = location
      self.module = None
      self.types = {}
      self.master_types = None
      self.version = None
      self.name = das.read_meta(path).get("name", None)
      if not self.name:
         name = os.path.splitext(os.path.basename(path))[0]
         if "." in name:
            raise Exception("Schema file base name must not contain '.'")
         else:
            self.name = name
      if not dont_load:
         self.load()

   def load(self):
      if not self.path:
         return False

      self.unload()

      md, content = das._read_file(self.path)

      dmv = md.get("das_minimum_version", None)
      if dmv is not None:
         try:
            spl = map(int, dmv.split("."))
            wmaj, wmin = spl[0], spl[1]
         except:
            raise Exception("'das_minimum_version' must follow MAJOR.MINOR format")
         else:
            dmaj, dmin, _ = map(int, das.__version__.split("."))
            if wmaj != dmaj or wmin > dmin:
               raise das.VersionError("Library", current_version=das.__version__, required_version=dmv)

      pmp = os.path.splitext(self.path)[0] + ".py"
      if os.path.isfile(pmp):
         try:
            modname = os.path.splitext(os.path.basename(self.path))[0]
            mod = imp.load_source("das.schema.%s" % modname, pmp)
         except Exception, e:
            import traceback
            print("[das] Failed to load schema module '%s' (%s)" % (pmp, e))
            traceback.print_exc()
            return False
         else:
            self.module = mod
            setattr(das.schema, modname, self.module)

      eval_locals = {"Boolean": das.schematypes.Boolean,
                     "Integer": das.schematypes.Integer,
                     "Real": das.schematypes.Real,
                     "String": das.schematypes.String,
                     "Set": das.schematypes.Set,
                     "Sequence": das.schematypes.Sequence,
                     "Tuple": das.schematypes.Tuple,
                     "StaticDict": das.schematypes.StaticDict, # Deprecated
                     "DynamicDict": das.schematypes.DynamicDict,  # Deprecated
                     "Struct": das.schematypes.Struct,
                     "Dict": das.schematypes.Dict,
                     "Class": das.schematypes.Class,
                     "Or": das.schematypes.Or,
                     "Optional": das.schematypes.Optional,
                     "Empty": das.schematypes.Empty,
                     "Deprecated": das.schematypes.Deprecated,
                     "SchemaType": das.schematypes.SchemaType,
                     "Alias": das.schematypes.Alias}
      if self.module is not None and hasattr(self.module, "__all__"):
         for an in self.module.__all__:
            eval_locals[an] = getattr(self.module, an)

      if content:
         self.version = md.get("version", None)
         if self.version is None:
            if das.__verbose__:
               das.print_once("[das] Warning: Schema '%s' defined in %s is unversioned" % (self.name, self.path))

         das.schematypes.TypeValidator.CurrentSchema = self.name
         rv = das.read_string(content, encoding=md.get("encoding", None), **eval_locals)
         das.schematypes.TypeValidator.CurrentSchema = ""
         for typename, validator in rv.iteritems():
            k = "%s.%s" % (self.name, typename)
            if SchemaTypesRegistry.instance.has_schema_type(k):
               raise Exception("[das] Schema type '%s' already registered in another schema" % k)
            else:
               self.types[k] = validator

         mt = md.get("master_types", None)
         if mt is not None:
            mt = filter(lambda y: len(y) > 0, map(lambda x: x.strip(), mt.split(",")))
            self.master_types = set(map(lambda x: "%s.%s" % (self.name, x), mt))

         return True

      else:
         return False

   def unload(self):
      if self.module is not None:
         delattr(das.schema, self.module.__name__.split(".")[-1])
         self.module = None
      self.types = {}
      self.master_types = None

   def list_types(self, sort=True, masters_only=False):
      rv = self.types.keys()
      if masters_only and self.master_types is not None:
         rv = filter(lambda x: x in self.master_types, rv)
      if sort:
         rv.sort()
      return rv

   def is_master_type(self, name):
      return (self.master_types is None or name in self.master_types)

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
         if das.__verbose__:
            print("[das] Load schema file: %s" % schema_file)
         schema = Schema(self, schema_file, dont_load=True)
         if SchemaTypesRegistry.instance.has_schema(schema.name):
            raise Exception("[das] Schema '%s' already registered in another schema")
         else:
            if schema.load():
               self.schemas[schema.name] = schema

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

   def list_schema_types(self, schema=None, sort=True, masters_only=False):
      rv = set()
      for n, s in self.schemas.iteritems():
         if schema is not None and n != schema:
            continue
         rv = rv.union(s.list_types(sort=False, masters_only=masters_only))
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

   def __cmp__(self, oth):
      p0 = os.path.abspath(self.path)
      p1 = os.path.abspath(oth.path)
      if sys.platform == "win32":
         p0 = p0.replace("\\", "/").lower()
         p1 = p1.replace("\\", "/").lower()
      return cmp(p0, p1)

   def __hash__(self):
      return hash(self.path)


class SchemaTypesRegistry(object):
   instance = None

   def __init__(self):
      super(SchemaTypesRegistry, self).__init__()
      if SchemaTypesRegistry.instance is not None:
         raise Exception("SchemaTypesRegistry must be globally unique")
      self.path = ""
      self.addedpath = ""
      self.locations = set()
      self.properties = {}
      self.dyntypes = {}
      self.cache = {"name_to_schema": {},
                    "name_to_type": {},
                    "type_to_name": {}}
      SchemaTypesRegistry.instance = self

   def _rebuild_cache(self):
      nts = {}
      ntt = {}
      ttn = {}
      for location in self.locations:
         for sname in location.list_schemas():
            schema = location.get_schema(sname)
            if not sname in nts:
               nts[sname] = schema
            for tname in schema.list_types():
               ttype = schema.get_type(tname)
               if not tname in ntt:
                  ntt[tname] = ttype
               if not ttype in ttn:
                  ttn[ttype] = tname
      self.cache["name_to_schema"] = nts
      self.cache["name_to_type"] = ntt
      self.cache["type_to_name"] = ttn
      for st in self.cache["type_to_name"]:
         if isinstance(st, das.schematypes.Struct):
            st.load_extensions()

   def load_schemas(self, paths=None, incremental=False, force=False):
      incremental = (paths is not None)
      if not incremental:
         path = os.environ.get("DAS_SCHEMA_PATH", "")
         # Keep in mind paths added incrementally
         if self.addedpath:
            if path:
               path += os.pathsep
            path += self.addedpath
      else:
         path = self.path
         for p in paths:
            if not p in path:
               if path:
                  path += os.pathsep
               path += p
            # Also keep track of added paths
            if not p in self.addedpath:
               if self.addedpath:
                  self.addedpath += os.pathsep
               self.addedpath += p

      if not force and path == self.path:
         return

      self.cache = {"name_to_schema": {},
                    "name_to_type": {},
                    "type_to_name": {}}

      if not incremental:
         locations = set()

         # Build list of not locations
         for d in path.split(os.pathsep):
            if not os.path.isdir(d):
               continue
            location = SchemaLocation(d, dont_load=True)
            if not location in locations:
               locations.add(location)

         # Unload unwanted locations
         remove_locations = set()
         for location in self.locations:
            if not location in locations:
               location.unload_schemas()
               remove_locations.add(location)

         if force:
            # Force load all locations and replace existing ones
            for location in locations:
               location.load_schemas()
            self.locations = locations
         else:
            # Add new locations...
            for location in locations:
               if not location in self.locations:
                  location.load_schemas()
                  self.locations.add(location)
               else:
                  # Already here and loaded
                  pass
            # ... and remove unloaded
            for location in remove_locations:
               self.locations.remove(location)

      else:
         for d in path.split(os.pathsep):
            if not os.path.isdir(d):
               continue
            location = SchemaLocation(d, dont_load=True)
            if not location in self.locations:
               location.load_schemas()
               self.locations.add(location)

         if force:
            forcelocations = set()
            for p in paths:
               forcelocations.add(SchemaLocation(p, dont_load=True))
            for location in self.locations:
               if location in forcelocations:
                  location.load_schemas()

      self.path = path

      # re register dynamically added schema types
      if len(self.dyntypes):
         for k, v in self.dyntypes.iteritems():
            try:
               if not self._add_schema_type(k, v):
                  print("Failed to re register dynamically added type '%s' (already registered)" % k)
            except Exception, e:
               print("Failed to re register dynamically added type '%s' (%s)" % (k, e))

      self._rebuild_cache()

   def list_locations(self, sort=True):
      self.load_schemas()
      rv = [x.path for x in self.locations]
      if sort:
         rv.sort()
      return rv

   def _samepath(self, path0, path1):
      if sys.platform == "win32":
         np0 = os.path.abspath(path0).replace("\\", "/").lower()
         np1 = os.path.abspath(path1).replace("\\", "/").lower()
         return (np0 == np1)
      else:
         return os.path.samefile(path0, path1)

   def get_location(self, path):
      self.load_schemas()
      for location in self.locations:
         if self._samepath(path, location.path):
            return location
      return None

   def list_schemas(self, sort=True):
      self.load_schemas()
      rv = self.cache["name_to_schema"].keys()
      if sort:
         rv.sort()
      return rv

   def list_schema_types(self, schema=None, sort=True, masters_only=False):
      self.load_schemas()
      if schema is None:
         rv = self.cache["name_to_type"].keys()
      else:
         schema = self.cache["name_to_schema"].get(schema, None)
         if schema:
            rv = schema.list_types(sort=False, masters_only=masters_only)
         else:
            rv = []
      if sort:
         rv.sort()
      return rv

   def has_schema(self, name):
      return (name in self.cache["name_to_schema"])

   def get_schema(self, name):
      self.load_schemas()
      schema = self.cache["name_to_schema"].get(name)
      if schema is None:
         raise UnknownSchemaError(name)
      return schema

   def has_schema_type(self, name):
      return (name in self.cache["name_to_type"])

   def get_schema_type(self, name):
      self.load_schemas()
      stype = self.cache["name_to_type"].get(name, None)
      if stype is None:
         raise UnknownSchemaError(name)
      return stype

   def get_schema_type_name(self, typ):
      self.load_schemas()
      return self.cache["type_to_name"].get(typ, "")

   def _add_schema_type(self, name, typ):
      if self.has_schema_type(name):
         return False
      else:
         spl = name.split(".")
         if len(spl) != 2:
            raise Exception("Invalid schema type name '%s'" % name)
         schema = self.get_schema(spl[0])
         schema.types[name] = typ
         self.dyntypes[name] = typ
         return True

   def add_schema_type(self, name, typ):
      if self._add_schema_type(name, typ):
         self._rebuild_cache()
         return True
      else:
         return False

   def set_schema_type_property(self, name, pname, pvalue):
      if not name:
         return False
      else:
         # do not call get_schema_type() as it would trigger a load_schemas
         if self.has_schema_type(name):
            self.cache["name_to_type"][name].set_property(pname, pvalue)
         # always keep a copy of the property in the registry
         props = self.properties.get(name, {})
         props[pname] = pvalue
         self.properties[name] = props
         return True

   def get_schema_type_property(self, name, pname, default=None):
      # do not call get_schema_type() as it would trigger a load_schemas
      if self.has_schema_type(name):
         st = self.cache["name_to_type"][name]
         if not st.has_property(pname):
            props = self.properties.get(name, {})
            if pname in props:
               rv = props[pname]
               # Transfer property to actual schema type
               st.set_property(pname, rv)
               return rv
            else:
               return default
         else:
            if st.has_property(pname):
               pval = st.get_property(pname)
               # Copy property to registry
               props = self.properties.get(name, {})
               props[pname] = pval
               self.properties[name] = props
               return pval
            else:
               return default
      else:
         return self.properties.get(name, {}).get(pname, default)

   def make_default(self, name):
      return self.get_schema_type(name).make_default()

   def make(self, _schema_type_name, *args, **kwargs):
      return self.get_schema_type(_schema_type_name).make(*args, **kwargs)

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
