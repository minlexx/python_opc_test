import sys
import sip
import time

import opc_helper

from PyQt5.QtCore import PYQT_VERSION_STR, Qt, pyqtSignal, pyqtSlot, QTimer, QModelIndex
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, \
    QLabel, QLineEdit, QListWidget, QPushButton, QSplitter, \
    QTableWidget, QTableWidgetItem, \
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class ServerSelectDialog(QDialog):
    def __init__(self, parent=None):
        super(ServerSelectDialog, self).__init__(parent)
        # out
        self.selected_server = None
        self.selected_comp_name = ''
        #
        self.layout = QVBoxLayout()
        self.layout1 = QHBoxLayout()
        self.layout2 = QHBoxLayout()
        self.layout3 = QHBoxLayout()
        # 1
        self.labelCompName = QLabel('Computer name (empty for localhost):', self)
        self.editCompName = QLineEdit(self)
        self.btnRefresh = QPushButton('List OPC servers', self)
        self.layout1.addWidget(self.labelCompName)
        self.layout1.addWidget(self.editCompName)
        self.layout1.addWidget(self.btnRefresh)
        # 2
        self.serversList = QListWidget(self)
        self.layout2.addWidget(self.serversList)
        # 3
        self.btnOK = QPushButton('OK', self)
        self.btnCancel = QPushButton('Cancel', self)
        self.layout3.addStretch()
        self.layout3.addWidget(self.btnOK)
        self.layout3.addWidget(self.btnCancel)
        self.layout3.addStretch()
        # final
        self.layout.addLayout(self.layout1)
        self.layout.addLayout(self.layout2)
        self.layout.addLayout(self.layout3)
        self.setLayout(self.layout)
        self.setWindowTitle('Select OPC server to connect to')
        #
        self.btnOK.clicked.connect(self.onClickedOK)
        self.btnCancel.clicked.connect(self.reject)
        self.btnRefresh.clicked.connect(self.onClickedRefresh)
        self.serversList.doubleClicked.connect(self.onListDoubleClick)
        #
        self.servers_list = []
        #
        self.onClickedRefresh()

    @pyqtSlot()
    def onClickedOK(self):
        sel_item = self.serversList.currentRow()
        if sel_item < 0:
            return
        self.selected_server = self.servers_list[sel_item]
        self.selected_comp_name = self.editCompName.text()
        self.accept()

    @pyqtSlot()
    def onClickedRefresh(self):
        self.serversList.clear()
        comp_name = self.editCompName.text()
        try:
            self.servers_list = opc_helper.opc_enum_query(comp_name)
        except OSError as ose:
            sys.stderr.write('OSError: ' + str(ose))
        for srv in self.servers_list:
            s = '{0} ({1})'.format(srv['desc'], srv['progid'])
            self.serversList.addItem(s)

    @pyqtSlot(QModelIndex)
    def onListDoubleClick(self, idx: QModelIndex):
        print('onListDoubleClick')
        self.onClickedOK()


