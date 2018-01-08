import das


class BindError(Exception):
   def __init__(self, msg):
      super(BindError, self).__init__(msg)


class SchemaTypeError(Exception):
   def __init__(self, msg):
      super(SchemaTypeError, self).__init__(msg)


class FunctionSet(object):
   def __init__(self, schema_type, data=None):
      super(FunctionSet, self).__init__()
      self.schema_type = das.get_schema_type(schema_type)
      if self.schema_type is None:
         raise SchemaTypeError("Invalid schema type '%s'" % schema_type)
      self.data = data
      if self.data is None:
         self.data = self.schema_type.make_default()

   def bind(self, data):
      self.data = self.schema_type.validate(data)

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
