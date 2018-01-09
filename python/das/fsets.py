import das


class SchemaTypeError(Exception):
   def __init__(self, msg):
      super(SchemaTypeError, self).__init__(msg)


class FunctionSet(object):
   def __init__(self, data=None, create=True, validate=True):
      super(FunctionSet, self).__init__()
      schema_type = self.get_schema_type()
      if schema_type is None:
         raise SchemaTypeError("Invalid schema type '%s'" % schema_type)
      if data is None:
         self.data = schema_type.make_default()
      elif validate:
         self.bind(data)
      else:
         self.data = data

   def get_schema_type(self):
      raise None

   def bind(self, data):
      self.data = self.get_schema_type().validate(data)

   def read(self, path):
      self.bind(das.read(path, ignore_meta=True))

   def write(self, path):
      das.write(self.data, path)

   def pprint(self):
      das.pprint(self.data)

   def copy(self):
      rv = self.__class__()
      rv.bind(das.copy(self.data))
      return rv

   # The two following method are to impersonate TypeBase type

   def _validate(self, schema_type=None):
      if schema_type is not None and schema_type != self.get_schema_type():
         raise das.ValidationError("FunctionSet schema type mismatch")
      self.data._validate(schema_type=schema_type)

   def _get_schema_type(self):
      return self.get_schema_type()
