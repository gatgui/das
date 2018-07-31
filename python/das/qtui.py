NoUI = False

try:
   from Qt import QtCore
   from Qt import QtGui
   from Qt import QtWidget
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
      def __init__(self, name, row, data, parent=None):
         super(ModelItem, self).__init__()
         self.row = row
         self.name = name
         self.parent = parent
         self.update(data)

      def update(self, data):
         self.children = []
         self.compound = False
         self.resizable = False
         self.data = data
         self.schema_type = None

         if self.data is not None:
            # Not necessarily here...
            self.schema_type = data._get_schema_type()

            if isinstance(self.schema_type, das.Sequence):
               self.compound = True
               self.resizable = True
               for i in xrange(len(self.data)):
                  itemname = "%s[%d]" % (self.name, i)
                  itemdata = self.data[i]
                  self.children.append(ModelItem(itemname, i, itemdata, parent=self))

            elif isinstance(self.schema_type, das.Tuple):
               self.compound = True
               self.resizable = False
               for i in xrange(len(self.data)):
                  itemname = "%s[%d]" % (self.name, i)
                  itemdata = self.data[i]
                  self.children.append(ModelItem(itemname, i, itemdata, parent=self))

            elif isinstance(self.schema_type, das.Set):
               self.compound = True
               self.resizable = True
               i = 0
               for itemdata in self.data:
                  itemname = "%s[%d]" % (self.name, i)
                  self.children.append(ModelItem(itemname, i, itemdata, parent=self))
                  i += 1

            elif isinstance(self.schema_type, das.Struct):
               self.compound = True
               self.resizable = False
               i = 0
               for k, v in self.data.iteritems():
                  self.children.append(ModelItem(k, i, v, parent=self))
                  i += 1

            elif isinstance(self.schema_type, das.Dict):
               self.compound = True
               self.resizable = True
               i = 0
               for k, v in self.data.iteritems():
                  self.children.append(ModelItem(k, i, v, parent=self))
                  i += 1


   class ModelItemDelegate(QtWidgets.QItemDelegate):
      def __init__(self, parent=None):
         super(ModelItemDelegate, self).__init__(parent)

      def createEditor(self, parent, viewOptions, modelIndex):
         pass

      def setEditorData(self, widget, modelIndex):
         pass

      def setModelData(self, widget, model, modelIndex):
         pass

      def updateEditorGeometry(self, widget, viewOptions, modelIndex):
         widget.setGeometry(viewOptions.rect)


   class Model(QtCore.QAbstractItemModel):
      def __init__(self, data, parent=None):
         super(Model, self).__init__(parent)
         # A little hacky but how else?
         if IsPySide2():
            self._org_data_changed = self.dataChanged
            self.dataChanged = self.dataChanged2Args
            self.dataChanged.connect(self.__emitDataChanged)
         self.headers = ["Name", "Value"]
         self.editable = ["Value"]
         self.data = data
         self._buildItemsTree()

      def __emitDataChanged(self, index1, index2):
         self._org_data_changed.emit(index1, index2, [])

      def _buildItemsTree(self):
         if self.rootItem:
            self.rootItem.update(self.data)
         else:
            self.rootItem = ModelItem("<root>", 0, self.data)

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
            return flags

      def headerData(self, index, orient, role):
         if orient == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headers[index]
         else:
            return None

      def hasChildren(self, index):
         if not index.isValid():
            return True
         else:
            item = index.internalPointer()
            return (len(item.children) > 0)

      def getChildren(self, index):
         if not index.isValid():
            return [self.rootItem]
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
               return self.createIndex(row, col, self.rootItem)
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

            return True

         return False

      def rowCount(self, index):
         if index.isValid():
            return len(index.internalPointer().children)
         else:
            return 1

      def columnCount(self, index):
         return len(self.headers)


   class Editor(QtWidgets.QTreeView):
      def __init__(self, data, parent=None):
         super(Editor, self).__init__(parent)


