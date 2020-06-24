import os
import re
import sys
import datetime

__version__ = "0.10.1"
__verbose__ = False
try:
   __verbose__ = (int(os.environ.get("DAS_VERBOSE", "0")) != 0)
except:
   pass

from .types import (ReservedNameError,
                    VersionError,
                    TypeBase,
                    Tuple,
                    Sequence,
                    Set,
                    Dict,
                    Struct,
                    GlobalValidationDisabled)
from .schematypes import (TypeValidator,
                          ValidationError)
from .validation import (UnknownSchemaError,
                         SchemaVersionError,
                         Schema,
                         SchemaLocation,
                         SchemaTypesRegistry)
from .mixin import (SchemaTypeError,
                    BindError,
                    Mixin,
                    bind,
                    has_bound_mixins,
                    get_bound_mixins)
from . import schema

# For backward compatibiilty
Das = Struct


def load_schemas(paths=None, force=False):
   SchemaTypesRegistry.instance.load_schemas(paths=paths, force=force)


def list_schemas():
   return SchemaTypesRegistry.instance.list_schemas()


def has_schema():
   return SchemaTypesRegistry.instance.has_schema()


def get_schema(name_or_type):
   if not isinstance(name_or_type, basestring):
      name_or_type = get_schema_type_name(name_or_type)
   name = name_or_type.split(".")[0]
   return SchemaTypesRegistry.instance.get_schema(name)


def list_schema_types(schema=None, masters_only=False):
   return SchemaTypesRegistry.instance.list_schema_types(schema, masters_only=masters_only)


def has_schema_type(name):
   return SchemaTypesRegistry.instance.has_schema_type(name)


def get_schema_type(name):
   return SchemaTypesRegistry.instance.get_schema_type(name)


def get_schema_type_name(typ):
   return SchemaTypesRegistry.instance.get_schema_type_name(typ)


def add_schema_type(name, typ):
   return SchemaTypesRegistry.instance.add_schema_type(name, typ)

# These 2 classes are meant to be used in conjonction to define_inline_type
class one_of(object):
   def __init__(self, *types):
      super(one_of, self).__init__()
      self.types = types

class none_or(one_of):
   def __init__(self, typ):
      super(none_or, self).__init__(None, typ)

def define_inline_type(typ):
   if typ is None:
      return schematypes.Empty()
   elif isinstance(typ, one_of):
      otypes = map(define_inline_type, typ.types)
      return schematypes.Or(*otypes)
   elif isinstance(typ, dict):
      n = len(typ)
      if n == 0:
         raise Exception("'dict' execpted to have length at least 1")
      stringkeys = True
      for k in typ.keys():
         if not isinstance(k, basestring):
            stringkeys = False
            break
      if stringkeys:
         items = dict(map(lambda x: (x[0], define_inline_type(x[1])), typ.items()))
         t = schematypes.Struct(**items)
         return t
      else:
         if n != 1:
            raise Exception("'dict' execpted to have length 1 or only string keys")
         kt, vt = typ.items()[0]
         return schematypes.Dict(ktype=define_inline_type(kt), vtype=define_inline_type(vt))
   elif isinstance(typ, list):
      if len(typ) != 1:
         raise Exception("'list' execpted to have length 1")
      return schematypes.Sequence(define_inline_type(typ[0]))
   elif isinstance(typ, set):
      if len(typ) != 1:
         raise Exception("'set' execpted to have length 1")
      return schematypes.Set(define_inline_type(typ.copy().pop()))
   elif isinstance(typ, tuple):
      tpl = map(lambda x: define_inline_type(x), typ)
      return schematypes.Tuple(*tpl)
   # Other accepted values are only class
   if not type(typ) is type:
      raise Exception("'%s' is not a type" % typ)
   elif issubclass(typ, basestring):
      return schematypes.String()
   elif typ in (int, long):
      return schematypes.Integer()
   elif typ in (float,):
      return schematypes.Real()
   elif typ in (bool,):
      return schematypes.Boolean()
   else:
      raise Exception("Unsupported simple type '%s'" % typ.__name__)


