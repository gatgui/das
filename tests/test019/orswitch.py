import das # pylint: disable=import-error
import math

class Test(das.Mixin):
   @classmethod
   def get_schema_type(klass):
      return "orswitch.Test"

   def __init__(self, *args, **kwargs):
      super(Test, self).__init__(*args, **kwargs)

   def set_margin(self, name, scale=None, resolution=None):
      if scale and resolution:
         try:
            wscl, hscl = scale
            wres, hres = resolution
            if math.fabs(self.resolution.base[0] * wscl - wres) > 1.0:
               raise Exception("Width scale and resolution mismatch (more than 1 pixel difference)")
            if math.fabs(self.resolution.base[1] * hscl - hres) > 1.0:
               raise Exception("Height scale and resolution mismatch (more than 1 pixel difference)")
            self.resolution.margins[name] = (wscl, hscl)
            return True
         except:
            return False
      elif scale:
         try:
            self.resolution.margins[name] = scale
            return True
         except:
            return False
      elif resolution:
         try:
            wres, hres = resolution
            wscl = float(wres) / self.resolution.base[0]
            hscl = float(hres) / self.resolution.base[1]
            self.resolution.margins[name] = (wscl, hscl)
            return True
         except:
            return False
      else:
         return False

   def list_margins(self):
      return self.resolution.margins.keys()

   def get_margin(self, name):
      return self.resolution.margins.get(name, (1.0, 1.0))

   def get_default_margin(self):
      return self.resolution.margin

   def get_resolution(self, margin=None):
      if margin is None:
         margin = self.get_default_margin()
      wscl, hscl = self.get_margin(margin)
      wres = int(math.floor(0.5 + self.resolution.base[0] * wscl))
      hres = int(math.floor(0.5 + self.resolution.base[1] * hscl))
      return (wres, hres)

   def _validate_globally(self):
      # Transfer old data to new
      with das.GlobalValidationDisabled(self):
         # Resolution & Margins
         if das.check(self.resolution, "orswitch.Resolution"): # pylint: disable=access-member-before-definition
            self.resolution = self._get_schema_type()["resolution"].make(base=self.resolution)

         hasResolutionsWithMargins = hasattr(self, "resolutionsWithMargins")
         hasMarginPresets = hasattr(self, "marginPresets")

         if hasResolutionsWithMargins:
            for name, res in self.resolutionsWithMargins.iteritems():
               scl = None
               if hasMarginPresets and name in self.marginPresets:
                  scl = self.marginPresets[name]
               self.set_margin(name, resolution=res, scale=scl)

         if hasMarginPresets:
            for name, scl in self.marginPresets.iteritems():
               if hasResolutionsWithMargins and name in self.resolutionsWithMargins:
                  continue
               self.set_margin(name, scale=scl)
            del(self.marginPresets)

         if hasResolutionsWithMargins:
            del(self.resolutionsWithMargins)

         if hasattr(self, "defaultMargin"):
            self.resolution.defaultMargin = self.defaultMargin
            del(self.defaultMargin)

      # Validate margin names
      if self.resolution.defaultMargin and not self.resolution.defaultMargin in self.resolution.margins:
         raise Exception("Invalid default margin '%s'. Must be one of %s" % (self.resolution.defaultMargin, ", ".join(map(repr, self.resolution.margins.keys()))))


das.register_mixins(Test)