class OTMainWindow(QWidget):
    def __init__(self, parent=None):
        super(OTMainWindow, self).__init__(parent, Qt.Window)
        self.setWindowTitle('OPC Python Tester')
        self.layout = QVBoxLayout()
        #
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabel('OPC server tree')
        self.tree_root = QTreeWidgetItem()
        self.tree_root.setText(0, 'not connected')
        self.tree.addTopLevelItem(self.tree_root)
        self.tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        #
        self.table = QTableWidget(self)
        self.table.setRowCount(0)
        self.table_column_labels = [
            'item_id', 'value', 'type', 'access', 'quality', 'timestamp']
        self.table.setColumnCount(len(self.table_column_labels))
        self.table.setHorizontalHeaderLabels(self.table_column_labels)
        self.table.horizontalHeader().setStretchLastSection(True)
        #
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        self.layout.addWidget(self.splitter)
        # final
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.table)
        self.splitter.setSizes([150, 300])
        self.setLayout(self.layout)

        # self.opcsrv = None
        self.cur_server_info = {}
        self.cur_comp_name = ''
        self.watched_itemids = []

        self.ssdialog = ServerSelectDialog(self)
        ssel_ret = self.ssdialog.exec_()
        if ssel_ret == QDialog.Accepted:
            self.do_connect(self.ssdialog.selected_server, self.ssdialog.selected_comp_name)
        else:
            print('Connection cancelled')

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.timer.start(1000)  # every 1 second

    def do_connect(self, srv_info: dict, comp_name: str):
        print('Connecting to "{0}" ({1}) on comp: {2}...'.format(
            srv_info['desc'], srv_info['guid'], comp_name))
        self.opcsrv = opc_helper.opc_connect(srv_info['guid'], comp_name)
        if self.opcsrv is None:
            return
        self.cur_comp_name = comp_name
        self.cur_server_info = srv_info
        print(self.opcsrv.get_status())
        self.fill_tree()

    def fill_tree(self):
        self.tree.clear()
        if self.opcsrv is None:
            return
        self.tree_root = QTreeWidgetItem(self.tree)
        self.tree_root.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        root_title = '{0}'.format(self.cur_server_info['desc'])
        if self.cur_comp_name != '':
            root_title = '{0} ({1})'.format(self.cur_server_info['desc'], self.cur_comp_name)
        self.tree_root.setText(0, root_title)
        self.tree.addTopLevelItem(self.tree_root)
        server_tree = self.opcsrv.browse(flat=False)
        #
        for oitem in server_tree:
            self.fill_item(oitem, self.tree_root)

    def fill_item(self, item: dict, parent: QTreeWidgetItem):
        tree_item = QTreeWidgetItem()
        tree_item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        tree_item.setText(0, item['name'])
        if item['children'] is None:
            # set userdata = item_id only if this IS a LEAF node
            tree_item.setData(0, Qt.UserRole, item['item_id'])  # column, role, data
        parent.addChild(tree_item)
        # recurse into children
        if item['children'] is not None:
            for oitem in item['children']:
                self.fill_item(oitem, tree_item)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        # void	itemDoubleClicked(QTreeWidgetItem * item, int column)
        # virtual QVariant	data(int column, int role) const
        item_data = item.data(0, Qt.UserRole)
        if item_data is None:
            return
        item_id = str(item_data)
        print('Double click on [{0}]'.format(item_id))
        self.opcsrv.get_item(item_id)
        if item_id not in self.watched_itemids:
            self.watched_itemids.append(item_id)

    @pyqtSlot()
    def on_timer_timeout(self):
        num_items = len(self.watched_itemids)
        self.table.setRowCount(num_items)
        i = 0
        while i < num_items:
            item_id = self.watched_itemids[i]
            item_value = self.opcsrv.get_item(item_id)
            item_info = self.opcsrv.get_item_info(item_id)
            #
            twi = QTableWidgetItem(str(item_id))
            self.table.setItem(i, 0, twi)
            #
            twi = QTableWidgetItem(str(item_value))
            self.table.setItem(i, 1, twi)
            #
            twi = QTableWidgetItem(str(item_info['type']))
            self.table.setItem(i, 2, twi)
            #
            twi = QTableWidgetItem(str(item_info['access_rights']))
            self.table.setItem(i, 3, twi)
            #
            twi = QTableWidgetItem(str(item_info['quality']))
            self.table.setItem(i, 4, twi)
            #
            ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item_info['timestamp']))
            twi = QTableWidgetItem(str(ts_str))
            self.table.setItem(i, 5, twi)
            #
            i += 1


class MyApplication(QApplication):
    def __init__(self, argv):
        super(MyApplication, self).__init__(argv)
        self.mainwindow = None

    def create_window(self):
        # create main window and keep reference to it
        self.mainwindow = OTMainWindow()
        self.mainwindow.show()
        pass


if __name__ == "__main__":
    print('Using opc_helper version ', opc_helper.opc_version())
    print('Using PyQt5 version: ', PYQT_VERSION_STR)
    if not opc_helper.initialize_com():
        sys.stderr.write('Failed to initialize COM!\n')
        sys.exit(1)
    #
    # fix PyQt crashes during program exit?
    sip.setdestroyonexit(False)
    app = MyApplication(sys.argv)
    app.setApplicationName('opc_test')
    app.setApplicationVersion('0.1')
    app.setApplicationDisplayName('OPC Test')
    app.create_window()
    retcode = app.exec_()  # Qt event loop!
    #
    app.mainwindow.close()
    app.mainwindow = None
    #
    opc_helper.uninitialize_com()
    #
    sys.exit(retcode)
