"""
Order Book Table Widget with Flexible Resizable Headers
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont
from engine.models import Order, OrderStatus, OrderAction


class OrdersWidget(QWidget):
    cancel_order_requested = pyqtSignal(str)  # order_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("ORDER BOOK")
        title.setStyleSheet("font-weight: 800; color: #8b96ad; font-size: 11px; letter-spacing: 0.8px;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Time", "Order ID", "Symbol", "Side", "Type", "Qty", "Price", "Status", "Action"
        ])
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Flexible interactive resizable headers
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        for i in range(9):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.table.setColumnWidth(0, 80)   # Time
        self.table.setColumnWidth(1, 105)  # Order ID
        self.table.setColumnWidth(2, 210)  # Symbol
        self.table.setColumnWidth(3, 60)   # Side
        self.table.setColumnWidth(4, 75)   # Type
        self.table.setColumnWidth(5, 60)   # Qty
        self.table.setColumnWidth(6, 85)   # Price
        self.table.setColumnWidth(7, 95)   # Status
        self.table.setColumnWidth(8, 75)   # Action

        layout.addWidget(self.table)

    def update_orders(self, orders: list):
        self.table.setRowCount(0)
        mono_font = QFont("JetBrains Mono", 10)
        bold_mono = QFont("JetBrains Mono", 10, QFont.Weight.Bold)

        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Time
            time_str = order.created_at.strftime("%H:%M:%S")
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFont(mono_font)
            self.table.setItem(row, 0, time_item)

            # Order ID
            id_item = QTableWidgetItem(order.order_id)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setFont(mono_font)
            self.table.setItem(row, 1, id_item)

            # Symbol
            sym_item = QTableWidgetItem(order.symbol)
            sym_item.setFont(bold_mono)
            self.table.setItem(row, 2, sym_item)

            # Side (BUY / SELL)
            side_item = QTableWidgetItem(order.action.value)
            side_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            side_color = QColor("#00e676") if order.action == OrderAction.BUY else QColor("#ff5252")
            side_item.setForeground(side_color)
            side_item.setFont(bold_mono)
            self.table.setItem(row, 3, side_item)

            # Type
            type_item = QTableWidgetItem(order.order_type.value)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_item.setFont(mono_font)
            self.table.setItem(row, 4, type_item)

            # Qty
            qty_item = QTableWidgetItem(str(order.quantity))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_item.setFont(mono_font)
            self.table.setItem(row, 5, qty_item)

            # Price
            p_str = f"{order.filled_price:.2f}" if order.status == OrderStatus.COMPLETE else (
                f"{order.price:.2f}" if order.price > 0 else "MKT"
            )
            price_item = QTableWidgetItem(p_str)
            price_item.setFont(mono_font)
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, price_item)

            # Status
            status_item = QTableWidgetItem(order.status.value)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFont(bold_mono)
            if order.status == OrderStatus.COMPLETE:
                status_item.setForeground(QColor("#00e676"))
            elif order.status == OrderStatus.PENDING:
                status_item.setForeground(QColor("#ffb74d"))
            else:
                status_item.setForeground(QColor("#ff5252"))
            self.table.setItem(row, 7, status_item)

            # Action
            if order.status == OrderStatus.PENDING:
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setStyleSheet("background-color: #2b1f0c; color: #ffb74d; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
                cancel_btn.clicked.connect(lambda _, oid=order.order_id: self.cancel_order_requested.emit(oid))
                self.table.setCellWidget(row, 8, cancel_btn)
            else:
                dash_item = QTableWidgetItem("-")
                dash_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 8, dash_item)
