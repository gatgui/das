import das

class SomeTypeValidator(das.Mixin):
   @classmethod
   def get_schema_type(klass):
      return "validation.SomeType"

   def __init__(self, *args, **kwargs):
      super(SomeTypeValidator, self).__init__(*args, **kwargs)

   def _schema_validation(self):
      for k in self.value_pairs.keys():
         if not k in self.valid_keys:
            raise Exception("Invalid key '%s'" % k)


das.register_mixins(SomeTypeValidator)
