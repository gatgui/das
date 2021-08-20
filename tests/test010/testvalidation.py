import das # pylint: disable=import-error

class SomeTypeValidator(das.Mixin):
   @classmethod
   def get_schema_type(klass):
      return "validation.SomeType"

   def __init__(self, *args, **kwargs):
      super(SomeTypeValidator, self).__init__(*args, **kwargs)

   def _validate_globally(self):
      for k, v in self.value_pairs.iteritems():
         if not k in self.valid_keys:
            raise Exception("Invalid key '%s'" % k)
         if not self.accepted_values.boolean and isinstance(v, bool):
            raise Exception("Boolean not allowed")
         if not self.accepted_values.integer and isinstance(v, (int, long)):
            raise Exception("Integer not allowed")
         if not self.accepted_values.real and isinstance(v, float):
            raise Exception("Real not allowed")
         if not self.accepted_values.string and isinstance(v, basestring):
            raise Exception("String not allowed")


das.register_mixins(SomeTypeValidator)
