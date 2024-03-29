import sys
import threading
import json
import ast
import datetime
# from itertools import *

import rclpy
from rclpy.node import Node

from PyQt5 import (QtWidgets, QtCore, QtGui)
from PyQt5.QtCore import (Qt)

from std_msgs.msg import String
import sp_msgs.srv


class Callbacks():
    info = {}
    cmd = {}

    trigger_node = None
    trigger_ui = None



class Ros2Node(Node, Callbacks):
    def __init__(self):
        Node.__init__(self, "sp_ui")
        Callbacks.__init__(self)

        Callbacks.trigger_node = self.trigger

        self.subscriber = self.create_subscription(
            String,
            "/sp/state_flat",
            self.sp_cmd_callback,
            10)

        self.state_publisher = self.create_client(
            sp_msgs.srv.Json,
            "/sp/set_state")

        self.get_logger().info("Sequence Planner UI, up and running")

    def trigger(self):
        x = sp_msgs.srv.Json.Request()
        x.json = json.dumps(Callbacks.cmd)
        self.state_publisher = self.create_client(
            sp_msgs.srv.Json,
            "/sp/set_state")
        res = self.state_publisher.call_async(x)

    def sp_cmd_callback(self, data):
        # print("ui got data: " + str(data.data))
        try:
            Callbacks.info = json.loads(data.data)
        except json.JSONDecodeError as error:
            self.get_logger().error('error in sp_cmd_callback: "%s"' % error)

        #self.get_logger().info('info: "%s"' % data)
        if Callbacks.trigger_ui:
            Callbacks.trigger_ui()

        #self.state_publisher.publish(Callbacks.cmd)


