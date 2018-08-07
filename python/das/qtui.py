import das
import math

NoUI = False
Debug = True

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
      def __init__(self, name, data, type=None, parent=None, row=0, key=None):
         super(ModelItem, self).__init__()
         self.row = row
         self.key = key
         self.name = name
         self.parent = parent
         self.update(data, type)

      def __str__(self):
         return "ModelItem(%s, compound=%s, resizable=%s, multi=%s, editable=%s, optional=%s, parent=%s, children=%d)" % (self.name, self.compound, self.resizable, self.multi, self.editable, self.optional, ("None" if not self.parent else self.parent.name), len(self.children))

      def fullname(self):
         k = ""
         item = self
         while item:
            suffix = ("" if not k else (".%s" % k))
            k = item.name + suffix
            item = item.parent
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
            return True

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
         self.editable = False
         self.multi = False
         self.data = data
         self.type = type
         self.invalid = False
         self.errmsg = ""

         if self.type is None and self.data is not None:
            self.type = self.data._get_schema_type()
            if self.type is None:
               raise Exception("No schema type for model item")

         self.optional = isinstance(self.type, das.schematypes.Optional)

         self.type = self.real_type(self.type)

         self.multi = isinstance(self.type, das.schematypes.Or)

         self.editable = self.is_editable(self.type)

         self.compound = self.is_compound(self.type)

         if self.compound:
            if isinstance(self.type, das.schematypes.Sequence):
               self.resizable = True
               self.orderable = True
               for i in xrange(len(self.data)):
                  itemname = "%s[%d]" % (self.name, i)
                  itemdata = self.data[i]
                  self.children.append(ModelItem(itemname, itemdata, type=self.type.type, parent=self, row=i))

            elif isinstance(self.type, das.schematypes.Tuple):
               self.resizable = False
               self.orderable = True
               for i in xrange(len(self.data)):
                  itemname = "%s[%d]" % (self.name, i)
                  itemdata = self.data[i]
                  self.children.append(ModelItem(itemname, itemdata, type=self.type.types[i], parent=self, row=i))

            elif isinstance(self.type, das.schematypes.Set):
               self.resizable = True
               self.orderable = False
               i = 0
               for itemdata in self.data:
                  itemname = "%s[%d]" % (self.name, i)
                  self.children.append(ModelItem(itemname, itemdata, type=self.type.type, parent=self, row=i))
                  i += 1

            elif isinstance(self.type, (das.schematypes.Struct, das.schematypes.StaticDict)):
               self.resizable = False
               self.orderable = False
               self.mapping = True
               self.mappingkeys = {}
               self.uniformmapping = False
               for k, t in self.type.iteritems():
                  if isinstance(t, das.schematypes.Alias):
                     continue
                  optional = isinstance(t, das.schematypes.Optional)
                  self.mappingkeys[k] = optional
                  if optional:
                     self.resizable = True
               i = 0
               for k in sorted([x for x in self.data.iterkeys()]):
                  v = self.data[k]
                  self.children.append(ModelItem(k, v, type=self.type[k], parent=self, row=i, key=k))
                  i += 1

            elif isinstance(self.type, (das.schematypes.Dict, das.schematypes.DynamicDict)):
               self.resizable = True
               self.orderable = False
               self.mapping = True
               self.mappingkeytype = self.type.ktype
               self.uniformmapping = (len(self.type.vtypeOverrides) == 0)
               i = 0
               dkeys = [x for x in self.data.iterkeys()]
               for k in sorted(dkeys):
                  v = self.data[k]
                  ks = str(k)
                  vtype = self.type.vtypeOverrides.get(k, self.type.vtype)
                  self.children.append(ModelItem(ks, v, type=vtype, parent=self, row=i, key=k))
                  i += 1


   class OrTypeChoiceDialog(QtWidgets.QDialog):
      def __init__(self, choices, parent=None):
         super(OrTypeChoiceDialog, self).__init__(parent)
         self.typename = None
         self.buttons = []
         layout = QtWidgets.QVBoxLayout()
         label = QtWidgets.QLabel("Inputed value matches several types.\nPlease specify the one you want:", self)
         layout.addWidget(label, 0)
         group = QtWidgets.QGroupBox(self)
         groupl = QtWidgets.QVBoxLayout()
         for choice in choices:
            rbtn = QtWidgets.QRadioButton(choice, group)
            groupl.addWidget(rbtn, 0)
            self.buttons.append(rbtn)
         group.setLayout(groupl)
         layout.addWidget(group, 0)
         layout.addStretch(1)
         okbtn = QtWidgets.QPushButton("Ok", self)
         cancelbtn = QtWidgets.QPushButton("Cancel", self)
         btnl = QtWidgets.QHBoxLayout()
         btnl.addWidget(okbtn, 1)
         btnl.addWidget(cancelbtn, 1)
         layout.addLayout(btnl, 0)
         self.setLayout(layout)
         # Wire callbacks
         okbtn.clicked.connect(self.accept)
         cancelbtn.clicked.connect(self.reject)

      def accept(self):
         self.typename = None
         for b in self.buttons:
            if b.isChecked():
               self.typename = b.text()
               break
         super(OrTypeChoiceDialog, self).accept()

      def reject(self):
         self.typename = None
         super(OrTypeChoiceDialog, self).reject()


   class ModelItemDelegate(QtWidgets.QItemDelegate):
      def __init__(self, parent=None):
         super(ModelItemDelegate, self).__init__(parent)

      def _getValidOrValues(self, s, item):
         values = []

         for t in item.type.types:
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
                  v = item.data.copy()
                  v.string_to_value(s)
                  values.append(("class", v))
               except:
                  pass

         return values

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
         return rv

      def createMappingKeyEditor(self, parent, item):
         rv = QtWidgets.QLineEdit(parent)
         def textChanged(txt):
            try:
               val = eval(txt)
               newkey = das.copy(item.key)
               newkey = val
            except Exception, e:
               item.invalid = True
               item.errmsg = "Invalid value for item key '%s': %s" % (item.fullname(), e)
            else:
               item.invalid = False
         rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setMappingKeyEditorData)
         rv.setProperty("setModelData", self.setMappingKeyModelData)
         return rv

      def createOrEditor(self, parent, item):
         rv = QtWidgets.QLineEdit(parent)
         def textChanged(txt):
            item.invalid = (len(self._getValidOrValues(txt, item)) == 0)
            if item.invalid:
               item.errmsg = "Invalid value for item '%s': Doesn't match any of the eligible types" % item.fullname()
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
            for k in sorted(item.type.enum.keys()):
               v = item.type.enum[k]
               rv.addItem(k, userData=v)
         elif item.type.min is not None and item.type.max is not None:
            rv = QtWidgets.QFrame(parent)
            fld = QtWidgets.QLineEdit(rv)
            fld.setObjectName("field")
            sld = QtWidgets.QSlider(QtCore.Qt.Horizontal, rv)
            sld.setObjectName("slider")
            sld.setTracking(True)
            sld.setMinimum(item.type.min)
            sld.setMaximum(item.type.max)
            lay = QtWidgets.QHBoxLayout()
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)
            lay.addWidget(fld, 0)
            lay.addWidget(sld, 1)
            rv.setLayout(lay)
            def textChanged(txt):
               try:
                  val = int(txt)
               except Exception, e:
                  item.invalid = True
                  item.errmsg = "Invalid value for item '%s': %s" % (item.fullname(), e)
                  # if text is not empty, reset to slider value
                  if txt:
                     fld.setText(str(sld.value()))
               else:
                  item.invalid = False
                  if val < item.type.min:
                     val = item.type.min
                     fld.blockSignals(True)
                     fld.setText(str(val))
                     fld.blockSignals(False)
                  elif val > item.type.max:
                     val = item.type.max
                     fld.blockSignals(True)
                     fld.setText(str(val))
                     fld.blockSignals(False)
                  sld.blockSignals(True)
                  sld.setValue(val)
                  sld.blockSignals(False)
            def sliderChanged(val):
               item.invalid = False
               fld.blockSignals(True)
               fld.setText(str(val))
               fld.blockSignals(False)
            sld.valueChanged.connect(sliderChanged)
            fld.textChanged.connect(textChanged)
            #fld.setFocus(QtCore.Qt.OtherFocusReason)
         else:
            rv = QtWidgets.QLineEdit(parent)
            def textChanged(txt):
               try:
                  int(txt)
               except Exception, e:
                  item.invalid = True
                  item.errmsg = "Invalid value for item '%s': %s" % (item.fullname(), e)
                  # if text is not empty, reset to original value
                  if txt:
                     rv.setText(str(item.data))
               else:
                  item.invalid = False
            rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setIntEditorData)
         rv.setProperty("setModelData", self.setIntModelData)
         return rv

      def createFltEditor(self, parent, item):
         if item.type.min is not None and item.type.max is not None:
            rv = QtWidgets.QFrame(parent)
            fld = QtWidgets.QLineEdit(rv)
            fld.setObjectName("field")
            sld = QtWidgets.QSlider(QtCore.Qt.Horizontal, rv)
            sld.setObjectName("slider")
            sld.setTracking(True)
            self.sldscl = 10000.0
            sldmin = int(math.floor(item.type.min * self.sldscl))
            sldmax = int(math.ceil(item.type.max * self.sldscl))
            sld.setMinimum(sldmin)
            sld.setMaximum(sldmax)
            lay = QtWidgets.QHBoxLayout()
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)
            lay.addWidget(fld, 0)
            lay.addWidget(sld, 1)
            rv.setLayout(lay)
            def textChanged(txt):
               try:
                  val = float(txt)
               except Exception, e:
                  item.invalid = True
                  item.errmsg = "Invalid value for item '%s': %s" % (item.fullname(), e)
                  # if text is not empty, reset to slider value
                  if txt:
                     fld.setText(str(sld.value() / self.sldscl))
               else:
                  item.invalid = False
                  if val < item.type.min:
                     val = item.type.min
                     fld.blockSignals(True)
                     fld.setText(str(val))
                     fld.blockSignals(False)
                  elif val > item.type.max:
                     val = item.type.max
                     fld.blockSignals(True)
                     fld.setText(str(val))
                     fld.blockSignals(False)
                  sld.blockSignals(True)
                  sld.setValue(int(math.floor(0.5 + val * self.sldscl)))
                  sld.blockSignals(False)
            def sliderChanged(val):
               # as we round down slider min value and round up slider max value
               # we may need to adjust here
               val = val / self.sldscl
               if val < item.type.min:
                  val = item.type.min
               elif val > item.type.max:
                  val = item.type.max
               fld.blockSignals(True)
               fld.setText(str(val))
               fld.blockSignals(False)
               item.invalid = False
            sld.valueChanged.connect(sliderChanged)
            fld.textChanged.connect(textChanged)
            #fld.setFocus(QtCore.Qt.OtherFocusReason)
         else:
            rv = QtWidgets.QLineEdit(parent)
            def textChanged(txt):
               try:
                  float(txt)
               except Exception, e:
                  item.invalid = True
                  item.errmsg = "Invalid value for item '%s': %s" % (item.fullname(), e)
                  # if text is not empty, reset to original value
                  if txt:
                     rv.setText(str(item.data))
               else:
                  item.invalid = False
            rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setFltEditorData)
         rv.setProperty("setModelData", self.setFltModelData)
         return rv

      def createStrEditor(self, parent, item):
         if item.type.choices is not None:
            rv = QtWidgets.QComboBox(parent)
            rv.addItems(sorted(item.type.choices))
            rv.setEditable(not item.type.strict)
         else:
            rv = QtWidgets.QLineEdit(parent)
            def textChanged(txt):
               if item.type.matches is not None:
                  item.invalid = (not item.type.matches.match(txt))
                  if item.invalid:
                     item.errmsg = "Invalid value for item '%s': Does't match '%s'" % (item.fullname(), item.type.matches.pattern)
               else:
                  item.invalid = False
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
               item.invalid = True
               item.errmsg = "Invalid class value for item %s: %s" % (item.fullname(), e)
            else:
               item.invalid = False
         rv.textChanged.connect(textChanged)
         rv.setProperty("setEditorData", self.setClassEditorData)
         rv.setProperty("setModelData", self.setClassModelData)
         return rv

      def setEditorData(self, widget, modelIndex):
         item = modelIndex.internalPointer()
         func = widget.property("setEditorData")
         if func:
            func(widget, item)

      def setMappingKeyEditorData(self, widget, item):
         widget.setText(str(item.key))

      def setOrEditorData(self, widget, item):
         if isinstance(item.data, bool):
            s = ("true" if item.data else "false")
         elif item.data is None:
            # Can't this be a valid string value too?
            s = "none"
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
               fld = widget.findChild(QtWidgets.QLineEdit, "field")
               sld = widget.findChild(QtWidgets.QSlider, "slider")
               sld.setValue(item.data)
            else:
               fld = widget
            fld.setText(str(item.data))
            fld.selectAll()
            #fld.setFocus(QtCore.Qt.OtherFocusReason)

      def setFltEditorData(self, widget, item):
         if item.type.min is not None and item.type.max is not None:
            fld = widget.findChild(QtWidgets.QLineEdit, "field")
            sld = widget.findChild(QtWidgets.QSlider, "slider")
            sld.setValue(int(math.floor(0.5 + item.data * self.sldscl)))
         else:
            fld = widget
         fld.setText(str(item.data))
         fld.selectAll()
         #fld.setFocus(QtCore.Qt.OtherFocusReason)

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
         if not item.invalid:
            func = widget.property("setModelData")
            if func:
               func(widget, model, modelIndex)
         else:
            # Maybe emit a message?
            pass

      def setMappingKeyModelData(self, widget, model, modelIndex):
         model.setData(modelIndex, eval(widget.text()), QtCore.Qt.EditRole)

      def setOrModelData(self, widget, model, modelIndex):
         s = widget.text()

         item = modelIndex.internalPointer()
         values = self._getValidOrValues(s, item)

         if len(values) > 1:
            idx = -1
            dlg = OrTypeChoiceDialog([v[0] for v in values])
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
               for i in xrange(len(values)):
                  if dlg.typename == values[i][0]:
                     idx = i
                     break
            if idx != -1:
               values = [values[idx]]

         if len(values) == 1:
            _, v = values[0]
            model.setData(modelIndex, v, QtCore.Qt.EditRole)

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
               fld = widget.findChild(QtWidgets.QLineEdit, "field")
            else:
               fld = widget
            data = long(fld.text())
         model.setData(modelIndex, data, QtCore.Qt.EditRole)

      def setFltModelData(self, widget, model, modelIndex):
         item = modelIndex.internalPointer()
         if item.type.min is not None and item.type.max is not None:
            fld = widget.findChild(QtWidgets.QLineEdit, "field")
         else:
            fld = widget
         data = float(fld.text())
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
         try:
            data.string_to_value(widget.text())
            model.setData(modelIndex, data, QtCore.Qt.EditRole)
         except:
            pass

      def updateEditorGeometry(self, widget, viewOptions, modelIndex):
         widget.setGeometry(viewOptions.rect)


   class Model(QtCore.QAbstractItemModel):
      internallyRebuilt = QtCore.Signal()
      dataChanged2Args = QtCore.Signal(QtCore.QModelIndex, QtCore.QModelIndex)

      def __init__(self, data, parent=None):
         super(Model, self).__init__(parent)
         # A little hacky but how else?
         if IsPySide2():
            self._org_data_changed = self.dataChanged
            self.dataChanged = self.dataChanged2Args
            self.dataChanged.connect(self.__emitDataChanged)
         self._headers = ["Name", "Value"]
         self._rootItem = None
         self._orgData = None
         self._buildItemsTree(data)

      def __emitDataChanged(self, index1, index2):
         self._org_data_changed.emit(index1, index2, [])

      def _buildItemsTree(self, data=None):
         if data is not None:
            self._orgData = das.copy(data)
         if self._rootItem:
            self._rootItem.update(self._rootItem.data if data is None else data)
         elif data is not None:
            self._rootItem = ModelItem("<root>", data)

      def getIndexData(self, index):
         if index.isValid():
            item = index.internalPointer()
            return item.data
         else:
            return None

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

            if item.parent and not item.parent.mapping and item.parent.orderable:
               flags = flags | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

            if item.compound  and not item.mapping and item.orderable:
               flags = flags | QtCore.Qt.ItemIsDropEnabled

            if index.column() == 0:
               flags = flags | QtCore.Qt.ItemIsEnabled
               # flags = flags | QtCore.Qt.ItemIsUserCheckable
               if item.parent:
                  if item.parent.mapping and item.parent.mappingkeytype is not None:
                     flags = flags | QtCore.Qt.ItemIsEditable

            elif index.column() == 1:
               if not item.compound:
                  flags = flags | QtCore.Qt.ItemIsEnabled
               # any other cases?
               if item.editable:
                  flags = flags | QtCore.Qt.ItemIsEditable
               
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

      def getChildren(self, index):
         if not index.isValid():
            return ([] if self._rootItem is None else [self._rootItem])
         else:
            item = index.internalPointer()
            return item.children

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
            if not item.compound:
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

         if role == QtCore.Qt.DisplayRole and index.column() == 1:
            rv = "    " + rv

         return rv

      def _setRawData(self, index, value):
         structureChanged = False
         item = index.internalPointer()

         oldvalue = item.data
         try:
            item.data = value
         except Exception, e:
            print("Try to set invalid value to '%s'" % item.fullname())
         else:
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
            return False

         elif role == QtCore.Qt.EditRole:
            if index.column() == 0:
               # except for Dict keys!
               print("Set key value!")
               return False

            structureChanged = self._setRawData(index, value)

            if Debug:
               das.pprint(self._rootItem.data)

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
               if Debug:
                  das.pprint(self._rootItem.data)
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
               self._setRawData(self.parent(tgtindex), seq)
               if Debug:
                  das.pprint(self._rootItem.data)
               self.rebuild()
               self.internallyRebuilt.emit()
            else:
               return False

         return True


   class Editor(QtWidgets.QTreeView):
      def __init__(self, data, parent=None):
         super(Editor, self).__init__(parent)
         self.model = Model(data, parent=self)
         self.delegate = ModelItemDelegate(parent=self)
         self.setModel(self.model)
         self.expandedState = {}
         self.checkedState = {}
         self.setItemDelegate(self.delegate)
         QtCompat.setSectionResizeMode(self.header(), QtWidgets.QHeaderView.ResizeToContents)
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
         self.collapsed.connect(self.onItemCollapsed)
         self.expanded.connect(self.onItemExpanded)

      def mousePressEvent(self, event):
         if event.button() == QtCore.Qt.RightButton:
            event.accept()
            menu = QtWidgets.QMenu(self)
            gpos = QtGui.QCursor.pos()
            pos = self.viewport().mapFromGlobal(gpos)
            modelIndex = self.indexAt(pos)
            item = (None if (modelIndex is None or not modelIndex.isValid()) else modelIndex.internalPointer())
            # Maybe more:
            # Container > Add
            #           > Remove
            actionExpandUnder = menu.addAction("Expand Under")
            actionExpandUnder.setEnabled(True if item and item.compound else False)
            actionExpandUnder.triggered.connect(self.makeOnExpandUnder(modelIndex))
            actionCollapseUnder = menu.addAction("Collapse Under")
            actionCollapseUnder.setEnabled(True if item and item.compound else False)
            actionCollapseUnder.triggered.connect(self.makeOnCollapseUnder(modelIndex))
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

      def makeOnExpandUnder(self, index):
         def _callback(*args):
            self.expandUnder(index)
         return _callback

      def expandUnder(self, index):
         if index.isValid():
            self.setExpanded(index, True)
            nr = self.model.rowCount(index)
            for r in xrange(nr):
               self.expandUnder(self.model.index(r, 0, index))

      def onCollapseAll(self):
         self.collapseAll()
         self.resetExpandedState()

      def makeOnCollapseUnder(self, index):
         def _callback(*args):
            self.collapseUnder(index)
         return _callback

      def collapseUnder(self, index):
         if index.isValid():
            self.setExpanded(index, False)
            nr = self.model.rowCount(index)
            for r in xrange(nr):
               self.collapseUnder(self.model.index(r, 0, index))

      def resetCheckedState(self, index=None):
         if index is None:
            index = QtCore.QModelIndex()
            self.checkedState = {}
         else:
            k = self.getItemKey(index)
            if k is not None:
               self.checkedState[k] = (self.model.data(index, QtCore.Qt.CheckStateRole) == QtCore.Qt.Checked)

         nr = self.model.rowCount(index)
         for r in xrange(nr):
            self.restoreCheckedState(index=self.model.index(r, 0, index))

      def restoreCheckedState(self, index=None):
         if index is None:
            index = QtCore.QModelIndex()
         else:
            k = self.getItemKey(index)
            if k is not None:
               checked = (QtCore.Qt.Checked if self.checkedState.get(k, False) else QtCore.Qt.Unchecked)
               self.model.setData(index, checked, QtCore.Qt.CheckStateRole)

         nr = self.model.rowCount(index)
         for r in xrange(nr):
            self.restoreCheckedState(index=self.model.index(r, 0, index))

      def onContentChanged(self, topLeft, bottomRight):
         self.resetCheckedState()

