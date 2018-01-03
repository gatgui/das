import das

__all__ = ["BindError",
           "SchemaTypeError",
           "FunctionSet"]


class BindError(Exception):
   def __init__(self, msg):
      super(BindError, self).__init__(msg)


class SchemaTypeError(Exception):
   def __init__(self, msg):
      super(SchemaTypeError, self).__init__(msg)


class FunctionSet(das.struct.Das):
   def __init__(self, schema_type=None, data=None):
      super(FunctionSet, self).__init__()
      st = (das.get_schema_type(schema_type) if schema_type else None)
      if st is None:
         raise SchemaTypeError("Invalid schema type '%s'" % schema_type)
      self._set_schema_type(st)
      if data is None:
         data = st.make_default()
      self.bind(data)

   def bind(self, data):
      if not isinstance(data, das.struct.Das):
         raise BindError("data must be an instance of das.struct.Das class")
      self._update(data._dict)
      self._validate()

   def read(self, path):
      self.bind(das.read(path, ignore_meta=True))

   def write(self, path):
      das.write(self, path)

   def pprint(self):
      das.pprint(self)

   def copy(self):
      rv = self.__class__()
      rv.bind(das.copy(self))
      return rv