def register_mixins(*mixins):
   if __verbose__:
      print("[das] Register mixins: %s" % ", ".join(map(lambda x: x.__module__ + "." + x.__name__, mixins)))
   tmp = {}
   for mixin in mixins:
      st = mixin.get_schema_type()
      lst = tmp.get(st, [])
      lst.append(mixin)
      tmp[st] = lst
   for k, v in tmp.iteritems():
      mixins = SchemaTypesRegistry.instance.get_schema_type_property(k, "mixins")
      if mixins is None:
         mixins = []
      changed = False
      for mixin in v:
         if not mixin in mixins:
            mixins.append(mixin)
            changed = True
      if changed:
         SchemaTypesRegistry.instance.set_schema_type_property(k, "mixins", mixins)


def get_registered_mixins(name):
   return SchemaTypesRegistry.instance.get_schema_type_property(name, "mixins")


def get_schema_path(name):
   return SchemaTypesRegistry.instance.get_schema_path(name)


def get_schema_module(name):
   return SchemaTypesRegistry.instance.get_schema_module(name)


def make_default(name):
   return SchemaTypesRegistry.instance.make_default(name)


def make(_schema_type_name, *args, **kwargs):
   return SchemaTypesRegistry.instance.make(_schema_type_name, *args, **kwargs)


def adapt_value(value, schema_type=None, key=None, index=None):
   if schema_type:
      return schema_type.validate(value, key=key, index=index)
   else:
      if isinstance(value, TypeBase):
         return value
      elif isinstance(value, dict):
         try:
            rv = Struct(**value)
         except ReservedNameError, e:
            # If failed to create Struct because of a ReservedNameError exception, wrap using Dict class
            rv = Dict(**value)
         return rv
      else:
         klass = None
         if isinstance(value, tuple):
            klass = Tuple
         elif isinstance(value, list):
            klass = Sequence
         elif isinstance(value, set):
            klass = Set
         if klass is not None:
            n = len(value)
            l = [None] * n
            i = 0
            for item in value:
               l[i] = adapt_value(item)
               i += 1
            return klass(l)
         else:
            return value


def conform(value, schema_type, fill=False):
   if not isinstance(schema_type, TypeValidator):
      schema_type = get_schema_type(schema_type)

   return schema_type.conform(value, fill=fill)


def validate(d, schema_type):
   if not isinstance(schema_type, (basestring, TypeValidator)):
      raise Exception("Expected a string or a das.schematypes.TypeValidator instance as second argument")
   if isinstance(schema_type, TypeValidator):
      return schema_type.validate(d)
   else:
      return get_schema_type(schema_type).validate(d)


def check(d, schema_type):
   if not isinstance(schema_type, (basestring, TypeValidator)):
      raise Exception("Expected a string or a das.schematypes.TypeValidator instance as second argument")
   try:
      if isinstance(schema_type, TypeValidator):
         schema_type.validate(copy(d))
      else:
         get_schema_type(schema_type).validate(copy(d))
      return True
   except:
      return False


def is_compatible(d, schema_type):
   if not isinstance(schema_type, (basestring, TypeValidator)):
      raise Exception("Expected a string or a das.schematypes.TypeValidator instance as second argument") 
   try:
      if isinstance(schema_type, TypeValidator):
         schema_type.is_compatible(copy(d))
      else:
         get_schema_type(schema_type).is_compatible(copy(d))
      return True
   except:
      return False


def _read_file(path, skip_content=False):
   mde = re.compile("^\s*([^:]+):\s*(.*)\s*$")
   reading_content = False
   content = ""
   md = {}
   if os.path.isfile(path):
      with open(path, "rb") as f:
         for l in f.readlines():
            sl = l.strip()
            if sl.startswith("#"):
               if not reading_content:
                  m = mde.match(sl[1:])
                  if m is not None:
                     md[m.group(1)] = m.group(2)
            else:
               reading_content = True
               if skip_content:
                  break
               else:
                  # Convert line endings to LF on the fly
                  content += l.rstrip() + "\n"
   return md, content


def read_meta(path):
   return _read_file(path, skip_content=True)[0]


def ascii_or_unicode(s, encoding=None):
   if isinstance(s, str):
      try:
         s.decode("ascii")
         return s
      except Exception, e:
         if encoding is None:
            raise Exception("Input string must be 'ascii' encoded (%s)" % e)
         try:
            return s.decode(encoding)
         except Exception, e:
            raise Exception("Input string must be 'ascii' or '%s' encoded (%s)" % (encoding, e))
   elif isinstance(s, unicode):
      try:
         return s.encode("ascii")
      except:
         return s
   else:
      raise Exception("'ascii_or_unicode' only works on string types (str, unicode)")


