import das
import re
import fnmatch
import math

NoUI = False

try:
   import Qt
   from Qt import QtCore
   from Qt import QtGui
   from Qt import QtWidgets
   from Qt import QtCompat
except Exception, e:
   print("Failed to import Qt (%s)" % e)
   NoUI = True


if not NoUI:
   def IsPySide2():
      if hasattr(Qt, "__version_info__"):
         return Qt.__version_info__[0] >= 2
      if hasattr(Qt, "IsPySide2"):
         return Qt.IsPySide2
      return False


   class FieldFilter(object):
      def __init__(self, name):
         super(FieldFilter, self).__init__()
         self.name = name

      def copy(self):
         raise Exception("Not implemented")

      def matches(self, fullname):
         raise Exception("Not implemented")

   class GlobFilter(FieldFilter):
      def __init__(self, name, pattern, invert=False):
         super(GlobFilter, self).__init__(name)
         self.pattern = pattern
         self.invert = invert

      def copy(self):
         return GlobFilter(self.name, self.pattern, self.invert)

      def matches(self, fullname):
         rv = fnmatch.fnmatch(fullname, self.pattern)
         return ((not rv) if self.invert else rv)

   class RegexFilter(FieldFilter):
      def __init__(self, name, pattern, partial=False, invert=False):
         super(RegexFilter, self).__init__(name)
         self.regex = re.compile(pattern)
         self.partial = partial
         self.invert = invert

      def copy(self):
         return RegexFilter(self.name, self.regex.pattern, self.partial, self.invert)

      def matches(self, fullname):
         if self.partial:
            rv = (self.regex.search(fullname) is not None)
         else:
            rv = (self.regex.match(fullname) is not None)
         return ((not rv) if self.invert else rv)

   class ListFilter(FieldFilter):
      def __init__(self, name, values, partial=False, invert=False):
         super(ListFilter, self).__init__(name)
         self.values = set(map(str, values))
         self.partial = partial
         self.invert = invert

      def copy(self):
         return ListFilter(self.name, self.values, self.partial, self.invert)

      def matches(self, fullname):
         if self.partial:
            rv = True
            for item in self.allowed:
               if item in fullname:
                  rv = False
                  break
         else:
            rv = (fullname in self.allowed)
         return ((not rv) if self.invert else rv)

   class FilterSet(FieldFilter):
      All = 0
      Any = 1

      def __init__(self, name, mode, invert=False):
         super(FilterSet, self).__init__(name)
         self.filters = []
         if mode != self.All and mode != self.Any:
            raise Exception("[das] Invalid FilterSet mode: %d" % mode)
         self.mode = mode
         self.invert = invert

      def copy(self):
         rv = FilterSet(self.name, self.mode, self.invert)
         rv.filters = map(lambda x: x.copy(), self.filters)
         return rv

      def matches(self, fullname):
         if self.mode == self.All:
            rv = True
            for f in self.filters:
               if not f.matches(fullname):
                  rv = False
                  break
         else:
            rv = False
            for f in self.filters:
               if f.matches(fullname):
                  rv = True
                  break
         return ((not rv) if self.invert else rv)

      def add(self, flt, force=False):
         for i in xrange(len(self.filters)):
            if flt.name == self.filters[i].name:
               if force:
                  self.filters[i] = flt.copy()
                  return True
               else:
                  return False
         self.filters.append(flt.copy())
         return True

      def count(self):
         return len(self.filters)

      def at(self, idx):
         return self.filters[idx]

      def get(self, name):
         for f in self.filters:
            if f.name == name:
               return f
         return None

      def clear(self):
         self.filters = []

      def remove(self, idxOrName):
         if isisnstance(idxOrName, basestring):
            idx = -1
            for i in xrange(len(self.filters)):
               if idxOrName == self.filters[i].name:
                  idx = i
                  break
            if idx != -1:
               del(self.filters[idx])
               return True
            else:
               return False
         else:
            try:
               del(self.filters[idxOrName])
               return True
            except:
               return False


   class ModelItem(object):
      ReservedTypeNames = set(["alias", "empty", "boolean", "integer", "real", "string", "list", "tuple", "set", "dict", "struct"])

      def __init__(self, name, row=0, key=None, parent=None):
         super(ModelItem, self).__init__()
         self.row = row
         self.key = key
         self.name = name
         self.parent = parent

      def __str__(self):
         return "ModelItem(%s, compound=%s, resizable=%s, multi=%s, editable=%s, optional=%s, parent=%s, children=%d)" % (self.name, self.compound, self.resizable, self.multi, self.editable, self.optional, ("None" if not self.parent else self.parent.name), len(self.children))

      def fullname(self, skipRoot=False):
         k = ""
         item = self
         while item:
            if skipRoot and not item.parent:
               break
            suffix = ("" if not k else (".%s" % k))
            k = item.name + suffix
            item = item.parent
         return k

      def get_description(self, typ):
         desc = typ.description
         while not desc:
            if isinstance(typ, das.schematypes.SchemaType):
               typ = das.get_schema_type(typ.name)
            elif isinstance(typ, das.schematypes.Or):
               if len(typ.types) == 1:
                  typ = typ.types[0]
               else:
                  break
            elif isinstance(typ, das.schematypes.Optional):
               typ = typ.type
            else:
               break
            desc = typ.description
         return desc

      def real_type(self, typ):
         while True:
            if isinstance(typ, das.schematypes.SchemaType):
               typ = das.get_schema_type(typ.name)
            elif isinstance(typ, das.schematypes.Or):
               if len(typ.types) == 1:
                  typ = typ.types[0]
               else:
                  break
            elif isinstance(typ, das.schematypes.Optional):
               typ = typ.type
            else:
               break
         return typ

      def is_compound(self, t):
         if isinstance(self.real_type(t), (das.schematypes.Tuple,
                                           das.schematypes.Sequence,
                                           das.schematypes.Set,
                                           das.schematypes.Struct,
                                           das.schematypes.StaticDict,
                                           das.schematypes.Dict,
                                           das.schematypes.DynamicDict)):
            return True
         else:
            return False

      def is_editable(self, t):
         rt = self.real_type(t)
         if self.is_compound(rt):
            return False
         else:
            if isinstance(rt, das.schematypes.Or):
               for ot in rt.types:
                  # Don't allow more that one depth of Or
                  if isinstance(self.real_type(ot), das.schematypes.Or):
                     return False
                  # All possible types for a Or must be editable
                  if not self.is_editable(ot):
                     return False
            elif isinstance(rt, das.schematypes.Class):
               return (hasattr(rt.klass, "string_to_value") and hasattr(rt.klass, "value_to_string"))
            elif isinstance(rt, das.schematypes.Alias):
               return False
            return True

      def class_name(self, klass):
         cn = self.data.__class__.__name__
         mn = self.data.__class__.__module__
         if mn not in ("__builtin__", "__main__"):
            cn = mn + "." + cn
         if cn in self.ReservedTypeNames:
            cn += " (user)"
         # convert das.types.SomeType to someType
         if cn.startswith("das.types."):
            cn = cn[10].lower() + cn[11:]
         return cn

      def update_multi_type_string(self):
         if self.multi:
            if self.data is None:
               self.typestr = "empty"
            elif isinstance(self.data, bool):
               self.typestr = "boolean"
            elif isinstance(self.data, (int, long)):
               self.typestr = "integer"
            elif isinstance(self.data, float):
               self.typestr = "real"
            elif isinstance(self.data, basestring):
               self.typestr = "string"
            else:
               self.typestr = self.class_name(self.data.__class__)

      def multi_string(self):
         if self.data is None or isinstance(self.data, bool):
            return str(self.data).lower()
         else:
            return str(self.data)

      def get_valid_types(self, **kwargs):
         values = []

         if not self.multi:
            return values

         s = kwargs.get("string", self.multi_string())

         for t in self.type.types:
            if isinstance(t, das.schematypes.SchemaType):
               t = das.get_schema_type(t.name)
            if isinstance(t, das.schematypes.Empty):
               if s.lower() == "none":
                  values.append(("empty", None))
            elif isinstance(t, das.schematypes.Boolean):
               if s.lower() in ("on", "yes", "true", "off", "no", "false"):
                  v = (s.lower() in ("on", "yes", "true"))
                  values.append(("boolean", v))
            elif isinstance(t, das.schematypes.Integer):
               try:
                  v = long(s)
                  t._validate_self(v)
                  values.append(("integer", v))
               except:
                  pass
            elif isinstance(t, das.schematypes.Real):
               try:
                  v = float(s)
                  t._validate_self(v)
                  values.append(("real", v))
               except:
                  pass
            elif isinstance(t, das.schematypes.String):
               try:
                  t._validate_self(s)
                  values.append(("string", s))
               except:
                  pass
            elif isinstance(t, das.schematypes.Class):
               try:
                  v = t.make_default()
                  v.string_to_value(s)
                  t._validate_self(v)
                  values.append((self.class_name(t.klass), v))
               except:
                  pass

         return values

      def exists(self):
         if self.typestr != "alias":
            if self.parent and self.parent.mapping and self.parent.mappingkeytype is None:
               return (True if not self.optional else (self.key in self.parent.data))
            else:
               return True
         else:
            return False

      def update(self, data, type=None, hideDeprecated=True, hideAliases=True, showHidden=False, fieldFilters=None):
         self.children = []
         self.compound = False
         self.mapping = False
         self.mappingkeys = None
         self.mappingkeytype = None
         self.uniformmapping = True # mapping of uniform type values
         self.resizable = False
         self.orderable = False # orderable compound
         self.optional = False
         self.deprecated = False
         self.editable = False # will be false for aliases
         self.editableType = True # is value tagged as editable in the schema type
         self.editableValue = True # is value actually editable in the UI
         self.multi = False
         self.data = data # for alias, it is the same data as the original
         self.type = type
         self.baseType = None
         self.typestr = ""
         self.desc = ""

         if self.type is None and self.data is not None:
            self.type = self.data._get_schema_type()
            if self.type is None:
               raise Exception("No schema type for model item")

         self.baseType = self.type

         if isinstance(self.type, das.schematypes.Alias):
            # Shortcut
            self.typestr = "alias"
            self.data = None
            if fieldFilters and not fieldFilters.matches(self.fullname(skipRoot=True)):
               return False
            else:
               return True

         # initialize those two with original type
         self.editableType = self.type.editable
         self.desc = self.get_description(self.type)

         self.optional = isinstance(self.type, das.schematypes.Optional)
         self.deprecated = isinstance(self.type, das.schematypes.Deprecated)

         self.type = self.real_type(self.type)

         # # override description using used type
         # if not self.desc:
         #    self.desc = self.type.description

         self.multi = isinstance(self.type, das.schematypes.Or)

         # if originally editable, check that type value can effectively be edited
         self.editableValue = self.is_editable(self.type)
         self.editable = (self.editableType and self.editableValue)

         self.compound = self.is_compound(self.type)

         if not self.compound:
            if self.multi:
               self.update_multi_type_string()
               # Try to figure actual datatype. If it is a compound, built matching item tree
               for typ in self.type.types:
                  if das.check(data, typ):
                     if isinstance(data, (das.types.Sequence, das.types.Tuple, das.types.Set, das.types.Struct, das.types.Dict)):
                        self.multi = False
                        self.compound = True
                        self.desc = self.get_description(typ)
                        self.type = self.real_type(typ)
                        self.editableType = self.type.editable
                        self.editableValue = self.is_editable(self.type)
                        self.editable = (self.editableType and self.editableValue)
                        # if not self.desc:
                        #    self.desc = self.type.description
                     break

            else:
               if isinstance(self.type, das.schematypes.Boolean):
                  self.typestr = "boolean"
               elif isinstance(self.type, das.schematypes.Integer):
                  self.typestr = "integer"
               elif isinstance(self.type, das.schematypes.Real):
                  self.typestr = "real"
               elif isinstance(self.type, das.schematypes.String):
                  self.typestr = "string"
               elif isinstance(self.type, das.schematypes.Empty):
                  self.typestr = "empty"
               elif isinstance(self.type, das.schematypes.Class):
                  self.typestr = self.class_name(self.type.klass)
               elif isinstance(self.type, das.schematypes.Alias):
                  self.typestr = "alias"

         if self.compound:
            if isinstance(self.type, das.schematypes.Sequence):
               self.typestr = "list"
               self.resizable = True
               self.orderable = True
               if self.exists():
                  for i in xrange(len(self.data)):
                     itemname = "[%d]" % i
                     itemdata = self.data[i]
                     newitem = ModelItem(itemname, row=i, parent=self)
                     if newitem.update(itemdata, type=self.type.type, hideDeprecated=hideDeprecated, hideAliases=hideAliases, showHidden=showHidden, fieldFilters=fieldFilters):
                        self.children.append(newitem)

            elif isinstance(self.type, das.schematypes.Tuple):
               self.typestr = "tuple"
               self.resizable = False
               self.orderable = True
               if self.exists():
                  for i in xrange(len(self.data)):
                     itemname = "(%d)" % i
                     itemdata = self.data[i]
                     newitem = ModelItem(itemname, row=i, parent=self)
                     if newitem.update(itemdata, type=self.type.types[i], hideDeprecated=hideDeprecated, hideAliases=hideAliases, showHidden=showHidden, fieldFilters=fieldFilters):
                        self.children.append(newitem)

            elif isinstance(self.type, das.schematypes.Set):
               self.typestr = "set"
               self.resizable = True
               self.orderable = False
               if self.exists():
                  i = 0
                  for itemdata in self.data:
                     itemname = "{%d}" % i
                     newitem = ModelItem(itemname, row=i, parent=self)
                     if newitem.update(itemdata, type=self.type.type, hideDeprecated=hideDeprecated, hideAliases=hideAliases, showHidden=showHidden, fieldFilters=fieldFilters):
                        self.children.append(newitem)
                     i += 1

            elif isinstance(self.type, (das.schematypes.Struct, das.schematypes.StaticDict)):
               self.typestr = "struct"
               self.resizable = False
               self.orderable = False
               self.mapping = True
               self.mappingkeys = {}
               self.uniformmapping = False
               i = 0
               for k in sorted(self.type.keys()):
                  t = self.type[k]
                  optional = isinstance(t, das.schematypes.Optional)
                  self.mappingkeys[k] = optional
                  if optional:
                     self.resizable = True
                  if self.exists() and (showHidden or not t.hidden):
                     if isinstance(t, das.schematypes.Alias):
                        if hideAliases:
                           continue
                        v = None
                     elif not k in self.data:
                        if hideDeprecated and isinstance(t, das.schematypes.Deprecated):
                           continue
                        v = t.make_default()
                     else:
                        v = self.data[k]
                     newitem = ModelItem(k, row=i, key=k, parent=self)
                     if newitem.update(v, type=t, hideDeprecated=hideDeprecated, hideAliases=hideAliases, showHidden=showHidden, fieldFilters=fieldFilters):
                        self.children.append(newitem)
                  i += 1

            elif isinstance(self.type, (das.schematypes.Dict, das.schematypes.DynamicDict)):
               self.typestr = "dict"
               self.resizable = True
               self.orderable = False
               self.mapping = True
               self.mappingkeytype = self.type.ktype
               self.uniformmapping = (len(self.type.vtypeOverrides) == 0)
               if self.exists():
                  i = 0
                  dkeys = [x for x in self.data.iterkeys()]
                  for k in sorted(dkeys):
                     if isinstance(k, basestring):
                        itemname = k
                     elif hasattr(k, "value_to_string"):
                        itemname = k.value_to_string()
                     else:
                        itemname = str(k)
                     v = self.data[k]
                     vtype = self.type.vtypeOverrides.get(k, self.type.vtype)
                     newitem = ModelItem(itemname, row=i, key=k, parent=self)
                     if newitem.update(v, type=vtype, hideDeprecated=hideDeprecated, hideAliases=hideAliases, showHidden=showHidden, fieldFilters=fieldFilters):
                        self.children.append(newitem)
                     i += 1

            # Never filter out root item, even when all its children are gone
            if self.parent is None:
               return True
            else:
               if len(self.children) > 0:
                  return True
               else:
                  if fieldFilters and not fieldFilters.matches(self.fullname(skipRoot=True)):
                     return False
                  else:
                     return True
         else:
            if fieldFilters and not fieldFilters.matches(self.fullname(skipRoot=True)):
               return False
            else:
               return True


   class NewValueDialog(QtWidgets.QDialog):
      def __init__(self, vtype, excludes=None, name=None, parent=None):
         super(NewValueDialog, self).__init__(parent, QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowSystemMenuHint)
         self.setWindowTitle("Create new value")
         self.excludes = excludes
         self.data = vtype.make_default()
         self.editor = Editor(self.data, type=vtype, name=name, headers=[], parent=self)
         layout = QtWidgets.QVBoxLayout()
         self.okbtn = QtWidgets.QPushButton("Ok", self)
         self.okbtn.setEnabled(True if excludes is None else (self.data not in self.excludes))
         cancelbtn = QtWidgets.QPushButton("Cancel", self)
         btnl = QtWidgets.QHBoxLayout()
         btnl.addWidget(self.okbtn, 1)
         btnl.addWidget(cancelbtn, 1)
         layout.addWidget(self.editor, 1)
         layout.addLayout(btnl, 0)
         self.setLayout(layout)
         # Wire callbacks
         self.editor.modelUpdated.connect(self.onDataChanged)
         self.okbtn.clicked.connect(self.accept)
         cancelbtn.clicked.connect(self.reject)
         self.resize(400, 200)

      def onDataChanged(self, model):
         self.data = model.getData()
         if self.excludes is not None and self.data in self.excludes:
            self.data = None
         self.okbtn.setEnabled(self.data is not None)

      def accept(self):
         super(NewValueDialog, self).accept()

      def reject(self):
         self.data = None
         super(NewValueDialog, self).reject()


   class FieldSlider(QtWidgets.QFrame):
      # (value, invalid, errmsg)
      realValueChanged = QtCore.Signal(float, bool, str)
      intValueChanged = QtCore.Signal(int, bool, str)

      def __init__(self, vmin, vmax, real=False, decimal=1, parent=None):
         super(FieldSlider, self).__init__(parent)
         self._value = None
         self.real = real
         self.scale = 1
         self.min = vmin
         self.max = vmax
         sldmin = int(vmin)
         sldmax = int(vmax)
         if self.real:
            self.scale = math.pow(10, decimal)
            sldmin = int(math.ceil(self.min * self.scale))
            sldmax = int(math.floor(self.max * self.scale))
            if self.min < (sldmin / self.scale) or (sldmax / self.scale) < self.max:
               print("[das] Not enough precision in slider (%d decimal(s)) for value range [%f, %f]" % (decimal, self.min, self.max))
         self.fld = QtWidgets.QLineEdit(self)
         self.fld.setObjectName("field")
         self.sld = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
         self.sld.setObjectName("slider")
         self.sld.setTracking(True)
         self.sld.setMinimum(sldmin)
         self.sld.setMaximum(sldmax)
         lay = QtWidgets.QHBoxLayout()
         lay.setContentsMargins(0, 0, 0, 0)
         lay.setSpacing(2)
         lay.addWidget(self.fld, 0)
         lay.addWidget(self.sld, 1)
         self.setLayout(lay)
         self.sld.valueChanged.connect(self.sliderChanged)
         self.fld.textChanged.connect(self.textChanged)
         self.valueChanged = (self.realValueChanged if self.real else self.intValueChanged)

      def focusInEvent(self, event):
         if event.gotFocus():
            self.fld.setFocus(event.reason())
            self.fld.selectAll()
            event.accept()

      def _setValue(self, val, updateField=True, updateSlider=True):
         self._value = (float(val) if self.real else int(val))
         if self._value < self.min:
            self._value = self.min
            updateField = True
            updateSlider = True
         elif self._value > self.max:
            self._value = self.max
            updateField = True
            updateSlider = True
         if updateField:
            self.fld.blockSignals(True)
            self.fld.setText(str(self._value))
            self.fld.blockSignals(False)
         if updateSlider:
            self.sld.blockSignals(True)
            if self.real:
               self.sld.setValue(int(math.floor(0.5 + self._value * self.scale)))
            else:
               self.sld.setValue(self._value)
            self.sld.blockSignals(False)

      def setValue(self, val):
         self._setValue(val, updateField=True, updateSlider=True)

      def value(self):
         return self._value

      def text(self):
         return str(self._value)

      def textChanged(self, txt):
         invalid = False
         errmsg = ""
         try:
            if self.real:
               val = float(txt)
            else:
               val = int(txt)
         except Exception, e:
            invalid = True
            errmsg = str(e)
            # if text is not empty, reset field to real value
            if txt:
               self.fld.blockSignals(True)
               self.fld.setText(str(self.value()))
               self.fld.blockSignals(False)
         else:
            self._setValue(val, updateField=False)

         self.valueChanged.emit(self.value(), invalid, errmsg)

      def sliderChanged(self, val):
         # as we round down slider min value and round up slider max value
         # we may need to adjust here
         self._setValue(val / self.scale, updateSlider=False)

         self.valueChanged.emit(self.value(), False, "")


   class ModelItemDelegate(QtWidgets.QItemDelegate):
      def __init__(self, parent=None):
         super(ModelItemDelegate, self).__init__(parent)

      def createEditor(self, parent, viewOptions, modelIndex):
         item = modelIndex.internalPointer()
         rv = None
         if modelIndex.column() == 0:
            if item.parent and item.parent.mapping and item.parent.mappingkeytype is not None:
               rv = self.createMappingKeyEditor(parent, item)
         elif modelIndex.column() == 1:
            if item.editable:
               if item.multi:
                  rv = self.createOrEditor(parent, item)
               else:
                  if isinstance(item.type, das.schematypes.Boolean):
                     rv = self.createBoolEditor(parent, item)
                  elif isinstance(item.type, das.schematypes.Integer):
                     rv = self.createIntEditor(parent, item)
                  elif isinstance(item.type, das.schematypes.Real):
                     rv = self.createFltEditor(parent, item)
                  elif isinstance(item.type, das.schematypes.String):
                     rv = self.createStrEditor(parent, item)
                  elif isinstance(item.type, das.schematypes.Class):
                     rv = self.createClassEditor(parent, item)
                  # Ignore 'Empty' and 'Alias'
         elif modelIndex.column() == 2:
            rv = self.createTypeEditor(parent, item)
         return rv

      def createTypeEditor(self, parent, item):
         tv = item.get_valid_types()
         tv.sort(key=lambda x: x[0])
         rv = QtWidgets.QComboBox(parent=parent)
         for typ, val in tv:
            rv.addItem(typ, userData=val)
         rv.setProperty("setEditorData", self.setTypeEditorData)
         rv.setProperty("setModelData", self.setTypeModelData)
         return rv

      def createMappingKeyEditor(self, parent, item):
         rv = QtWidgets.QLineEdit(parent)
         def textChanged(txt):
            # Convert text to a python value
            try:
               val = eval(txt)
            except:
               val = txt
            # Create a new key
            newkey = das.copy(item.key)
            try:
               newkey = val
            except Exception, e:
               rv.setProperty("invalidState", True)
               rv.setProperty("message", "Invalid key (%s)" % e)
            else:
               # Set the new key
               tmpdict = item.parent.type.make_default()
               tmpval = item.parent.type.vtype.make_default()
               try:
                  tmpdict[newkey] = tmpval
               except Exception, e:
                  rv.setProperty("invalidState", True)
                  rv.setProperty("message", "Invalid key (%s)" % e)
               else:
                  rv.setProperty("invalidState", False)
         rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setMappingKeyEditorData)
         rv.setProperty("setModelData", self.setMappingKeyModelData)
         return rv

      def createOrEditor(self, parent, item):
         rv = QtWidgets.QLineEdit(parent)
         def textChanged(txt):
            invalid = (len(item.get_valid_types(string=txt)) == 0)
            rv.setProperty("invalidState", invalid)
            if invalid:
               rv.setProperty("message", "'%s' doesn't match any supported types" % txt)
         rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setOrEditorData)
         rv.setProperty("setModelData", self.setOrModelData)
         return rv

      def createBoolEditor(self, parent, item):
         rv = QtWidgets.QCheckBox(parent)
         rv.setProperty("setEditorData", self.setBoolEditorData)
         rv.setProperty("setModelData", self.setBoolModelData)
         return rv

      def createIntEditor(self, parent, item):
         if item.type.enum is not None:
            rv = QtWidgets.QComboBox(parent)
            for k in sorted(item.type.enum.keys(), key=lambda x: item.type.enum[x]):
               v = item.type.enum[k]
               rv.addItem(k, userData=v)
         elif item.type.min is not None and item.type.max is not None:
            rv = FieldSlider(item.type.min, item.type.max, real=False, parent=parent)
            def valueChanged(val, invalid, errmsg):
               rv.setProperty("invalidState", invalid)
               if invalid:
                  rv.setProperty("message", errmsg)
            rv.intValueChanged.connect(valueChanged)
         else:
            rv = QtWidgets.QLineEdit(parent)
            def textChanged(txt):
               try:
                  int(txt)
               except Exception, e:
                  rv.setProperty("invalidState", True)
                  rv.setProperty("message", str(e))
                  # if text is not empty, reset to original value
                  if txt:
                     rv.setText(str(item.data))
               else:
                  rv.setProperty("invalidState", False)
            rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setIntEditorData)
         rv.setProperty("setModelData", self.setIntModelData)
         return rv

      def createFltEditor(self, parent, item):
         if item.type.min is not None and item.type.max is not None:
            rv = FieldSlider(item.type.min, item.type.max, real=True, decimal=4, parent=parent)
            def valueChanged(val, invalid, errmsg):
               rv.setProperty("invalidState", invalid)
               if invalid:
                  rv.setProperty("message", errmsg)
            rv.realValueChanged.connect(valueChanged)
         else:
            rv = QtWidgets.QLineEdit(parent)
            def textChanged(txt):
               try:
                  float(txt)
               except Exception, e:
                  rv.setProperty("invalidState", True)
                  rv.setProperty("message", str(e))
                  # if text is not empty, reset to original value
                  if txt:
                     rv.setText(str(item.data))
               else:
                  rv.setProperty("invalidState", False)
            rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setFltEditorData)
         rv.setProperty("setModelData", self.setFltModelData)
         return rv

      def createStrEditor(self, parent, item):
         if item.type.choices is not None:
            rv = QtWidgets.QComboBox(parent)
            rv.addItems(item.type.choices)
            rv.setEditable(not item.type.strict)
         else:
            rv = QtWidgets.QLineEdit(parent)
            def textChanged(txt):
               if item.type.matches is not None:
                  invalid = (not item.type.matches.match(txt))
                  rv.setProperty("invalidState", invalid)
                  if invalid:
                     rv.setProperty("message", "'%s' doesn't match '%s'" % (txt, item.type.matches.pattern))
               else:
                  rv.setProperty("invalidState", False)
            rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setStrEditorData)
         rv.setProperty("setModelData", self.setStrModelData)
         return rv

      def createClassEditor(self, parent, item):
         rv = QtWidgets.QLineEdit(parent)
         def textChanged(txt):
            try:
               item.data.copy().string_to_value(txt)
            except Exception, e:
               rv.setProperty("invalidState", True)
               rv.setProperty("message", str(e))
            else:
               rv.setProperty("invalidState", False)
         rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setClassEditorData)
         rv.setProperty("setModelData", self.setClassModelData)
         return rv

      def setEditorData(self, widget, modelIndex):
         item = modelIndex.internalPointer()
         func = widget.property("setEditorData")
         if func:
            func(widget, item)

      def setTypeEditorData(self, widget, item):
         widget.setCurrentIndex(widget.findText(item.typestr))

      def setMappingKeyEditorData(self, widget, item):
         if hasattr(item.key, "value_to_string"):
            widget.setText(item.key.value_to_string())
         else:
            widget.setText(str(item.key))

      def setOrEditorData(self, widget, item):
         if item.data is None or isinstance(item.data, bool):
            s = str(item.data).lower()
         else:
            s = str(item.data)
         widget.setText(s)

      def setBoolEditorData(self, widget, item):
         widget.setCheckState(QtCore.Qt.Checked if item.data else QtCore.Qt.Unchecked)

      def setIntEditorData(self, widget, item):
         if item.type.enum is not None:
            widget.setCurrentIndex(widget.findData(item.data))
         else:
            if item.type.min is not None and item.type.max is not None:
               widget.setValue(item.data)
            else:
               widget.setText(str(item.data))

      def setFltEditorData(self, widget, item):
         if item.type.min is not None and item.type.max is not None:
            widget.setValue(item.data)
         else:
            widget.setText(str(item.data))

      def setStrEditorData(self, widget, item):
         if item.type.choices is not None:
            if item.type.strict:
               widget.setCurrentIndex(widget.findText(item.data))
            else:
               idx = widget.findText(item.data)
               if idx == -1:
                  widget.setEditText(item.data)
               else:
                  widget.setCurrentIndex(idx)
         else:
            widget.setText(item.data)

      def setClassEditorData(self, widget, item):
         widget.setText(item.data.value_to_string())

      def setModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         invalid = widget.property("invalidState")
         if not invalid:
            func = widget.property("setModelData")
            if func:
               olddata = item.data
               if not func(widget, model, modelIndex):
                  # even if model.setData fails, UI still shows the
                  # invalid edited value until next refresh
                  msg = model.message()
                  model.disableUndo()
                  model.setData(modelIndex, olddata, QtCore.Qt.EditRole)
                  model.enableUndo()
                  model.setMessage(msg)
            else:
               model.setItemErrorMessage(item, "No 'setModelData' property set on editor widget")
         else:
            model.setItemErrorMessage(item, widget.property("message"))

      def setTypeModelData(self, widget, model, modelIndex):
         data = widget.itemData(widget.currentIndex())
         index = model.index(modelIndex.row(), 1, modelIndex.parent())
         return model.setData(index, data, QtCore.Qt.EditRole)

      def setMappingKeyModelData(self, widget, model, modelIndex):
         try:
            key = eval(widget.text())
         except:
            key = widget.text()
         item = modelIndex.internalPointer()
         if hasattr(item.key, "string_to_value"):
            tmp = key
            key = item.key.copy()
            key.string_to_value(tmp)
         return model.setData(modelIndex, key, QtCore.Qt.EditRole)

      def setOrModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()

         values = item.get_valid_types(string=widget.text())

         if len(values) >= 1:
            _, v = values[0]
            return model.setData(modelIndex, v, QtCore.Qt.EditRole)
         else:
            model.setItemErrorMessage(item, "Input doesn't match any supported types")
            return False

      def setBoolModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         data = (widget.checkState() == QtCore.Qt.Checked)
         return model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setIntModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.enum is not None:
            data = item.type.enum[widget.currentText()]
         else:
            if item.type.min is not None and item.type.max is not None:
               data = widget.value()
            else:
               data = long(widget.text())
         return model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setFltModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.min is not None and item.type.max is not None:
            data = widget.value()
         else:
            data = float(widget.text())
         return model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setStrModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.choices is not None:
            data = widget.currentText()
         else:
            data = widget.text()
         return model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setClassModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         data = item.data.copy()
         data.string_to_value(widget.text())
         return model.setData(modelIndex, data, QtCore.Qt.EditRole)


   class Model(QtCore.QAbstractItemModel):
      AllHeaders = ["Name", "Value", "Type", "Description"]
      OptionalHeaders = ["Type", "Description"]

      internallyRebuilt = QtCore.Signal()
      dataChanged2Args = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
      messageChanged = QtCore.Signal(str)

      def __init__(self, data, type=None, name=None, readonly=False, headers=None, fieldfilters=None, parent=None):
         super(Model, self).__init__(parent)
         # A little hacky but how else?
         if IsPySide2():
            self._org_data_changed = self.dataChanged
            self.dataChanged = self.dataChanged2Args
            self.dataChanged.connect(self.__emitDataChanged)
         if headers is None:
            self._headers = self.AllHeaders[:]
         else:
            hdrs = filter(lambda x: x in self.AllHeaders, headers)
            if not "Name" in hdrs:
               hdrs.insert(0, "Name")
            if not "Value" in hdrs:
               hdrs.insert(hdrs.index("Name") + 1, "Value")
            self._headers = hdrs
         self._rootItem = None
         self._orgData = None
         self._message = ""
         self._readonly = readonly
         self._undos = []
         self._curundo = -1
         self._noundo = False
         self._hideDeprecated = True
         self._hideAliases = True
         self._showHidden = False
         self._fieldFilters = (fieldfilters.copy() if fieldfilters is not None else None)
         self._buildItemsTree(data=data, type=type, name=name)

      def __emitDataChanged(self, index1, index2):
         self._org_data_changed.emit(index1, index2, [])

      def _buildItemsTree(self, data=None, type=None, name=None):
         if data is not None:
            self._orgData = das.copy(data)
         else:
            type = None
         if self._rootItem:
            if data is None:
               data = self._rootItem.data
               type = self._rootItem.type
            self._rootItem.update(data, type=type, hideDeprecated=self._hideDeprecated, hideAliases=self._hideAliases, showHidden=self._showHidden, fieldFilters=self._fieldFilters)
         elif data is not None:
            # self._rootItem = ModelItem("<root>" if name is None else name, data, type=type, hideDeprecated=self._hideDeprecated, hideAliases=self._hideAliases, showHidden=self._showHidden, fieldFilters=self._fieldFilters)
            self._rootItem = ModelItem("<root>" if name is None else name)
            self._rootItem.update(data, type=type, hideDeprecated=self._hideDeprecated, hideAliases=self._hideAliases, showHidden=self._showHidden, fieldFilters=self._fieldFilters)

      def hideDeprecated(self):
         return self._hideDeprecated

      def hideAliases(self):
         return self._hideAliases

      def showHidden(self):
         return self._showHidden

      def setHideDeprecated(self, on):
         if on != self._hideDeprecated:
            self._hideDeprecated = on
            self._updateData()

      def setHideAliases(self, on):
         if on != self._hideAliases:
            self._hideAliases = on
            self._updateData()

      def setShowHidden(self, on):
         if on != self._showHidden:
            self._showHidden = on
            self._updateData()

      def isColumnShown(self, name):
         return (name in self._headers)

      def setShowColumn(self, name, onoff):
         if not name in self.OptionalHeaders:
            return
         if onoff:
            if not name in self._headers:
               idx = self.AllHeaders.index(name)
               self.beginInsertColumns(QtCore.QModelIndex(), idx, idx)
               self._headers.insert(idx, name)
               self.endInsertColumns()
         else:
            if name in self._headers:
               idx = self._headers.index(name)
               self.beginRemoveColumns(QtCore.QModelIndex(), idx, idx)
               del(self._headers[idx])
               self.endRemoveColumns()

      def fieldFilters(self):
         return self._fieldFilters.copy()

      def setFieldFilters(self, filterSet):
         self._fieldFilters = filterSet.copy()
         self._updateData()

      def _updateData(self, data=None, type=None, name=None):
         self.beginResetModel()
         self._buildItemsTree(data=data, type=type, name=name)
         self.endResetModel()
         rootIndex = self.index(0, 0, QtCore.QModelIndex())
         self.dataChanged.emit(rootIndex, rootIndex)
         self.internallyRebuilt.emit()

      def getData(self):
         return (None if self._rootItem is None else self._rootItem.data)

      def replaceData(self, data, type=None, name=None):
         self._orgData = None
         self._rootItem = None
         self._undos = []
         self._curundo = -1
         self._updateData(data, type=type, name=name)

      def getIndexData(self, index):
         if index.isValid():
            item = index.internalPointer()
            return item.data
         else:
            return None

      def message(self):
         return self._message

      def setMessage(self, msg):
         self._message = msg
         self.messageChanged.emit(msg)

      def setItemErrorMessage(self, item, msg):
         if msg:
            n = item.fullname(skipRoot=True)
            if not n:
               n = item.fullname()
            self.setMessage("Failed to update '%s'.\n%s" % (n, msg))
         else:
            self.setMessage("")

      def hasDataChanged(self):
         return (False if self._rootItem is None else (self._rootItem.data != self._orgData))

      def cleanData(self):
         if self._rootItem:
            self._orgData = das.copy(self._rootItem.data)

      def canUndo(self):
         return (len(self._undos) > 0 and self._curundo >= 0)

      def canRedo(self):
         return (len(self._undos) > 0 and self._curundo + 1 < len(self._undos))

      def undo(self):
         if not self.canUndo():
            return False
         else:
            self._rootItem.data = das.copy(self._undos[self._curundo][0])
            self._updateData()
            self._curundo -= 1
            return True

      def redo(self):
         if not self.canRedo():
            return False
         else:
            self._curundo += 1
            self._rootItem.data = das.copy(self._undos[self._curundo][1])
            self._updateData()
            return True

      def pushUndo(self, undoData):
         if self._noundo:
            return
         if self._rootItem and undoData is not None:
            curData = das.copy(self.getData())
            if curData != undoData:
               self._undos = self._undos[:self._curundo + 1]
               self._undos.append((undoData, curData))
               self._curundo = len(self._undos) - 1

      def enableUndo(self):
         self._noundo = False

      def disableUndo(self):
         self._noundo = True

      def clearUndos(self):
         self._undos = []
         self._curundo = -1

      def findIndex(self, s, addRoot=False):
         if not s:
            if addRoot:
               return self._rootItem
            else:
               return None
         spl = s.split(".")
         if addRoot and self._rootItem:
            spl.insert(0, self._rootItem.name)
         cnt = len(spl)
         idx = 0
         parentIndex = QtCore.QModelIndex()
         curKey = ""
         while idx < len(spl):
            curKey = curKey + ("." if curKey else "") + spl[idx]
            nr = self.rowCount(parentIndex)
            for r in xrange(nr):
               index = self.index(r, 0, parentIndex)
               if index.isValid():
                  item = index.internalPointer()
                  if item.name == curKey:
                     parentIndex = index
                     curKey = ""
                     break
            # may want to strip root name?
            idx += 1
         if curKey:
            # print("Can't find index for '%s'" % s)
            return None
         else:
            return parentIndex

      def rebuild(self):
         self.beginResetModel()
         self._buildItemsTree()
         self.endResetModel()

      def _checkIndex(self, index):
         if not index.isValid():
            return False
         col = index.column()
         if col < 0 or col >= len(self._headers):
            return False
         ptr = index.internalPointer()
         if not ptr:
            return False
         return True

      def flags(self, index):
         if not self._checkIndex(index):
            return QtCore.Qt.NoItemFlags
         else:
            flags = QtCore.Qt.ItemIsSelectable
            item = index.internalPointer()

            if not self._readonly:
               if item.parent and not item.parent.mapping and item.parent.orderable:
                  flags = flags | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

               if item.compound  and not item.mapping and item.orderable:
                  flags = flags | QtCore.Qt.ItemIsDropEnabled

            if self._headers[index.column()] == "Name":
               if item.exists():
                  flags = flags | QtCore.Qt.ItemIsEnabled
               # flags = flags | QtCore.Qt.ItemIsUserCheckable
               if not self._readonly:
                  if item.parent:
                     if item.parent.mapping and item.parent.mappingkeytype is not None:
                        flags = flags | QtCore.Qt.ItemIsEditable

            elif self._headers[index.column()] == "Value":
               if not self._readonly:
                  if item.exists() and not item.compound and item.editableType:
                     flags = flags | QtCore.Qt.ItemIsEnabled
                  # any other cases?
                  if item.editable:
                     flags = flags | QtCore.Qt.ItemIsEditable

            elif self._headers[index.column()] == "Type":
               if not self._readonly:
                  if item.editable and item.multi and len(item.get_valid_types()) > 1:
                     flags = flags | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

            elif self._headers[index.column()] == "Description":
               if not self._readonly:
                  if item.exists():
                     flags = flags | QtCore.Qt.ItemIsEnabled

            return flags

      def headerData(self, index, orient, role):
         if orient == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._headers[index]
         else:
            return None

      def hasChildren(self, index):
         if not index.isValid():
            rv = (True if self._rootItem is not None else False)
         else:
            item = index.internalPointer()
            rv = (len(item.children) > 0)
         return rv

      def parent(self, index):
         if not index.isValid():
            return QtCore.QModelIndex()
         else:
            item = index.internalPointer()
            if item is None or not hasattr(item, "parent"):
               return QtCore.QModelIndex()
            if item.parent is None:
               return QtCore.QModelIndex()
            else:
               return self.createIndex(item.parent.row, 0, item.parent)

      def index(self, row, col, parentIndex):
         if not parentIndex.isValid():
            if row != 0:
               return QtCore.QModelIndex()
            else:
               return self.createIndex(row, col, self._rootItem)
         else:
            item = parentIndex.internalPointer()
            if row < 0 or row >= len(item.children):
               return QtCore.QModelIndex()
            else:
               return self.createIndex(row, col, item.children[row])

      def data(self, index, role):
         if not self._checkIndex(index):
            return None

         item = index.internalPointer()

         if role == QtCore.Qt.DecorationRole:
            # No icons
            return None

         elif role == QtCore.Qt.CheckStateRole:
            # No check boxes
            # If want some: return QtCore.Qt.Checked or QtCore.Qt.Unchecked
            return None

         elif role == QtCore.Qt.FontRole:
            if item.optional and self._headers[index.column()] == "Name":
               font = QtGui.QFont()
               font.setStyle(QtGui.QFont.StyleItalic)
               if item.exists():
                  font.setWeight(90)
               return font
            else:
               return None

         elif not role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return None

         rv = None

         if self._headers[index.column()] == "Name":
            rv = item.name

         elif self._headers[index.column()] == "Value":
            if item.typestr == "alias":
               rv = "= " + item.type.name

            elif not item.compound:
               if role == QtCore.Qt.DisplayRole:
                  #if not item.editable:
                  if not item.editableValue:
                     rv = "---"
                  #elif isinstance(item.type, das.schematypes.Class):
                  elif hasattr(item.data, "value_to_string"):
                     rv = item.data.value_to_string()
                  else:
                     if isinstance(item.type, das.schematypes.Integer) and item.type.enum is not None:
                        for k, v in item.type.enum.iteritems():
                           if v == item.data:
                              rv = k
                              break
                        # just for safety
                        if rv is None:
                           rv = str(item.data)
                     else:
                        rv = str(item.data)
                        if isinstance(item.data, (bool, type(None))):
                           rv = rv.lower()
               else:
                  rv = item.data
            else:
               rv = "---"

         elif self._headers[index.column()] == "Type":
            rv = item.typestr

         elif self._headers[index.column()] == "Description":
            rv = item.desc

         if role == QtCore.Qt.DisplayRole and self._headers[index.column()] == "Value":
            rv = "    " + rv

         return rv

      def _setRawData(self, index, value, pushUndo=True):
         structureChanged = False
         item = index.internalPointer()

         undoData = (das.copy(self.getData()) if pushUndo else None)

         oldvalue = item.data
         # The following statement may fails because of validation
         item.data = value
         item.update_multi_type_string()
         self.setMessage("")
         # Check whether we need to replace data reference in parent item, if any
         if item.parent is not None:
            if item.parent.mapping:
               item.parent.data[item.key] = item.data
            elif item.parent.resizable:
               if isinstance(item.parent.type, das.schematypes.Sequence):
                  item.parent.data[item.row] = item.data
               else:
                  item.parent.data.remove(oldvalue)
                  item.parent.data.add(item.data)
            else:
               seq = list(item.parent.data)
               seq[item.row] = item.data
               #self.setData(self.parent(index), das.types.Tuple(seq), role)
               self._setRawData(self.parent(index), das.types.Tuple(seq), pushUndo=False)
            # Force rebuild
            # (note: not necessary all the time, but to simplify logic)
            structureChanged = True

         self.pushUndo(undoData)

         return structureChanged

      def setData(self, index, value, role):
         if not self._checkIndex(index):
            return False

         if role == QtCore.Qt.CheckStateRole:
            # Update check stats
            # self.dataChanged.emit(index, index)
            # self.layoutChanged.emit()
            # return True
            self.setMessage("")
            return False

         elif role == QtCore.Qt.EditRole:
            if self._readonly:
               return False

            if self._headers[index.column()] == "Name":
               # Dict/DynamicDict keys
               item = index.internalPointer()
               newkey = das.copy(item.key)
               try:
                  newkey = value
               except Exception, e:
                  self.setItemErrorMessage(item, str(e))
                  return False
               if newkey != item.key:
                  if newkey in item.parent.data:
                     self.setItemErrorMessage(item.parent, "Key %s already exists" % value)
                     return False
                  else:
                     undoData = das.copy(self.getData())
                     try:
                        item.parent.data[newkey] = item.data
                        del(item.parent.data[item.key])
                     except Exception, e:
                        self.setItemErrorMessage(item.parent, str(e))
                        return False
                     else:
                        self.setMessage("")
                        self.pushUndo(undoData)
                        structureChanged = True
               else:
                  # Nothing to do here
                  return True

            elif self._headers[index.column()] == "Value":
               try:
                  structureChanged = self._setRawData(index, value)
               except Exception, e:
                  self.setItemErrorMessage(index.internalPointer(), str(e))
                  return False

            elif self._headers[index.column()] == "Type":
               # We actually never trigger this one... should we?
               return False

            elif self._headers[index.column()] == "Description":
               return False

            self.dataChanged.emit(index, index)

            if structureChanged:
               self.rebuild()
               self.internallyRebuilt.emit()
            else:
               self.layoutChanged.emit()

            return True

         return False

      def rowCount(self, index):
         if self._checkIndex(index):
            cnt = len(index.internalPointer().children)
         else:
            cnt = (0 if self._rootItem is None else 1)
         return cnt

      def columnCount(self, index):
         return len(self._headers)

      def supportedDragActions(self):
         return QtCore.Qt.MoveAction

      def supportedDropActions(self):
         return QtCore.Qt.MoveAction

      def mimeTypes(self):
         return ["text/plain"]

      def mimeData(self, indices):
         sl = []
         for index in indices:
            sl.append(index.internalPointer().fullname())
         data = QtCore.QMimeData()
         data.setText("\n".join(sl))
         return data

      def dropMimeData(self, data, action, row, column, parentIndex):
         if self._readonly:
            return False

         if not data.hasFormat("text/plain"):
            return False
         elif action == QtCore.Qt.IgnoreAction:
            return False

         indices = []
         for s in set(data.text().split("\n")):
            index = self.findIndex(s.strip())
            if index and index.isValid():
               indices.append(index)

         if len(indices) != 1:
            return False

         srcindex = indices[0]
         srcitem = srcindex.internalPointer()

         if row == -1 and column == -1:
            # Dropped on an item
            tgtindex = parentIndex
            tgtitem = tgtindex.internalPointer()
            if tgtitem == srcitem.parent:
               # Move element to last position
               seq = tgtitem.data
               if not tgtitem.resizable:
                  seq = list(seq)
               # Build re-ordered sequence
               seq = seq[:srcitem.row] + seq[srcitem.row+1:] + [srcitem.data]
               try:
                  self._setRawData(tgtindex, seq)
               except Exception, e:
                  self.setItemErrorMessage(tgtitem, str(e))
                  return False
               self.dataChanged.emit(self.index(0, 1, tgtindex), self.index(self.rowCount(tgtindex)-1, 1, tgtindex))
               self.rebuild()
               self.internallyRebuilt.emit()
               return True
            elif tgtitem.parent == srcitem.parent:
               # Copy element data
               index = self.index(tgtindex.row(), 1, self.parent(tgtindex))
               data = das.copy(srcitem.data)
               return self.setData(index, data, QtCore.Qt.EditRole)
            else:
               return False

         else:
            # Dropped between 2 items
            tgtindex = self.index(row, column, parentIndex)
            tgtitem = tgtindex.internalPointer()
            if tgtitem.parent == srcitem.parent:
               # Move element before tgtindex
               pindex = self.parent(tgtindex)
               pitem = srcitem.parent
               seq = pitem.data
               if not pitem.resizable:
                  seq = list(seq)
               # Build re-ordererd sequence
               seq = seq[:srcitem.row] + seq[srcitem.row+1:]
               idx = tgtitem.row
               if tgtitem.row > srcitem.row:
                  idx -= 1
               seq.insert(idx, srcitem.data)
               try:
                  self._setRawData(pindex, seq)
               except Exception, e:
                  self.setItemErrorMessage(pitem, str(e))
                  return False
               self.dataChanged.emit(tgtindex if (tgtitem.row < srcitem.row) else srcindex, self.index(self.rowCount(pindex)-1, 1, pindex))
               self.rebuild()
               self.internallyRebuilt.emit()
               return True
            else:
               return False


   class Editor(QtWidgets.QTreeView):
      modelUpdated = QtCore.Signal(Model)
      messageChanged = QtCore.Signal(str)

      def __init__(self, data, type=None, name=None, readonly=False, headers=None, fieldfilters=None, parent=None):
         super(Editor, self).__init__(parent)
         self.model = Model(data, type=type, name=name, readonly=readonly, headers=headers, fieldfilters=fieldfilters, parent=self)
         self.delegate = ModelItemDelegate(parent=self)
         self.selection = []
         self.scrollState = None
         self.setModel(self.model)
         self.expandedState = {}
         self.setItemDelegate(self.delegate)
         QtCompat.setSectionResizeMode(self.header(), QtWidgets.QHeaderView.Interactive)
         self.header().setStretchLastSection(False)
         self.header().setMinimumSectionSize(100)
         self.header().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
         self.header().customContextMenuRequested.connect(self.headerMenu)
         self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
         self.setAnimated(False)
         self.setHeaderHidden(False)
         self.setItemsExpandable(True)
         self.setAllColumnsShowFocus(True)
         self.setRootIsDecorated(True)
         self.setSortingEnabled(False)
         self.setDragEnabled(True)
         self.setAcceptDrops(True)
         self.setDropIndicatorShown(True)
         self.model.internallyRebuilt.connect(self.restoreExpandedState)
         self.model.dataChanged.connect(self.onContentChanged)
         self.model.messageChanged.connect(self.onMessageChanged)
         self.model.modelAboutToBeReset.connect(self.storeSelection)
         self.model.modelReset.connect(self.restoreSelection )
         self.collapsed.connect(self.onItemCollapsed)
         self.expanded.connect(self.onItemExpanded)
         index = QtCore.QModelIndex()
         if self.model.rowCount(index) > 0:
            self.setExpanded(self.model.index(0, 0, index), True)
         self._readonly = readonly

      def makeOnToggleColumn(self, name, show):
         def _callback(*args):
            self.model.setShowColumn(name, show)
         return _callback

      def headerMenu(self, pos):
         # column = self.header().logicalIndexAt(pos.x())
         # => clicked column... if ever needed
         menu = QtWidgets.QMenu(self)
         for item in Model.OptionalHeaders:
            shown = self.model.isColumnShown(item)
            act = menu.addAction(item)
            act.setCheckable(True)
            act.setChecked(shown)
            act.triggered.connect(self.makeOnToggleColumn(item, not shown))
         menu.popup(self.header().mapToGlobal(pos))

      def keyPressEvent(self, event):
         if (event.modifiers() & QtCore.Qt.ControlModifier) != 0:
            if event.key() == QtCore.Qt.Key_Y:
               event.accept()
               self.redo()

            elif event.key() == QtCore.Qt.Key_Z:
               event.accept()
               self.undo()

         elif event.modifiers() == QtCore.Qt.NoModifier:
            if event.key() == QtCore.Qt.Key_Delete:
               event.accept()
               # Check selected items
               iipairs = []
               if not self._readonly:
                  keys = set()
                  sel = self.selectionModel().selectedIndexes()
                  for index in sel:
                     item = index.internalPointer()
                     key = item.fullname()
                     if not key in keys:
                        keys.add(key)
                        iipairs.append((index, item))

               if len(set(map(lambda x: "" if x[1].parent is None else x[1].parent.fullname(), iipairs))) == 1:
                  # All items have same parent
                  index, item = iipairs[0]
                  if item.parent:
                     indices = [x[0] for x in iipairs]
                     if item.parent.mapping:
                        self.remDictItems(indices)
                     else:
                        if item.parent.orderable:
                           if item.parent.resizable:
                              self.remSeqItems(indices)
                        else:
                           self.remSetItems(indices)

      def mousePressEvent(self, event):
         if event.button() == QtCore.Qt.RightButton:
            event.accept()
            menu = QtWidgets.QMenu(self)

            # Selected items
            iipairs = []
            if not self._readonly:
               keys = set()
               sel = self.selectionModel().selectedIndexes()
               for index in sel:
                  item = index.internalPointer()
                  key = item.fullname()
                  if not key in keys:
                     keys.add(key)
                     iipairs.append((index, item))

            if len(set(map(lambda x: "" if x[1].parent is None else x[1].parent.fullname(), iipairs))) == 1:
               # All items have same parent
               index, item = iipairs[0]

               if len(iipairs) == 1 and item.exists():
                  actionAddItem = None
                  actionClearItems = None
                  if item.compound:
                     if item.mapping:
                        if item.mappingkeytype is not None:
                           actionAddItem = menu.addAction("Add ...")
                           actionAddItem.triggered.connect(self.makeOnAddDictItem(index))
                           actionClearItems = menu.addAction("Clear")
                           actionClearItems.triggered.connect(self.makeOnClearDictItems(index))
                     else:
                        if item.orderable:
                           if item.resizable:
                              actionAddItem = menu.addAction("Add")
                              actionAddItem.triggered.connect(self.makeOnAddSeqItem(index))
                              actionClearItems = menu.addAction("Clear")
                              actionClearItems.triggered.connect(self.makeOnClearSeqItems(index))
                        else:
                           actionAddItem = menu.addAction("Add ...")
                           actionAddItem.triggered.connect(self.makeOnAddSetItem(index))
                           actionClearItems = menu.addAction("Clear")
                           actionClearItems.triggered.connect(self.makeOnClearSetItems(index))
                  if actionAddItem:
                     menu.addSeparator()

               if item.parent:
                  actionRemItem = None
                  indices = [x[0] for x in iipairs]
                  if item.parent.mapping:
                     if item.parent.mappingkeytype is not None:
                        #actionRemItem = menu.addAction("Remove Key%s" % ("s" if len(iipairs) > 1 else ""))
                        actionRemItem = menu.addAction("Remove")
                        actionRemItem.triggered.connect(self.makeOnRemDictItems(indices))
                  else:
                     if item.parent.orderable:
                        if item.parent.resizable:
                           actionRemItem = menu.addAction("Remove")
                           actionRemItem.triggered.connect(self.makeOnRemSeqItems(indices))
                     else:
                        actionRemItem = menu.addAction("Remove")
                        actionRemItem.triggered.connect(self.makeOnRemSetItems(indices))
                  if actionRemItem:
                     menu.addSeparator()

            # Clicked item
            gpos = QtGui.QCursor.pos()
            pos = self.viewport().mapFromGlobal(gpos)
            modelIndex = self.indexAt(pos)
            item = (None if (modelIndex is None or not modelIndex.isValid()) else modelIndex.internalPointer())
            validitem = (item and item.exists())

            if not self._readonly and item:
               if item.exists():
                  if item.parent and item.parent.mapping and item.parent.mappingkeytype is None and item.optional:
                     actionRemItem = menu.addAction("Remove '%s'" % item.name)
                     actionRemItem.triggered.connect(self.makeOnRemOptionalItem(modelIndex))
                     menu.addSeparator()
               elif item.typestr != "alias":
                  actionAddItem = menu.addAction("Add '%s'" % item.name)
                  actionAddItem.triggered.connect(self.makeOnAddOptionalItem(modelIndex))
                  menu.addSeparator()

            actionResize = menu.addAction("Resize to Contents")
            actionResize.triggered.connect(self.onResizeToContents)
            actionExpandAll = menu.addAction("Expand All")
            actionExpandAll.triggered.connect(self.onExpandAll)
            actionCollapseAll = menu.addAction("Collapse All")
            actionCollapseAll.triggered.connect(self.onCollapseAll)
            actionHideDeprecated = menu.addAction("Deprecated Field(s)")
            actionHideDeprecated.setCheckable(True)
            actionHideDeprecated.setChecked(not self.model.hideDeprecated())
            actionHideDeprecated.toggled.connect(self.onToggleDeprecated)
            actionHideAliases = menu.addAction("Alias Field(s)")
            actionHideAliases.setCheckable(True)
            actionHideAliases.setChecked(not self.model.hideAliases())
            actionHideAliases.toggled.connect(self.onToggleAliases)
            actionShowHidden = menu.addAction("Show Hidden Field(s)")
            actionShowHidden.setCheckable(True)
            actionShowHidden.setChecked(self.model.showHidden())
            actionShowHidden.toggled.connect(self.onToggleShowHidden)

            menu.popup(event.globalPos())

         else:
            super(Editor, self).mousePressEvent(event)
 
      def getItemKey(self, modelIndex):
         return modelIndex.internalPointer().fullname(skipRoot=True)

      def storeSelection(self):
         mdl = self.selectionModel()
         sel = mdl.selection()
         self.selection = [self.getItemKey(x) for x in sel.indexes()]
         self.scrollState = (self.horizontalScrollBar().value(), self.verticalScrollBar().value())

      def restoreSelection(self):
         self.setFocus()
         mdl = self.selectionModel()
         sel = QtCore.QItemSelection()
         for item in self.selection:
            index = self.model.findIndex(item, addRoot=True)
            if index:
               sel.merge(QtCore.QItemSelection(index, index), QtCore.QItemSelectionModel.Select)
         mdl.select(sel, QtCore.QItemSelectionModel.SelectCurrent|QtCore.QItemSelectionModel.Rows)
         self.selection = []

      def getData(self):
         return self.model.getData()

      def setData(self, data, type=None, name=None):
         self.model.replaceData(data, type=type, name=name)
         index = QtCore.QModelIndex()
         # Try to restore expanded State
         if not self.restoreExpandedState():
            # Only reset expanded set if we have data and nothing was restored
            if data:
               self.expandedState = {}
            if self.model.rowCount(index) > 0:
               self.setExpanded(self.model.index(0, 0, index), True)
         self.modelUpdated.emit(self.model)

      def cleanData(self):
         self.model.cleanData()
         self.modelUpdated.emit(self.model)

      def canRedo(self):
         return self.model.canRedo()

      def canUndo(self):
         return self.model.canUndo()

      def clearUndos(self):
         self.model.clearUndos()

      def redo(self):
         if self.model.redo():
            self.modelUpdated.emit(self.model)

      def undo(self):
         if self.model.undo():
            self.modelUpdated.emit(self.model)

      def hasDataChanged(self):
         return self.model.hasDataChanged()

      def fieldFilters(self):
         return self.model().fieldFilters()

      def setFieldFilters(self, filterSet):
         self.model().setFieldFilters(filterSet)

      def resetExpandedState(self, index=None):
         if index is None:
            index = QtCore.QModelIndex()
            self.expandedState = {}
         else:
            k = self.getItemKey(index)
            if k is not None:
               self.expandedState[k] = self.isExpanded(index)

         nr = self.model.rowCount(index)
         for r in xrange(nr):
            self.resetExpandedState(index=self.model.index(r, 0, index))

         self.model.layoutChanged.emit()

      def restoreExpandedState(self, index=None):
         stateSet = False

         if index is None:
            index = QtCore.QModelIndex()
         else:
            k = self.getItemKey(index)
            if k is not None and k in self.expandedState:
               # avoid header resizing
               self.blockSignals(True)
               self.setExpanded(index, self.expandedState[k])
               self.blockSignals(False)
               stateSet = True

         nr = self.model.rowCount(index)
         for r in xrange(nr):
            if self.restoreExpandedState(index=self.model.index(r, 0, index)):
               stateSet = True

         #self.model.layoutChanged.emit()

         if index == QtCore.QModelIndex():
            if self.scrollState:
               hsv, vsv = self.scrollState
               self.horizontalScrollBar().setValue(hsv)
               self.verticalScrollBar().setValue(vsv)
               self.scrollState = None

         return stateSet

      def onItemCollapsed(self, modelIndex):
         self.expandedState[self.getItemKey(modelIndex)] = False
      
      def onItemExpanded(self, modelIndex):
         self.expandedState[self.getItemKey(modelIndex)] = True
         self.header().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

      def onResizeToContents(self):
         self.header().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

      def onToggleDeprecated(self, toggled):
         self.model.setHideDeprecated(not toggled)

      def onToggleAliases(self, toggled):
         self.model.setHideAliases(not toggled)

      def onToggleShowHidden(self, toggled):
         self.model.setShowHidden(toggled)

      def onExpandAll(self):
         # avoid onItemExpanded being called
         self.blockSignals(True)
         self.expandAll()
         self.blockSignals(False)
         self.resetExpandedState()
         self.header().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

      def onCollapseAll(self):
         self.collapseAll()
         self.resetExpandedState()

      def onContentChanged(self, topLeft, bottomRight):
         # Forward signal
         self.modelUpdated.emit(self.model)

      def onMessageChanged(self, msg):
         # Forward signal
         self.messageChanged.emit(msg)

      def makeOnAddDictItem(self, index):
         def _callback(*args):
            self.setExpanded(index, True)
            self.addDictItem(index)
         return _callback

      def makeOnAddSeqItem(self, index):
         def _callback(*args):
            self.setExpanded(index, True)
            self.addSeqItem(index)
         return _callback

      def makeOnAddSetItem(self, index):
         def _callback(*args):
            self.setExpanded(index, True)
            self.addSetItem(index)
         return _callback

      def makeOnAddOptionalItem(self, index):
         def _callback(*args):
            self.addOptionalItem(index)
         return _callback

      def makeOnClearDictItems(self, index):
         def _callback(*args):
            self.clearDictItems(index)
         return _callback

      def makeOnClearSeqItems(self, index):
         def _callback(*args):
            self.clearSeqItems(index)
         return _callback

      def makeOnClearSetItems(self, index):
         def _callback(*args):
            self.clearSetItems(index)
         return _callback

      def makeOnRemDictItems(self, indices):
         def _callback(*args):
            self.remDictItems(indices)
         return _callback

      def makeOnRemSeqItems(self, indices):
         def _callback(*args):
            self.remSeqItems(indices)
         return _callback

      def makeOnRemSetItems(self, indices):
         def _callback(*args):
            self.remSetItems(indices)
         return _callback

      def makeOnRemOptionalItem(self, index):
         def _callback(*args):
            self.remOptionalItem(index)
         return _callback

      def addDictItem(self, index):
         # Show a dialog with another Editor for just the key type
         item = index.internalPointer()
         dlg = NewValueDialog(item.type.ktype, excludes=item.data, name="%s[...]" % item.name, parent=self)
         def _addDictItem():
            undoData = das.copy(self.model.getData())
            try:
               item.data[dlg.data] = item.type.vtype.make_default()
            except Exception, e:
               self.model.setItemErrorMessage(item, "Failed to add key %s\n(%s)" % (dlg.data, e))
            else:
               self.model.pushUndo(undoData)
               self.model.rebuild()
               self.restoreExpandedState()
               self.modelUpdated.emit(self.model)
         dlg.accepted.connect(_addDictItem)
         dlg.show()

      def addSeqItem(self, index):
         item = index.internalPointer()
         undoData = das.copy(self.model.getData())
         item.data.append(item.type.type.make_default())
         self.model.pushUndo(undoData)
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

      def addSetItem(self, index):
         # Show a dialog with another Editor for just the value type
         item = index.internalPointer()
         dlg = NewValueDialog(item.type.type, excludes=item.data, name="%s{...}" % item.name, parent=self)
         def _addSetItem():
            undoData = das.copy(self.model.getData())
            try:
               item.data.add(dlg.data)
            except Exception, e:
               self.model.setItemErrorMessage(item, "Failed to add value %s\n(%s)" % (dlg.data, e))
            else:
               self.model.pushUndo(undoData)
               self.model.rebuild()
               self.restoreExpandedState()
               self.modelUpdated.emit(self.model)
         dlg.accepted.connect(_addSetItem)
         dlg.show()

      def addOptionalItem(self, index):
         item = index.internalPointer()
         v = item.type.make_default()
         undoData = das.copy(self.model.getData())
         item.parent.data[item.key] = v
         self.model.pushUndo(undoData)
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

      def clearDictItems(self, index):
         self.model.setData(index.sibling(index.row(), 1), {}, QtCore.Qt.EditRole)

      def clearSeqItems(self, index):
         self.model.setData(index.sibling(index.row(), 1), [], QtCore.Qt.EditRole)

      def clearSetItems(self, index):
         self.model.setData(index.sibling(index.row(), 1), set(), QtCore.Qt.EditRole)

      def remDictItems(self, indices):
         undoData = das.copy(self.model.getData())
         for index in indices:
            item = index.internalPointer()
            del(item.parent.data[item.key])
         self.model.pushUndo(undoData)
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

      def remSeqItems(self, indices):
         # Not really
         if len(indices) > 0:
            parents = set(map(lambda x: "" if x.parent is None else x.parent.fullname(), [y.internalPointer() for y in indices]))
            if len(parents) != 1:
               return

            parentIndex = self.model.parent(indices[0])
            curseq = parentIndex.internalPointer().data
            newseq = []
            remrows = set([index.row() for index in indices])
            for row in xrange(len(curseq)):
               if not row in remrows:
                  newseq.append(curseq[row])

            # this will create an undo entry for the parent automatically
            self.model.setData(parentIndex.sibling(parentIndex.row(), 1), newseq, QtCore.Qt.EditRole)

      def remSetItems(self, indices):
         undoData = das.copy(self.model.getData())
         for index in indices:
            item = index.internalPointer()
            item.parent.data.remove(item.data)
         self.model.pushUndo(undoData)
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

      def remOptionalItem(self, index):
         item = index.internalPointer()
         undoData = das.copy(self.model.getData())
         del(item.parent.data[item.key])
         self.model.pushUndo(undoData)
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