# workaround for missing .setRecursiveFilteringEnabled(True)
class RecursiveFilterProxyModel(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        if (super(RecursiveFilterProxyModel, self).filterAcceptsRow(source_row, source_parent)):
            return True

        if (self.hasAcceptedChildren(source_row, source_parent)):
            return True

        return False

    def hasAcceptedChildren(self, source_row, source_parent):
        model = self.sourceModel()
        sourceIndex = model.index(source_row, 0, source_parent)
        if not (sourceIndex.isValid()):
            return False

        childCount = model.rowCount(sourceIndex)
        if (childCount == 0):
            return False

        for i in range (childCount):
            if (super(RecursiveFilterProxyModel, self).filterAcceptsRow(i, sourceIndex)):
                return True

            if (self.hasAcceptedChildren(i, sourceIndex)):
                return True

        return False


class Window(QtWidgets.QWidget, Callbacks):
    triggerSignal = QtCore.pyqtSignal()

    def __init__(self):
        Callbacks.__init__(self)
        QtWidgets.QWidget.__init__(self, None)
        #self.count = 0

        self.state_model = QtGui.QStandardItemModel(self)
        #self.state_model_proxy = QtCore.QSortFilterProxyModel(self)
        # workaround for missing .setRecursiveFilteringEnabled(True)
        self.state_model_proxy = RecursiveFilterProxyModel(self)

        Callbacks.trigger_ui = self.trigger
        self.triggerSignal.connect(self.update_state_variables)
        self.state_map = {}

        grid = QtWidgets.QGridLayout(self)
        grid.addWidget(self.info_widget())
        grid.addWidget(self.tree_widget())
        self.setLayout(grid)
        self.setWindowTitle("Sequence Planner Control UI")
        self.resize(750, 1000)

        self.init = True

    def split_path(self, s):
        path = s.split("/")
        path = list(filter(None, path))
        res = []
        if len(path) > 0:
            aggr = path[0]
            res = [(None, aggr)]
            for p in path[1:]:
                x = aggr
                aggr = aggr + "/" + p
                res.append((x, aggr))

        return res

    def get_leaf_name(self, path):
        return path.split("/")[-1]

    def get_parent(self, path):
        if path not in self.state_map:
            return self.state_model.invisibleRootItem()
        else:
            p = self.state_map[path]
            return self.state_model.itemFromIndex(p)

    def insert_parent(self, parent, name):
        if name not in self.state_map:
            item = QtGui.QStandardItem()
            n = self.get_leaf_name(name)
            item.setData(n, Qt.DisplayRole)
            item.setData(name, Qt.ToolTipRole)
            parent.appendRow([item])
            self.state_map[name] = item.index()

    def insert_variable(self, parent, name, value):
        if name not in self.state_map:
            item = QtGui.QStandardItem()
            n = self.get_leaf_name(name)
            item.setData(n, Qt.DisplayRole)
            item.setData(name, Qt.ToolTipRole)
            value_item = QtGui.QStandardItem()
            value_item.setData(value, Qt.DisplayRole)

            set_item = QtGui.QStandardItem()
            set_item.setData("", Qt.EditRole)
            item.setData(name, Qt.ToolTipRole)

            parent.appendRow([item, value_item, set_item])
            self.state_map[name] = item.index()


    def update_state_variables(self):
        if self and self.init:
            for p, v in Callbacks.info.items():
                path = self.split_path(p)
                if len(path) == 0:
                    continue

                # add parents
                for (p_of_p, p) in path[:-1]:
                    if not p_of_p:
                        self.insert_parent(self.state_model.invisibleRootItem(), p)
                    else:
                        p_of_p_item = self.state_model.itemFromIndex(self.state_map[p_of_p])
                        self.insert_parent(p_of_p_item, p)


                # add variable
                (parent, name) = path[-1]
                value = v
                try:
                    value = json.loads(v.value_as_json)
                except Exception as e:
                    pass

                if isinstance(value, dict):
                    secs = value.get("secs_since_epoch")
                    nanos = value.get("nanos_since_epoch")
                    if secs != None and nanos != None:
                        value = str(datetime.datetime.fromtimestamp(secs + nanos / 10**9))

                if name not in self.state_map:
                    self.insert_variable(self.get_parent(parent), name, value)
                else:
                    index = self.state_map[name]
                    #value_index = index.siblingAtColumn(1)
                    value_index = index.sibling(index.row(), 1)
                    value_item = self.state_model.itemFromIndex(value_index)

                    if value_item is not None and value_item.data(Qt.DisplayRole) != value:
                        value_item.setData(value, Qt.DisplayRole)
                        value_item.setData(value, Qt.ToolTipRole)

            #self.mode.setText(str(Callbacks.info["/mode"]))

            #self.count += 1

            #i = self.state_model.invisibleRootItem().index()
            #self.tree.dataChanged(i, i)


    def trigger(self):
        self.triggerSignal.emit()

    def info_widget(self):
        info_l = QtWidgets.QGridLayout(self)

        #pub state: Vec<sp_messages::msg::State>,
        #   pub plans: Vec<sp_messages::msg::PlanningInfo>,
        #pub mode: std::string::String,
        #pub forced_state: Vec<sp_messages::msg::State>,
        #pub forced_goal: Vec<sp_messages::msg::ForcedGoal>,


        self.mode = QtWidgets.QLabel("no info yet")
        info_l.addWidget(QtWidgets.QLabel("runner mode: "), 1, 0)
        info_l.addWidget(self.mode, 1, 1)

        box = QtWidgets.QGroupBox("Runner info")
        box.setLayout(info_l)
        return box

    def tree_widget(self):
        self.state_model.setHorizontalHeaderLabels(['path', 'value', 'set'])
        # self.state_model_proxy.setRecursiveFilteringEnabled(True)
        self.state_model_proxy.setFilterRole(Qt.ToolTipRole)
        self.state_model_proxy.setSourceModel(self.state_model)

        tree_l = QtWidgets.QGridLayout(self)
        filter_box = QtWidgets.QLineEdit("")
        def filter_changed(text):
            regex = "^.*{}.*".format(text)
            self.state_model_proxy.setFilterRegExp(QtCore.QRegExp(regex, Qt.CaseInsensitive))
            self.tree.expandAll()

        filter_box.textChanged.connect(filter_changed)
        tree_l.addWidget(filter_box, 1, 0)

        expand_button = QtWidgets.QPushButton("expand")
        def expand_button_clicked():
            print("expand")
            self.tree.expandAll()

        expand_button.clicked.connect(expand_button_clicked)
        tree_l.addWidget(expand_button, 1, 1)

        collaps_button = QtWidgets.QPushButton("collaps")
        def collaps_button_clicked():
            print("collapse")
            self.tree.collapseAll()

        collaps_button.clicked.connect(collaps_button_clicked)
        tree_l.addWidget(collaps_button, 1, 2)

        set_state_button = QtWidgets.QPushButton("set_state")
        def set_state_button_clicked():
            print("set_state")
            set_it = {}
            for path, index in self.state_map.items():
                #set_index = index.siblingAtColumn(2)
                set_index = index.sibling(index.row(), 2)
                set_item = self.state_model.itemFromIndex(set_index)
                if set_item:
                    set_value = set_item.data(Qt.EditRole)
                    if set_value == "true" or set_value == "t" or set_value == "T":
                        set_it[path]= True
                    elif set_value == "false" or set_value == "f" or set_value == "F":
                        set_it[path]= False
                    elif set_value:
                        try:
                            val = ast.literal_eval(set_value)
                            set_it[path]= val
                        except ValueError:
                            set_it[path]= set_value

                    set_item.setData("", Qt.EditRole)

            print("SET STATE:")
            print(set_it)
            if set_it:
                Callbacks.cmd = set_it
                Callbacks.trigger_node()

        set_state_button.clicked.connect(set_state_button_clicked)
        tree_l.addWidget(set_state_button, 1, 3)

        self.tree = QtWidgets.QTreeView(self)

        self.tree.setModel(self.state_model_proxy)
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 400)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        tree_l.addWidget(self.tree, 2, 0, 1, 4)

        box = QtWidgets.QGroupBox("State")
        box.setLayout(tree_l)
        return box


def main(args=None):

    def launch_node():
        def launch_node_callback_local():
            rclpy.init(args=args)
            node = Ros2Node()
            rclpy.spin(node)
            node.destroy_node()
            rclpy.shutdown()
        t = threading.Thread(target=launch_node_callback_local)
        t.daemon = True
        t.start()

    # Window has to be in the main thread
    def launch_window():
        app = QtWidgets.QApplication(sys.argv)
        clock = Window()
        clock.show()
        sys.exit(app.exec_())

    launch_node()
    launch_window()

if __name__ == '__main__':
    main()