def decode(d, encoding):
   if hasattr(d, "_decode") and callable(getattr(d, "_decode")):
      try:
         return d._decode(encoding)
      except Exception, e:
         print_once("[das] '%s._decode' method call failed (%s)\n[das] Fallback to default decoding" % (d.__class__.__name__, e))

   if isinstance(d, basestring):
      return ascii_or_unicode(d, encoding=encoding)
   elif isinstance(d, tuple):
      return d.__class__([decode(x, encoding) for x in d])
   elif isinstance(d, set):
      return d.__class__([decode(x, encoding) for x in d])
   else:
      # In-place
      if isinstance(d, list):
         for idx, val in enumerate(d):
            d[idx] = decode(val, encoding)
      elif isinstance(d, dict):
         for k, v in d.iteritems():
            d[k] = decode(v, encoding)
      elif isinstance(d, Struct):
         for k, v in d._dict.iteritems():
            d[k] = decode(v, encoding)
      return d


def read_string(s, schema_type=None, encoding=None, strict_schema=True, **funcs):
   if schema_type is not None:
      if isinstance(schema_type, basestring):
         schname = schema_type
         sch = get_schema_type(schema_type)
      elif isinstance(schema_type, TypeValidator):
         schname = get_schema_type_name(schema_type)
         sch = schema_type
      else:
         print_once("[das] 'schema_type' must either be a string or a das.schematypes.TypeValidator instance")
         sch = None
      if sch is not None:
         mod = get_schema_module(schname)
         if mod is not None and hasattr(mod, "__all__"):
            for item in mod.__all__:
               funcs[item] = getattr(mod, item)
      else:
         mod = None
   else:
      sch, mod = None, None

   if not encoding:
      if __verbose__:
         print_once("[das] Warning: das.read assumes system default encoding for unicode characters unless explicitely set.")
   else:
      s = ("# encoding: %s\n" % encoding) + s

   rv = eval(s, globals(), funcs)

   if encoding:
      rv = decode(rv, encoding)

   if sch is None:
      return rv
   else:
      try:
         schematypes.Struct.CompatibilityMode = (True if not strict_schema else False)
         return sch.validate(rv)
      finally:
         schematypes.Struct.CompatibilityMode = False


# returns: -2 if version check could not be performed
#          -1 imcompatible
#           0 forward compatible
#           1 fully compatible
#           2 backward compatible
def is_version_compatible(reqver, curver):
   try:
      cur = map(int, curver.split("."))
      req = map(int, reqver.split("."))
      if req[0] != cur[0]:
         return -1
      elif req[1] > cur[1]:
         return 0
      else:
         return (1 if req[1] == cur[1] else 2)
   except:
      return -2


def read(path, schema_type=None, ignore_meta=False, strict_schema=None, **funcs):
   # Read header data
   md, src = _read_file(path)  

   libver = md.get("version", None)
   if libver:
      compat = is_version_compatible(libver, __version__)
      if compat <= 0:
         raise VersionError("Library", current_version=__version__, required_version=libver)

   schema_version = None
   if schema_type is None and not ignore_meta:
      schema_type = md.get("schema_type", None)

   if schema_type:
      schema = get_schema(schema_type)
      if schema:
         schema_version = md.get("schema_version", None)
         if schema_version:
            if not schema.version:
               raise SchemaVersionError(schema.name, required_version=schema_version)
            else:
               compat = is_version_compatible(schema_version, schema.version)
               if compat == -2:
                  # Invalid version specifications
                  raise SchemaVersionError(schema.name, current_version=schema.version, required_version=schema_version)
               elif compat == -1:
                  # Incompatible schema
                  raise SchemaVersionError(schema.name, current_version=schema.version, required_version=schema_version)
               elif compat == 2:
                  if __verbose__:
                     print_once("[das] Warning: '%s' data was saved using an older version of the schema, newly added fields will be set to their default value" % schema_type)
                  if strict_schema is None:
                     strict_schema = False
               elif compat == 0:
                  if __verbose__:
                     print_once("[das] Warning: '%s' data was saved using a newer version of the schema, you may loose information in the process" % schema_type)
                  if strict_schema is None:
                     strict_schema = False

   encoding = md.get("encoding", None)
   if encoding is None:
      if __verbose__:
         print_once("[das] Warning: No encoding specified in file '%s'." % path.replace("\\", "/"))

   if strict_schema is None:
      strict_schema = True

   return read_string(src, schema_type=schema_type, encoding=encoding, strict_schema=strict_schema, **funcs)


