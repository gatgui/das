import re

_opening_chars = "([{"
_closing_chars = ")]}"
_subscript_expr = re.compile(r"^(.*)\[([^]]+)\]$")
# 'set' and 'eval' functions are defined below so keep a reference to python's 'set' class
_pyset = set
_pyeval = eval

def _merge(field_parts):
   i = 0
   n = len(field_parts)
   o = []
   while i < n:
      part = field_parts[i]
      if part:
         opencnt = 0
         for c in _opening_chars:
            opencnt += part.count(c)
         for c in _closing_chars:
            opencnt -= part.count(c)
         while opencnt != 0:
            i += 1
            if i >= n:
               raise Exception("Unbalanced parenthesis or brackets")
            npart = field_parts[i]
            part += "." + npart
            for c in _opening_chars:
               opencnt += npart.count(c)
            for c in _closing_chars:
               opencnt -= npart.count(c)
         o.append(part)
      i += 1
   return o

def _generic_do(data, key, val=None, attrfunc=None, subscriptfunc=None):
   field = data

   parts = _merge(key.split("."))
   nparts = len(parts)

   novalue = (val is None)
   value = None
   if not novalue:
      novalue = False
      try:
         value = _pyeval(val)
      except Exception, e:
         raise Exception("Invalid value %s: %s\n" % (val, e))

   if not novalue and (attrfunc is None or subscriptfunc is None):
      raise Exception("'attrfunc' and 'subscriptfunc' functions must be provided")

   retval = None

   for i in xrange(nparts):
      part = parts[i]
      if not part:
         continue

      last = (i + 1 == nparts)

      m = _subscript_expr.match(part)

      if m is None:
         if last and attrfunc:
            if novalue:
               retval = attrfunc(field, part)
            else:
               retval = attrfunc(field, part, value)
         else:
            field = getattr(field, part)
            if last:
               retval = field

      else:
         subscripts = []
         while m is not None:
            subscripts.append(_pyeval(m.group(2)))
            part = m.group(1)
            m = _subscript_expr.match(part)
         subscripts.reverse()
         nsubscripts = len(subscripts)

         field = getattr(field, part)
         for j in xrange(nsubscripts):
            subscript = subscripts[j]
            lastsubscript = (j + 1 == nsubscripts)
            if lastsubscript and subscriptfunc:
               if novalue:
                  retval = subscriptfunc(field, subscript)
               else:
                  retval = subscriptfunc(field, subscript, value)
            else: 
               field = field[subscript]
               if lastsubscript:
                  retval = field

   return (field if len(parts) == 0 else retval)

def _attr_set(data, attr, value):
   setattr(data, attr, value)

def _subscript_set(data, index, value):
   data[index] = value

def _any_add(data, value):
   if isinstance(data, list):
      data.append(value)
   elif isinstance(data, _pyset):
      data.add(value)
   else:
      raise Exception("Cannot add value to %s" % type(data).__name__)

def _attr_add(data, attr, value):
   _any_add(getattr(data, attr), value)

def _subscript_add(data, index, value):
   _any_add(data[index], value)

def _attr_remove(data, attr):
   delattr(data, attr)

def _subscript_remove(data, index):
   del(data[index])

# ---

# 'key', 'value' and 'expr' parameter are strings

def set(data, key, value):
   _generic_do(data, key, value, attrfunc=_attr_set, subscriptfunc=_subscript_set)

def add(data, key, value):
   _generic_do(data, key, value, attrfunc=_attr_add, subscriptfunc=_subscript_add)

def remove(data, key):
   _generic_do(data, key, attrfunc=_attr_remove, subscriptfunc=_subscript_remove)

def get(data, key):
   return _generic_do(data, key)

def eval(data, expr):
   return _pyeval(ee, globals(), {"data": data})
