
__all__ = ["CustomClass"]

class CustomClass(object):
   def __init__(self, value=None):
      super(CustomClass, self).__init__()
      self._value = None
      self.set_value({} if value is None else value)

   def __str__(self):
      return "CustomClass(%s)" % repr(self._value)

   def __repr__(self):
      return "CustomClass(%s)" % repr(self._value)

    def __cmp__(self, oth):
      return self._value.__cmp__(oth._value)

   def copy(self):
      return CustomClass(self._value)

   def value_to_string(self):
      return str(self._value)

   def string_to_value(self, s):
      self.set_value(eval(s))

   def set_value(self, value):
      self._value = None

      if isinstance(value, (str, unicode)):
         self.string_to_value(value)
         return

      items = None
      d = {}

      if isinstance(value, dict):
         items = value.items()

      elif isinstance(value, (tuple, list, set)):
         items = value

      if items is not None:
         for k, v in items:
            if not isinstance(k, (str, unicode)):
               raise Exception("Key type must be str or unicode")
            if not isinstance(v, (int, long)):
               raise Exception("Value type must be int or long")
            d[k] = v
      else:
         raise Exception("Expected dict, tuple, list, set, str or unicode")

      self._value = d