class _Placeholder(object):
   def __init__(self, is_optional=False):
      object.__init__(self)
      self.optional = is_optional

   def __repr__(self):
      return "__NULL__"

   @staticmethod
   def is_place_holder(data):
      if isinstance(data, (dict)):
         for k, v in data.items():
            if _Placeholder.is_place_holder(k):
               return True

            if _Placeholder.is_place_holder(v):
               return True

      elif isinstance(data, (list, tuple, set)):
         for v in data:
            if _Placeholder.is_place_holder(v):
               return True

      return isinstance(data, _Placeholder)

   @staticmethod
   def make_place_holder(st, is_optional=False):
      if isinstance(st, (schematypes.Struct, schematypes.Dict)):
         return _PlaceholderDict(is_optional=is_optional)

      elif isinstance(st, schematypes.Sequence):
         return _PlaceholderList(is_optional=is_optional)

      return _Placeholder(is_optional=is_optional)

   @staticmethod
   def finalize(data):
      if isinstance(data, (dict)):
         pop_list = []
         new_dict = {}

         for k, v in data.items():
            if isinstance(v, _PlaceholderDict):
               if not v and v.optional:
                  pop_list.append(k)
                  continue

               new_dict[k] = v.copy()

            elif isinstance(v, _PlaceholderList):
               if not v and v.optional:
                  pop_list.append(k)
                  continue

               new_dict[k] = v[:]

            elif isinstance(v, _Placeholder):
               if v.optional:
                  pop_list.append(k)
                  continue

               new_dict[k] = v

            else:
               new_dict[k] = v

         for k, v in new_dict.items():
            _Placeholder.finalize(v)
            data[k] = v

         for k in pop_list:
            data.pop(k)

      elif isinstance(data, (list, tuple, set)):
         pop_list = []
         new_list = {}

         for i, v in enumerate(data):
            if isinstance(v, _PlaceholderDict):
               if not v and v.optional:
                  pop_list.append(i)
                  continue

               new_list[i] = v.copy()

            elif isinstance(v, _PlaceholderList):
               if not v and v.optional:
                  pop_list.append(i)
                  continue

               new_list[i] = v[:]

            elif isinstance(v, _Placeholder):
               if v.optional:
                  pop_list.append(i)
                  continue

               new_list[i] = v

            else:
               new_list[i] = v

         for i, v in new_list.items():
            _Placeholder.finalize(v)
            data[i] = v

         for i in sorted(pop_list, reverse=True):
            data.pop(i)


class _PlaceholderDict(dict, _Placeholder):
   def __init__(self, is_optional=False):
      dict.__init__(self)
      _Placeholder.__init__(self, is_optional=is_optional)


class _PlaceholderList(list, _Placeholder):
   def __init__(self, is_optional=False):
      list.__init__(self)
      _Placeholder.__init__(self, is_optional=is_optional)


def _get_value_type(parent, key):
   if key == "{value}":
      return parent.vtype

   elif key == "[value]":
      return parent.type

   return parent[key]


def _get_org_type(st):
   while (isinstance(st, schematypes.SchemaType)):
      st = get_schema_type(st.name)

   if isinstance(st, schematypes.Optional):
      st = st.type

   while (isinstance(st, schematypes.SchemaType)):
      st = get_schema_type(st.name)

   return st


def _read_csv(value, row, header, headers, schematype, data, csv):
   re_d_key = re.compile("[{]key[}]$")
   re_a_index = re.compile("[[]index[]]$")
   re_dot = re.compile("[.]")
   re_tkn = re.compile("[[{][^]}{[]+[]}]")
   st = schematype

   keys = []
   for sh in re_dot.split(header):
      pure_name = re_tkn.sub("", sh)
      keys.append(pure_name)
      keys += re_tkn.findall(sh)

   parent = data
   key = keys[0]
   found = True

   parent_header = ""
   is_optional = False

   while (True):
      creatable = True
      cur_key = keys.pop(0)
      cur_header = cur_key

      # {key} and [index] should be only at the end of header
      if cur_key == "{key}":
         break

      elif cur_key == "[index]":
         break

      st = _get_value_type(st, cur_key)
      if isinstance(st, schematypes.Optional):
         is_optional = True

      st = _get_org_type(st)

      if cur_key == "{value}":
         creatable = False
         kv = csv[row][headers[parent_header + "{key}"]]
         if kv == "":
            found = False
            break

         key = kv

      elif cur_key == "[value]":
         creatable = False
         iv = csv[row][headers[parent_header + "[index]"]]
         if iv == "":
            found = False
            break

         key = int(iv)

      else:
         key = cur_key
         cur_header = ("." + cur_key) if parent_header else cur_key

      parent_header += cur_header

      if not keys:
         break

      if not creatable:
         parent = parent[key]
      else:
         parent[key] = parent.get(key, _Placeholder.make_place_holder(st, is_optional=is_optional))
         parent = parent[key]

   if not found:
      return

   if re_d_key.search(header):
      if value != "":
         parent[value] = _Placeholder.make_place_holder(_get_org_type(st.vtype), is_optional=is_optional)

      return

   if re_a_index.search(header):
      if value != "":
         parent.append(_Placeholder.make_place_holder(_get_org_type(st.type), is_optional=is_optional))

      return

   if key in parent and not isinstance(parent[key], _Placeholder):
      return

   # TODO : find better way
   value = value.replace('\\"', '"')

   if not value:
      if is_optional:
         p = _Placeholder(is_optional=is_optional)
         return

      try:
         value = st.string_to_value(value)
      except:
         return

   parent[key] = st.string_to_value(value)


