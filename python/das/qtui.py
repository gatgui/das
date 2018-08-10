import das
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


   class ModelItem(object):
      ReservedTypeNames = set(["alias", "empty", "boolean", "integer", "real", "string", "list", "tuple", "set", "dict", "struct"])

      def __init__(self, name, data, type=None, parent=None, row=0, key=None):
         super(ModelItem, self).__init__()
         self.row = row
         self.key = key
         self.name = name
         self.parent = parent
         self.update(data, type)

      def __str__(self):
         return "ModelItem(%s, compound=%s, resizable=%s, multi=%s, editable=%s, optional=%s, parent=%s, children=%d)" % (self.name, self.compound, self.resizable, self.multi, self.editable, self.optional, ("None" if not self.parent else self.parent.name), len(self.children))

      def fullname(self, skipRoot=False):
         k = ""
         item = self
         while item:
            suffix = ("" if not k else (".%s" % k))
            k = item.name + suffix
            item = item.parent
            if skipRoot and item and not item.parent:
               break
         return k

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
                  values.append(("integer", v))
               except:
                  pass
            elif isinstance(t, das.schematypes.Real):
               try:
                  v = float(s)
                  values.append(("real", v))
               except:
                  pass
            elif isinstance(t, das.schematypes.String):
               try:
                  values.append(("string", s))
               except:
                  pass
            elif isinstance(t, das.schematypes.Class):
               try:
                  v = t.make_default()
                  v.string_to_value(s)
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

      def update(self, data, type=None):
         self.children = []
         self.compound = False
         self.mapping = False
         self.mappingkeys = None
         self.mappingkeytype = None
         self.uniformmapping = True # mapping of uniform type values
         self.resizable = False
         self.orderable = False # orderable compound
         self.optional = False
         self.editable = False # will be false for aliases
         self.multi = False
         self.data = data # for alias, it is the same data as the original
         self.type = type
         self.typestr = ""

         if self.type is None and self.data is not None:
            self.type = self.data._get_schema_type()
            if self.type is None:
               raise Exception("No schema type for model item")

         if isinstance(self.type, das.schematypes.Alias):
            # Shortcut
            self.typestr = "alias"
            self.data = None
            return

         self.optional = isinstance(self.type, das.schematypes.Optional)

         self.type = self.real_type(self.type)

         self.multi = isinstance(self.type, das.schematypes.Or)

         self.editable = self.is_editable(self.type)

         self.compound = self.is_compound(self.type)

         if self.compound:
            if isinstance(self.type, das.schematypes.Sequence):
               self.typestr = "list"
               self.resizable = True
               self.orderable = True
               if self.exists():
                  for i in xrange(len(self.data)):
                     itemname = "[%d]" % i
                     itemdata = self.data[i]
                     self.children.append(ModelItem(itemname, itemdata, type=self.type.type, parent=self, row=i))

            elif isinstance(self.type, das.schematypes.Tuple):
               self.typestr = "tuple"
               self.resizable = False
               self.orderable = True
               if self.exists():
                  for i in xrange(len(self.data)):
                     itemname = "(%d)" % i
                     itemdata = self.data[i]
                     self.children.append(ModelItem(itemname, itemdata, type=self.type.types[i], parent=self, row=i))

            elif isinstance(self.type, das.schematypes.Set):
               self.typestr = "set"
               self.resizable = True
               self.orderable = False
               if self.exists():
                  i = 0
                  for itemdata in self.data:
                     itemname = "{%d}" % i
                     self.children.append(ModelItem(itemname, itemdata, type=self.type.type, parent=self, row=i))
                     i += 1

            elif isinstance(self.type, (das.schematypes.Struct, das.schematypes.StaticDict)):
               self.typestr = "struct"
               self.resizable = False
               self.orderable = False
               self.mapping = True
               self.mappingkeys = {}
               self.uniformmapping = False
               i = 0
               for k, t in self.type.iteritems():
                  optional = isinstance(t, das.schematypes.Optional)
                  self.mappingkeys[k] = optional
                  if optional:
                     self.resizable = True
                  if self.exists():
                     if isinstance(t, das.schematypes.Alias):
                        v = None
                     elif not k in self.data:
                        v = t.make_default()
                     else:
                        v = self.data[k]
                     self.children.append(ModelItem(k, v, type=t, parent=self, row=i, key=k))
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
                     v = self.data[k]
                     ks = str(k)
                     vtype = self.type.vtypeOverrides.get(k, self.type.vtype)
                     self.children.append(ModelItem(ks, v, type=vtype, parent=self, row=i, key=k))
                     i += 1

         else:
            if self.multi:
               self.update_multi_type_string()
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


   class NewValueDialog(QtWidgets.QDialog):
      def __init__(self, vtype, excludes=None, name=None, parent=None):
         super(NewValueDialog, self).__init__(parent, QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowSystemMenuHint)
         self.setWindowTitle("Create new value")
         self.excludes = excludes
         self.data = vtype.make_default()
         self.editor = Editor(self.data, type=vtype, name=name, parent=self)
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
               rv.setProperty("message", str(e))
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
               func(widget, model, modelIndex)
            else:
               model.setItemErrorMessage(item, "No 'setModelData' property set on editor widget")
         else:
            model.setItemErrorMessage(item, widget.property("message"))

      def setTypeModelData(self, widget, model, modelIndex):
         data = widget.itemData(widget.currentIndex())
         index = model.index(modelIndex.row(), 1, modelIndex.parent())
         model.setData(index, data, QtCore.Qt.EditRole)

      def setMappingKeyModelData(self, widget, model, modelIndex):
         try:
            key = eval(widget.text())
         except:
            key = widget.text()
         model.setData(modelIndex, key, QtCore.Qt.EditRole)

      def setOrModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()

         values = item.get_valid_types(string=widget.text())

         if len(values) >= 1:
            _, v = values[0]
            model.setData(modelIndex, v, QtCore.Qt.EditRole)
         else:
            model.setItemErrorMessage(item, "Input doesn't match any supported types")

      def setBoolModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         data = (widget.checkState() == QtCore.Qt.Checked)
         model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setIntModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.enum is not None:
            data = item.type.enum[widget.currentText()]
         else:
            if item.type.min is not None and item.type.max is not None:
               data = widget.value()
            else:
               data = long(widget.text())
         model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setFltModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.min is not None and item.type.max is not None:
            data = widget.value()
         else:
            data = float(widget.text())
         model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setStrModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.choices is not None:
            data = widget.currentText()
         else:
            data = widget.text()
         model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setClassModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         data = item.data.copy()
         data.string_to_value(widget.text())
         model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def updateEditorGeometry(self, widget, viewOptions, modelIndex):
         widget.setGeometry(viewOptions.rect)


   class Model(QtCore.QAbstractItemModel):
      internallyRebuilt = QtCore.Signal()
      dataChanged2Args = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)
      messageChanged = QtCore.Signal(str)

      def __init__(self, data, type=None, name=None, readonly=False, parent=None):
         super(Model, self).__init__(parent)
         # A little hacky but how else?
         if IsPySide2():
            self._org_data_changed = self.dataChanged
            self.dataChanged = self.dataChanged2Args
            self.dataChanged.connect(self.__emitDataChanged)
         self._headers = ["Name", "Value", "Type"]
         self._rootItem = None
         self._orgData = None
         self._message = ""
         self._readonly = readonly
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
            self._rootItem.update(data, type=type)
         elif data is not None:
            self._rootItem = ModelItem("<root>" if name is None else name, data, type=type)

      def getData(self):
         return (None if self._rootItem is None else self._rootItem.data)

      def replaceData(self, data, type=None, name=None):
         self._orgData = None
         self._rootItem = None
         self.beginResetModel()
         self._buildItemsTree(data=data, type=type, name=name)
         self.endResetModel()
         rootIndex = self.index(0, 0, QtCore.QModelIndex())
         self.dataChanged.emit(rootIndex, rootIndex)
         self.internallyRebuilt.emit()

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

      def findIndex(self, s):
         spl = s.split(".")
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
            print("Can't find index for '%s'" % s)
            return None
         else:
            return parentIndex

      def rebuild(self):
         self.beginResetModel()
         self._buildItemsTree()
         self.endResetModel()

      def flags(self, index):
         if not index.isValid():
            return QtCore.Qt.NoItemFlags
         else:
            flags = QtCore.Qt.ItemIsSelectable
            item = index.internalPointer()

            if not self._readonly:
               if item.parent and not item.parent.mapping and item.parent.orderable:
                  flags = flags | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

               if item.compound  and not item.mapping and item.orderable:
                  flags = flags | QtCore.Qt.ItemIsDropEnabled

            if index.column() == 0:
               if item.exists():
                  flags = flags | QtCore.Qt.ItemIsEnabled
               # flags = flags | QtCore.Qt.ItemIsUserCheckable
               if not self._readonly:
                  if item.parent:
                     if item.parent.mapping and item.parent.mappingkeytype is not None:
                        flags = flags | QtCore.Qt.ItemIsEditable

            elif index.column() == 1:
               if not self._readonly:
                  if item.exists() and not item.compound:
                     flags = flags | QtCore.Qt.ItemIsEnabled
                  # any other cases?
                  if item.editable:
                     flags = flags | QtCore.Qt.ItemIsEditable

            elif index.column() == 2:
               if not self._readonly:
                  if item.editable and item.multi and len(item.get_valid_types()) > 1:
                     flags = flags | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

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
         if not index.isValid():
            return None

         item = index.internalPointer()

         if role == QtCore.Qt.DecorationRole:
            # No icons
            return None

         elif role == QtCore.Qt.CheckStateRole:
            # No check boxes
            # If want some: return QtCore.Qt.Checked or QtCore.Qt.Unchecked
            return None

         elif role == QtCore.Qt.ForegroundRole:
            # No changes in color
            return None

         elif not role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return None

         rv = None

         if index.column() == 0:
            rv = item.name

         elif index.column() == 1:
            if item.typestr == "alias":
               rv = "= " + item.type.name

            elif not item.compound:
               if role == QtCore.Qt.DisplayRole:
                  if not item.editable:
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

         elif index.column() == 2:
            rv = item.typestr

         if role == QtCore.Qt.DisplayRole and index.column() == 1:
            rv = "    " + rv

         return rv

      def _setRawData(self, index, value):
         structureChanged = False
         item = index.internalPointer()

         oldvalue = item.data
         try:
            item.data = value
            item.update_multi_type_string()
         except Exception, e:
            self.setItemErrorMessage(item, str(e))
         else:
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
                  self._setRawData(self.parent(index), das.types.Tuple(seq))
               # Force rebuild
               # (note: not necessary all the time, but to simplify logic)
               structureChanged = True

         return structureChanged

      def setData(self, index, value, role):
         if not index.isValid():
            return False

         if role == QtCore.Qt.CheckStateRole:
            # Update check stats
            # self.dataChanged.emit(index, index)
            # self.layoutChanged.emit()
            # return True
            self.setMessage("")
            return False

         elif role == QtCore.Qt.EditRole:
            if index.column() == 0:
               # Dict/DynamicDict keys
               item = index.internalPointer()
               newkey = das.copy(item.key)
               newkey = value
               self.setMessage("")
               if newkey != item.key:
                  if newkey in item.parent.data:
                     self.setItemErrorMessage(item.parent, "Key %s already exists" % value)
                     return False
                  else:
                     item.parent.data[newkey] = item.data
                     del(item.parent.data[item.key])
                     structureChanged = True
               else:
                  return True

            elif index.column() == 1:
               structureChanged = self._setRawData(index, value)

            elif index.column() == 2:
               # We actually never trigger this one... should we?
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
         if index.isValid():
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
               self._setRawData(tgtindex, seq)
               self.dataChanged.emit(self.index(0, 1, tgtindex), self.index(self.rowCount(tgtindex)-1, 1, tgtindex))
               self.rebuild()
               self.internallyRebuilt.emit()
            elif tgtitem.parent == srcitem.parent:
               # Copy element data
               index = self.index(tgtindex.row(), 1, self.parent(tgtindex))
               data = das.copy(srcitem.data)
               self.setData(index, data, QtCore.Qt.EditRole)
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
               self._setRawData(pindex, seq)
               self.dataChanged.emit(tgtindex if (tgtitem.row < srcitem.row) else srcindex, self.index(self.rowCount(pindex)-1, 1, pindex))
               self.rebuild()
               self.internallyRebuilt.emit()
            else:
               return False

         return True


   class Editor(QtWidgets.QTreeView):
      modelUpdated = QtCore.Signal(Model)
      messageChanged = QtCore.Signal(str)

      def __init__(self, data, type=None, name=None, readonly=False, parent=None):
         super(Editor, self).__init__(parent)
         self.model = Model(data, type=type, name=name, readonly=readonly, parent=self)
         self.delegate = ModelItemDelegate(parent=self)
         self.setModel(self.model)
         self.expandedState = {}
         self.checkedState = {}
         self.setItemDelegate(self.delegate)
         #QtCompat.setSectionResizeMode(self.header(), QtWidgets.QHeaderView.ResizeToContents)
         QtCompat.setSectionResizeMode(self.header(), QtWidgets.QHeaderView.Interactive)
         self.header().setStretchLastSection(True)
         self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
         #self.header().setMinimumSectionSize(200)
         self.setAnimated(True)
         self.setHeaderHidden(False)
         self.setItemsExpandable(True)
         self.setAllColumnsShowFocus(True)
         self.setRootIsDecorated(True)
         self.setSortingEnabled(False)
         # self.setUniformRowHeights(True)
         self.setDragEnabled(True)
         self.setAcceptDrops(True)
         self.setDropIndicatorShown(True)
         self.model.internallyRebuilt.connect(self.restoreExpandedState)
         self.model.dataChanged.connect(self.onContentChanged)
         self.model.messageChanged.connect(self.onMessageChanged)
         self.collapsed.connect(self.onItemCollapsed)
         self.expanded.connect(self.onItemExpanded)
         index = QtCore.QModelIndex()
         if self.model.rowCount(index) > 0:
            self.setExpanded(self.model.index(0, 0, index), True)

      def mousePressEvent(self, event):
         if event.button() == QtCore.Qt.RightButton:
            event.accept()
            menu = QtWidgets.QMenu(self)

            # Selected items
            keys = set()
            iipairs = []
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
                           actionAddItem = menu.addAction("Add Key...")
                           actionAddItem.triggered.connect(self.makeOnAddDictItem(index))
                           actionClearItems = menu.addAction("Clear Keys")
                           actionClearItems.triggered.connect(self.makeOnClearDictItems(index))
                     else:
                        if item.orderable:
                           if item.resizable:
                              actionAddItem = menu.addAction("Append Element")
                              actionAddItem.triggered.connect(self.makeOnAddSeqItem(index))
                              actionClearItems = menu.addAction("Clear List")
                              actionClearItems.triggered.connect(self.makeOnClearSeqItems(index))
                        else:
                           actionAddItem = menu.addAction("Add Element...")
                           actionAddItem.triggered.connect(self.makeOnAddSetItem(index))
                           actionClearItems = menu.addAction("Clear Set")
                           actionClearItems.triggered.connect(self.makeOnClearSetItems(index))
                  if actionAddItem:
                     menu.addSeparator()

               if item.parent:
                  actionRemItem = None
                  indices = [x[0] for x in iipairs]
                  if item.parent.mapping:
                     if item.parent.mappingkeytype is not None:
                        actionRemItem = menu.addAction("Remove Key%s" % ("s" if len(iipairs) > 1 else ""))
                        actionRemItem.triggered.connect(self.makeOnRemDictItems(indices))
                  else:
                     if item.parent.orderable:
                        if item.parent.resizable:
                           actionRemItem = menu.addAction("Remove Element%s" % ("s" if len(iipairs) > 1 else ""))
                           actionRemItem.triggered.connect(self.makeOnRemSeqItems(indices))
                     else:
                        actionRemItem = menu.addAction("Remove Element%s" % ("s" if len(iipairs) > 1 else ""))
                        actionRemItem.triggered.connect(self.makeOnRemSetItems(indices))
                  if actionRemItem:
                     menu.addSeparator()

            # Clicked item
            gpos = QtGui.QCursor.pos()
            pos = self.viewport().mapFromGlobal(gpos)
            modelIndex = self.indexAt(pos)
            item = (None if (modelIndex is None or not modelIndex.isValid()) else modelIndex.internalPointer())
            validitem = (item and item.exists())

            if item:
               if item.exists():
                  if item.parent and item.parent.mapping and item.parent.mappingkeytype is None and item.optional:
                     actionRemItem = menu.addAction("Remove '%s'" % item.name)
                     actionRemItem.triggered.connect(self.makeOnRemOptionalItem(modelIndex))
                     menu.addSeparator()
               elif item.typestr != "alias":
                  actionAddItem = menu.addAction("Add '%s'" % item.name)
                  actionAddItem.triggered.connect(self.makeOnAddOptionalItem(modelIndex))
                  menu.addSeparator()

            actionExpandAll = menu.addAction("Expand All")
            actionExpandAll.triggered.connect(self.onExpandAll)
            actionCollapseAll = menu.addAction("Collapse All")
            actionCollapseAll.triggered.connect(self.onCollapseAll)

            menu.popup(event.globalPos())

         else:
            super(Editor, self).mousePressEvent(event)

      def getItemKey(self, modelIndex):
         k = None
         item = modelIndex.internalPointer()
         return item.fullname()

      def getData(self):
         return self.model.getData()

      def setData(self, data, type=None, name=None):
         self.expandedState = {}
         self.model.replaceData(data, type=type, name=name)
         self.modelUpdated.emit(self.model)
         index = QtCore.QModelIndex()
         if self.model.rowCount(index) > 0:
            self.setExpanded(self.model.index(0, 0, index), True)

      def cleanData(self):
         self.model.cleanData()
         self.modelUpdated.emit(self.model)

      def hasDataChanged(self):
         return self.model.hasDataChanged()

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
         if index is None:
            index = QtCore.QModelIndex()
         else:
            k = self.getItemKey(index)
            if k is not None and k in self.expandedState:
               self.setExpanded(index, self.expandedState[k])

         nr = self.model.rowCount(index)
         for r in xrange(nr):
            self.restoreExpandedState(index=self.model.index(r, 0, index))

         self.model.layoutChanged.emit()

      def onItemCollapsed(self, modelIndex):
         k = self.getItemKey(modelIndex)
         if k is not None:
            self.expandedState[k] = False
      
      def onItemExpanded(self, modelIndex):
         k = self.getItemKey(modelIndex)
         if k is not None:
            self.expandedState[k] = True

      def onExpandAll(self):
         self.expandAll()
         self.resetExpandedState()

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
            self.addDictItem(index)
         return _callback

      def makeOnAddSeqItem(self, index):
         def _callback(*args):
            self.addSeqItem(index)
         return _callback

      def makeOnAddSetItem(self, index):
         def _callback(*args):
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
         dlg = NewValueDialog(item.type.ktype, excludes=item.data, name="<new key>", parent=self)
         def _addDictItem():
            try:
               item.data[dlg.data] = item.type.vtype.make_default()
            except Exception, e:
               self.model.setItemErrorMessage(item, "Failed to add key %s\n(%s)" % (dlg.data, e))
            else:
               self.model.rebuild()
               self.restoreExpandedState()
               self.modelUpdated.emit(self.model)
         dlg.accepted.connect(_addDictItem)
         dlg.show()

      def addSeqItem(self, index):
         item = index.internalPointer()
         item.data.append(item.type.type.make_default())
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

      def addSetItem(self, index):
         # Show a dialog with another Editor for just the value type
         item = index.internalPointer()
         dlg = NewValueDialog(item.type.type, excludes=item.data, name="<new value>", parent=self)
         def _addSetItem():
            try:
               item.data.add(dlg.data)
            except Exception, e:
               self.model.setItemErrorMessage(item, "Failed to add value %s\n(%s)" % (dlg.data, e))
            else:
               self.model.rebuild()
               self.restoreExpandedState()
               self.modelUpdated.emit(self.model)
         dlg.accepted.connect(_addSetItem)
         dlg.show()

      def addOptionalItem(self, index):
         item = index.internalPointer()
         v = item.type.make_default()
         item.parent.data[item.key] = v
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
         for index in indices:
            item = index.internalPointer()
            del(item.parent.data[item.key])
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

            self.model.setData(parentIndex.sibling(parentIndex.row(), 1), newseq, QtCore.Qt.EditRole)

         for index in indices:
            
            item = index.internalPointer()
            seq = item.parent.data
            seq = seq[:item.row] + seq[item.row+1:]
         

      def remSetItems(self, indices):
         for index in indices:
            item = index.internalPointer()
            item.parent.data.remove(item.data)
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)

      def remOptionalItem(self, index):
         item = index.internalPointer()
         del(item.parent.data[item.key])
         self.model.rebuild()
         self.restoreExpandedState()
         self.modelUpdated.emit(self.model)
