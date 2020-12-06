import das
from . import schematypes
import das


def get_schema_type(st):
   if isinstance(st, basestring):
      st = das.get_schema_type(st)
   if not isinstance(st, schematypes.TypeValidator):
      raise Exception("Expected a string or a das.schema.TypeValidator instance")

   stn = das.get_schema_type_name(st)
   if not stn:
      return st.diff_type()
   else:
      stn += ".diff"
      dst = das.get_schema_type(stn)
      if dst:
         return dst
      else:
         dst = st.diff_type()
         das.add_schema_type(stn, dst)
      return dst


def diff(base, other):
   st0 = base._get_schema_type()
   st1 = other._get_schema_type()
   if st0 != st1:
      raise Exception("Cannot diff value of deferring schema type")
   dst = get_schema_type(st0)
   dv = dst.make_default()
   return st0.diff(dst, dv, base, other)


def patch(value, diff):
   pass