def read_csv_table(csv_table):
   data_table = csv_table[:]

   headers = data_table.pop(0)
   col_size = len(headers)
   row_size = len(data_table)

   re_metadata = re.compile("^[<](.*)[>]$")
   re_alias = re.compile("[ ]+as[ ]+([^ ]+)[ ]*$")

   mts = {}
   contents = []
   alias_map = {}
   column_map = {}
   header_map = {}
   regex_map = {}

   # read metadata
   column = 0
   for header in headers:
      hr = re_metadata.search(header)
      if not hr:
         break

      mtn = hr.group(1)
      if mtn == "schematype":
         cur = None
         for r in range(row_size):
            tv = data_table[r][column]

            if tv:
               alr = re_alias.search(tv)
               tv = re_alias.sub("", tv)
               if alr:
                  if tv in alias_map and alr.group(1) != alias_map[tv]:
                     raise Exception("Two different aliases were set of '%s'" % (tv))

                  alias_map[tv] = alr.group(1)

               if tv not in column_map:
                  column_map[tv] = list()

               cur = {"type": tv, "start": r, "end": r}
               contents.append(cur)

            elif cur is not None:
               cur["end"] = r

      else:
         mts[hr.group(1)] = data_table[0][column]

      column += 1

   # get content column range
   for k, cln_list in column_map.items():
      als = alias_map.get(k, k)
      regex = re.compile("^" + als.replace(".", "[.]") + "[.]")

      regex_map[k] = regex
      con_headers = {}
      header_map[k] = con_headers

      for c in range(column, col_size):
         if regex.search(headers[c]):
            con_headers[regex.sub("", headers[c])] = c
            cln_list.append(c)

   results = []

   for content in contents:
      typ = content["type"]
      row_start = content["start"]
      row_end = content["end"]
      regex = regex_map[typ]
      schema_type = get_schema_type(typ)
      con_headers = header_map[typ]
      read_data = {}
      for c in column_map[typ]:
         header = regex.sub("", headers[c])
         for r in range(row_start, row_end + 1):
            _read_csv(data_table[r][c], r, header, con_headers, schema_type, read_data, data_table)

      _Placeholder.finalize(read_data)

      if _Placeholder.is_place_holder(read_data):
         raise Exception("Parsing uncompleted")

      results.append(schema_type.partial_make(read_data))

   return results


def read_csv(csv_path, delimiter="\t", newline="\n"):
   re_metadata = re.compile("^[<](.*)[>]$")
   re_strip = re.compile(newline + "$")
   re_alias = re.compile("[ ]+as[ ]+([^ ]+)[ ]*$")
   re_delimiter = re.compile(delimiter)

   if not os.path.isfile(csv_path):
      return []

   with open(csv_path, "r") as f:
      lines = map(lambda x: re_strip.sub("", x), f.readlines())

   if len(lines) == 0:
      return []

   csv_table = []
   col_size = len(re_delimiter.split(lines[0]))

   for l in lines:
      col_datas = re_delimiter.split(l)
      if col_size != len(col_datas):
         raise Exception("Parsing '%s' was failed" % (csv_path))

      csv_table.append(col_datas)

   return read_csv_table(csv_table)


