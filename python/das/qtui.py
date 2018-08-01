import das

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
      def __init__(self, name, data, type=None, parent=None, row=0):
         super(ModelItem, self).__init__()
         self.row = row
         self.name = name
         self.parent = parent
         self.update(data, type)

      def __str__(self):
         return "ModelItem(%s, compound=%s, resizable=%s, multi=%s, editable=%s, optional=%s, parent=%s, children=%d)" % (self.name, self.compound, self.resizable, self.multi, self.editable, self.optional, ("None" if not self.parent else self.parent.name), len(self.children))

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
         self.resizable = False
         self.optional = False
         self.editable = False
         self.multi = False
         self.data = data
         self.type = type

         if self.data is not None:
            if self.type is None:
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
                  for i in xrange(len(self.data)):
                     itemname = "%s[%d]" % (self.name, i)
                     itemdata = self.data[i]
                     self.children.append(ModelItem(itemname, itemdata, type=self.type.type, parent=self, row=i))

               elif isinstance(self.type, das.schematypes.Tuple):
                  self.resizable = False
                  for i in xrange(len(self.data)):
                     itemname = "%s[%d]" % (self.name, i)
                     itemdata = self.data[i]
                     self.children.append(ModelItem(itemname, itemdata, type=self.type.types[i], parent=self, row=i))

               elif isinstance(self.type, das.schematypes.Set):
                  self.resizable = True
                  i = 0
                  for itemdata in self.data:
                     itemname = "%s[%d]" % (self.name, i)
                     self.children.append(ModelItem(itemname, itemdata, type=self.type.type, parent=self, row=i))
                     i += 1

               elif isinstance(self.type, (das.schematypes.Struct, das.schematypes.StaticDict)):
                  self.resizable = False
                  self.mappingkeys = {}
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
                     self.children.append(ModelItem(k, v, type=self.type[k], parent=self, row=i))
                     i += 1

               elif isinstance(self.type, (das.schematypes.Dict, das.schematypes.DynamicDict)):
                  self.resizable = True
                  self.mappingkeytype = self.type.ktype
                  i = 0
                  for k in sorted([x for x in self.data.iterkeys()]):
                     v = self.data[k]
                     ks = str(k)
                     vtype = self.type.vtypeOverrides.get(k, self.type.vtype)
                     self.children.append(ModelItem(ks, v, type=vtype, parent=self, row=i))
                     i += 1


   class ModelItemDelegate(QtWidgets.QItemDelegate):
      def __init__(self, parent=None):
         super(ModelItemDelegate, self).__init__(parent)

      def createEditor(self, parent, viewOptions, modelIndex):
         item = modelIndex.internalPointer()
         # Boolean, Integer, Real, String, Or, Empty, Class, Alias?
         # for 'Or' -> string field
         # for 'Empty' -> not editable if only type
         #             -> if inside a Or ... what? Or(String(), Empty())
         #                '' is a valid string... how to set None? (Empty)
         # Class will be a mother fucker too, we need to be able to build it from string
         # and convert value to string too
         # => require 'string_to_value', 'value_to_string' method to edit Class
         return None

      def strToBool(self, s):
         ls = s.lower()
         if ls in ("1", "on", "yes", "true", "0", "off", "no", "false"):
            return (ls in ("1", "on", "yes", "true"))
         else:
            return None

      def boolToStr(self, b):
         return ("true" if b else "false")

      def strToReal(self, s):
         try:
            return float(s)
         except:
            return None

      def realToStr(self, r):
         return str(r)

      def strToInt(self, s):
         try:
            return long(s)
         except:
            return None

      def intToStr(self, i):
         return str(i)

      def setEditorData(self, widget, modelIndex):
         pass

      def setModelData(self, widget, model, modelIndex):
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
         self._data = data
         self._rootItem = None
         self._buildItemsTree()

      def __emitDataChanged(self, index1, index2):
         self._org_data_changed.emit(index1, index2, [])

      def _buildItemsTree(self):
         if self._rootItem:
            self._rootItem.update(self._data)
         else:
            self._rootItem = ModelItem("<root>", self._data)

      def getIndexData(self, index):
         if index.isValid():
            item = index.internalPointer()
            return item.data
         else:
            return None

      def rebuild(self):
         self.beginResetModel()
         self._buildItemsTree()
         self.endResetModel()

      def flags(self, index):
         if not index.isValid():
            return QtCore.Qt.ItemNoFlags
         else:
            flags = QtCore.Qt.NoItemFlags
            flags = flags | QtCore.Qt.ItemIsSelectable
            flags = flags | QtCore.Qt.ItemIsEnabled
            item = index.internalPointer()
            if index.column() == 0:
               # flags = flags | QtCore.Qt.ItemIsUserCheckable
               if item.mappingkeytype is not None:
                  flags = flags | QtCore.Qt.ItemIsEditable
            elif index.column() == 1:
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
               rv = str(item.data)

         if rv is not None and role == QtCore.Qt.DisplayRole:
            # artificially add spaces for more readability
            rv += "  "

         return rv

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
               return False

            item = index.internalPointer()
            if not item.compound:
               # set from parent if it exists
               pass
            else:
               # item.data is a reference
               pass

            structureChanged = False
            # if something added or removed, set to True

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


   class Editor(QtWidgets.QTreeView):
      def __init__(self, data, parent=None):
         super(Editor, self).__init__(parent)
         self.model = Model(data, parent=self)
         #self.delegate = ModelItemDelegate(parent=self)
         self.setModel(self.model)
         self.expandedState = {}
         self.checkedState = {}
         #self.setItemDelegate(self.delegate)
         QtCompat.setSectionResizeMode(self.header(), QtWidgets.QHeaderView.ResizeToContents)
         self.setAnimated(True)
         self.setHeaderHidden(False)
         self.setItemsExpandable(True)
         self.setAllColumnsShowFocus(True)
         self.setRootIsDecorated(True)
         self.setSortingEnabled(False)
         # self.setUniformRowHeights(True)
         self.model.internallyRebuilt.connect(self.restoreExpandedState)
         self.model.dataChanged.connect(self.onContentChanged)
         self.collapsed.connect(self.onItemCollapsed)
         self.expanded.connect(self.onItemExpanded)

      def mousePressEvent(self, event):
         if event.button() == QtCore.Qt.RightButton:
            event.accept()
            menu = QtWidgets.QMenu(self)
            gpos = QtWidgets.QCursor.pos()
            pos = self.viewport().mapFromGlobal(gpos)
            modelIndex = self.indexAt(pos)
            item = (None if (modelIndex is None or not modelIndex.isValid()) else modelIndex.internalPointer())
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
         while item:
            suffix = ("" if k is None else (".%s" % k))
            k = item.name + suffix
            item = item.parent
         return k

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
            self.restoreExpandedState(index=self.model.index(r, 0, index))

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

         nr = self.model.rowCount(parentIndex)
         for r in xrange(nr):
            self.restoreCheckedState(index=self.model.index(r, 0, index))

      def onContentChanged(self, topLeft, bottomRight):
         self.resetCheckedState()

