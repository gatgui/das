import das
import math


class Resolution(das.Mixin):
   @classmethod
   def get_schema_type(klass):
      return "inherit.Resolution"

   def __init__(self, *args, **kwargs):
      super(Resolution, self).__init__(*args, **kwargs)

   def pixel_count(self):
      return self.width * self.height


class Scale(das.Mixin):
   @classmethod
   def get_schema_type(klass):
      return "inherit.Scale"

   def __init__(self, *args, **kwargs):
      super(Scale, self).__init__(*args, **kwargs)

   def is_uniform(self):
      return (math.fabs(self.x - self.y) < 0.000001)


das.register_mixins(Resolution, Scale)