def copy(d, deep=True):
   if isinstance(d, TypeValidator):
      return d.copy()
   elif isinstance(d, list):
      if deep:
         rv = d.__class__([copy(x, deep=True) for x in d])
      else:
         rv = d.__class__(d[:])
   elif isinstance(d, tuple):
      if deep:
         rv = d.__class__([copy(x, deep=True) for x in d])
      else:
         rv = d.__class__(d[:])
   elif isinstance(d, set):
      if deep:
         rv = d.__class__([copy(x, deep=True) for x in d])
      else:
         rv = d.__class__([x for x in d])
   elif isinstance(d, dict):
      if deep:
         rv = d.__class__()
         for k, v in d.iteritems():
            rv[k] = copy(v, deep=True)
      else:
         rv = d.copy()
   elif isinstance(d, Struct):
      if deep:
         rv = d.__class__()
         for k, v in d._dict.iteritems():
            rv[k] = copy(v, deep=True)
      else:
         rv = d._copy()
   elif hasattr(d, "copy") and callable(getattr(d, "copy")):
      rv = d.copy()
   else:
      rv = d
   if isinstance(rv, TypeBase) and isinstance(d, TypeBase):
      rv._set_schema_type(d._get_schema_type())
   return rv


def _get_sorted_keys(d):
   _keys = [k for k in d]
   try:
      keys = d.ordered_keys()
      # Just in case we get empty key list, make sure we have something
      if not keys:
         keys = [k for k in d]
      else:
         ekeys = list(set(_keys).difference(keys))
         ekeys.sort()
         keys += ekeys
   except:
      keys = _keys
      keys.sort()

   for k in keys:
      # We assume string keys are 'ascii'
      if isinstance(k, unicode):
         try:
            k = k.encode("ascii")
         except:
            raise Exception("Non-ascii keys are not supported!")
      elif isinstance(k, str):
         try:
            k.decode("ascii")
         except:
            raise Exception("Non-ascii keys are not supported!")

   return keys


def pprint(d, stream=None, indent="  ", depth=0, inline=False, eof=True, encoding=None):
   if stream is None:
      stream = sys.stdout

   tindent = indent * depth

   if not inline:
      stream.write(tindent)

   if isinstance(d, (dict, Struct)):
      stream.write("{\n")
      n = len(d)
      i = 0
      keys = _get_sorted_keys(d)
      for k in keys:
         stream.write("%s%s%s: " % (tindent, indent, repr(k)))
         v = d[k]
         pprint(v, stream, indent=indent, depth=depth+1, inline=True, eof=False, encoding=encoding)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s}" % tindent)

   elif isinstance(d, list):
      stream.write("[\n")
      n = len(d)
      i = 0
      for v in d:
         pprint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False, encoding=encoding)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s]" % tindent)

   elif isinstance(d, set):
      stream.write("set([\n")
      n = len(d)
      i = 0
      for v in d:
         pprint(v, stream, indent=indent, depth=depth+1, inline=False, eof=False, encoding=encoding)
         i += 1
         if i >= n:
            stream.write("\n")
         else:
            stream.write(",\n")
      stream.write("%s])" % tindent)

   elif isinstance(d, str):
      try:
         d.decode("ascii")
      except Exception, e:
         if not encoding:
            raise Exception("Non-ascii string value found but no encoding provided (%s)." % e)
         try:
            stream.write(repr(d.decode(encoding)))
         except Exception, e:
            raise Exception("Non-ascii string value cannot be decoded to '%s' (%s)." % (encoding, e))
      else:
         # properly deal with multiline characters
         # using repr here would solve the problem too but lead to less readable files
         # -> line1\\nline1 -> eval -> line1\nline2
         lines = d.split("\n")
         nlines = len(lines)
         if nlines > 1:
            stream.write("'''")
            for i in xrange(nlines):
               stream.write(lines[i])
               if i + 1 < nlines:
                  stream.write("\n")
            stream.write("'''")
         else:
            # stream.write("'%s'" % d)
            stream.write(repr(d))

   elif isinstance(d, unicode):
      try:
         s = d.encode("ascii")
      except:
         stream.write(repr(d))
      else:
         # see comment above
         lines = s.split("\n")
         nlines = len(lines)
         if nlines > 1:
            stream.write("'''")
            for i in xrange(nlines):
               stream.write(lines[i])
               if i + 1 < nlines:
                  stream.write("\n")
            stream.write("'''")
         else:
            # stream.write("'%s'" % s)
            stream.write(repr(s))

   else:
      # stream.write(str(d))
      stream.write(repr(d))

   if eof:
      stream.write("\n")


class _CSVHeader(object):
   def __init__(self, name, column, fill=True):
      super(_CSVHeader, self).__init__()
      self.__column = column
      self.__name = name
      self.__data = []
      self.__fill = fill

   def fill(self):
      return self.__fill

   def column(self):
      return self.__column

   def name(self):
      return self.__name

   def add_data(self, data):
      self.__data.append(data)

   def data(self):
      return self.__data[:]

   def get_row(self, data):
      if data not in self.__data:
         return -1

      c = 0
      for d in self.__data:
         if d == data:
            return c

         c += d.count()

      return -1

   def row_count(self):
      rc = 0
      for d in self.__data:
         rc += d.count()

      return rc


class _CSVValue(object):
   def __init__(self, value, header, valuetype=None, parent=None):
      super(_CSVValue, self).__init__()
      self.__children = []
      self.__header = header
      self.__parent = parent
      self.__valuetype = valuetype
      self.__value = value

      if parent:
         parent.__children.append(self)

   def header(self):
      return self.__header

   def value(self):
      return self.__value

   def valuetype(self):
      return self.__valuetype

   def parent(self):
      return self.__parent

   def children(self):
      return self.__children[:]

   def row(self):
      if not self.__parent:
         return self.__header.get_row(self)

      return self.__parent.get_row(self)

   def get_row(self, child):
      if child not in self.__children:
         raise Exception("'%s' is not a child of '%s'" % (child.value(), self.value()))

      cr = self.row()
      header_count = {}
      for c in self.__children:
         h = c.header()
         if h not in header_count:
            header_count[h] = cr

         if c == child:
            return header_count[h]

         header_count[h] += c.count()

   def count(self):
      if not self.__children:
         return 1

      header_count = {}
      for c in self.__children:
         h = c.header()
         if h not in header_count:
            header_count[h] = 0

         header_count[h] += c.count()

      return max(header_count.values())


def _get_header(key, headers):
   header = None
   for h in headers:
      if key == h.name():
         header = h
         break

   if not header:
      header = _CSVHeader(key, len(headers))
      headers.append(header)

   return header


def _dump_csv_data(k, d, valuetype, headers, parent=None, prefix=None):
   if prefix is None:
      prefix = ""

   valuetype = _get_org_type(valuetype)

   if isinstance(d, Struct):
      if not d:
         return

      ckeys = map(lambda x: eval(repr(x)), _get_sorted_keys(d))

      for ck in ckeys:
         _dump_csv_data(k + "." + ck, d[ck], valuetype.get(ck), headers, parent=parent, prefix=prefix)

   elif isinstance(d, dict):
      if not d:
         return

      ckeys = map(lambda x: eval(repr(x)), _get_sorted_keys(d))
      key_header = _get_header(prefix + k + "{key}", headers)

      vk = k + "{value}"
      for ck in ckeys:
         kv = _CSVValue(ck, key_header, parent=parent)
         key_header.add_data(kv)
         _dump_csv_data(vk, d[ck], valuetype.vtype, headers, parent=kv, prefix=prefix)

   elif isinstance(d, (list, set, tuple)):
      if not d:
         return

      index_header = _get_header(prefix + k + "[index]", headers)
      vk = k + "[value]"
      i = 0
      for v in d:
         index = _CSVValue(str(i), index_header, parent=parent)
         index_header.add_data(index)
         vt = None
         if isinstance(valuetype, (schematypes.Sequence, schematypes.Set)):
            vt = valuetype.type
         elif isinstance(valuetype, schematypes.Tuple):
            vt = valuetype.types[i]
         else:
            raise Exception("Unexpected value type '%s'" % valuetype)

         _dump_csv_data(vk, v, vt, headers, parent=index, prefix=prefix)
         i += 1

   # scalar
   else:
      header = _get_header(prefix + k, headers)

      cv = _CSVValue(valuetype.value_to_string(d), header, valuetype=valuetype, parent=parent)
      header.add_data(cv)


def write(d, path, indent="  ", encoding=None):
   d._validate()

   schema_type = d._get_schema_type()

   if encoding is None and schema_type:
      encoding = "utf8"

   with open(path, "wb") as f:
      if encoding is not None:
         f.write("# encoding: %s\n" % encoding)
      f.write("# version: %s\n" % __version__)
      f.write("# author: %s\n" % os.environ["USER" if sys.platform != "win32" else "USERNAME"])
      f.write("# date: %s\n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
      if schema_type:
         st = get_schema_type_name(schema_type)
         f.write("# schema_type: %s\n" % st)
         sn = get_schema(st)
         if sn and sn.version is not None:
            f.write("# schema_version: %s\n" % sn.version)
      pprint(d, stream=f, indent=indent, encoding=encoding)


def write_csv(data, path, alias=None, encoding=None, delimiter="\t", newline="\n"):
   data_list = []

   if isinstance(data, types.TypeBase):
      if not data._get_schema_type():
            raise Exception("Cannot export a csv file from unschemed data")

      data_list = [data]

   elif isinstance(data, (set, list)):
      for d in data:
         if not isinstance(d, types.TypeBase):
            raise Exception("Invalid data given. Must be a instance of das.types.TypeBase")
         if not d._get_schema_type():
            raise Exception("Cannot export a csv file from unschemed data")

         data_list.append(d)

   if alias is None:
      alias = {}

   header_schema = _CSVHeader("<schematype>", 0, fill=False)
   headers = [header_schema]

   alias_defined = set()
   for d in data_list:
      d._validate()

      schema_type = d._get_schema_type()
      schema_type_name = get_schema_type_name(schema_type)
      type_value = schema_type_name

      prefix = alias.get(schema_type_name, schema_type_name)
      if prefix != schema_type_name and prefix not in alias_defined:
         alias_defined.add(prefix)
         type_value = schema_type_name + " as " + prefix
      prefix += "."

      schem_val = _CSVValue(type_value, header_schema)
      header_schema.add_data(schem_val)

      keys = map(lambda x: eval(repr(x)), _get_sorted_keys(d))

      for k in keys:
         _dump_csv_data(k, d[k], schema_type[k], headers, parent=schem_val, prefix=prefix)

   with open(path, "wb") as f:
      f.write(delimiter.join(map(lambda x: x.name(), headers)))
      row_counts = max(map(lambda x: x.row_count(), headers))

      column_counts = len(headers)
      lines = map(lambda y: map(lambda x: "", range(column_counts)), range(row_counts))

      for header in headers:
         for hd in header.data():
            vv = hd.value()

            # TODO : find better way
            if "\"" in hd.value():
               vv = vv.replace("\"", "\\\"")

            sr = hd.row()
            er = sr + (hd.count() if header.fill() else 1)
            c = header.column()

            for r in range(sr, er):
               if lines[r][c] != "":
                  raise Exception("Invalid index. There is a data at [%s][%s] already" % (r, c))
               lines[r][c] = vv

      for r in lines:
         f.write(newline)
         f.write(delimiter.join(r))


def generate_empty_schema(path, name=None, version=None, author=None):
   with open(path, "wb") as f:
      if not name:
         name = os.path.basename(path).split(".")[0]
      if not author:
         author = os.environ["USER" if sys.platform != "win32" else "USERNAME"]
      if not version:
         version = "1.0"
      f.write("# encoding: utf8\n")
      f.write("# name: %s\n" % name)
      f.write("# version: %s\n" % version)
      f.write("# das_minimum_version: %s\n" % __version__)
      f.write("# author: %s\n" % author)
      f.write("# date: %s\n" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
      f.write("{\n")
      f.write("}\n\n")


def update_schema_metadata(path, name=None, version=None, author=None):
   md, content = _read_file(path)
   changed = False

   if not "encoding" in md:
      md["encoding"] = "ascii"
      changed = True

   if name:
      if md.get("name", "") != name:
         md["name"] = name
         changed = True
   elif not "name" in md:
      md["name"] = os.path.basename(path).split(".")[0]
      changed = True

   if version:
      if md.get("version", "") != version:
         md["version"] = version
         changed = True
   
   if author:
      if md.get("author", "") != author:
         md["author"] = author
         changed = True
   
   if not "das_minimum_version" in md:
      md["das_minimum_version"] = __version__
      changed = True

   if changed:
      md["date"] = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

      with open(path, "wb") as f:
         for mdn in ("encoding", "name", "version", "das_minimum_version", "author", "date"):
            if not mdn in md:
               continue
            f.write("# %s: %s\n" % (mdn, md[mdn]))
         f.write(content)

   else:
      if __verbose__:
         print("[das] No need to update schema metadata")


# Utilities

_PrintedMsgs = set()

def print_once(msg):
   global _PrintedMsgs
   if msg in _PrintedMsgs:
      return
   print(msg)
   _PrintedMsgs.add(msg)
