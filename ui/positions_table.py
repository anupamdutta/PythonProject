"""
Professional Positions & Live MTM Tracker Table with Interactive Resizable Headers
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont
from engine.models import Position


class PositionsWidget(QWidget):
    close_position_requested = pyqtSignal(str)   # pos_key
    close_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Top Bar
        top_bar = QHBoxLayout()
        title = QLabel("OPEN POSITIONS BOOK")
        title.setStyleSheet("font-weight: 800; color: #8b96ad; font-size: 11px; letter-spacing: 0.8px;")

        self.exit_all_btn = QPushButton("EXIT ALL")
        self.exit_all_btn.setObjectName("ExitAllBtn")
        self.exit_all_btn.setFixedHeight(26)
        self.exit_all_btn.clicked.connect(self.close_all_requested.emit)

        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(self.exit_all_btn)
        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Prod", "Symbol", "Net Qty", "Avg Buy", "Avg Sell", "Bid", "Ask", "LTP",
            "Realized P&L", "Unrealized MTM", "Action"
        ])
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Flexible interactive resizable headers
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        for i in range(11):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.table.setColumnWidth(0, 65)   # Prod
        self.table.setColumnWidth(1, 210)  # Symbol
        self.table.setColumnWidth(2, 75)   # Net Qty
        self.table.setColumnWidth(3, 85)   # Avg Buy
        self.table.setColumnWidth(4, 85)   # Avg Sell
        self.table.setColumnWidth(5, 80)   # Bid
        self.table.setColumnWidth(6, 80)   # Ask
        self.table.setColumnWidth(7, 80)   # LTP
        self.table.setColumnWidth(8, 95)   # Realized P&L
        self.table.setColumnWidth(9, 105)  # Unrealized MTM
        self.table.setColumnWidth(10, 80)  # Action

        layout.addWidget(self.table)

    def update_positions(self, positions: dict):
        """Refreshes positions list and live MTM."""
        active_positions = {k: p for k, p in positions.items() if p.net_qty != 0 or p.realized_pnl != 0}

        self.table.setRowCount(0)
        mono_font = QFont("JetBrains Mono", 10)
        bold_mono = QFont("JetBrains Mono", 10, QFont.Weight.Bold)

        for pos_key, pos in active_positions.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 0: Product
            prod_item = QTableWidgetItem(pos.product.value)
            prod_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            prod_item.setFont(bold_mono)
            self.table.setItem(row, 0, prod_item)

            # 1: Symbol
            sym_item = QTableWidgetItem(pos.symbol)
            sym_item.setFont(bold_mono)
            self.table.setItem(row, 1, sym_item)

            # 2: Net Qty
            qty_item = QTableWidgetItem(f"{pos.net_qty:+d}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_color = QColor("#00e676") if pos.net_qty > 0 else (QColor("#ff5252") if pos.net_qty < 0 else QColor("#8b96ad"))
            qty_item.setForeground(qty_color)
            qty_item.setFont(bold_mono)
            self.table.setItem(row, 2, qty_item)

            # 3: Avg Buy Price
            buy_p = f"{pos.avg_buy_price:.2f}" if pos.avg_buy_price > 0 else "-"
            buy_item = QTableWidgetItem(buy_p)
            buy_item.setFont(mono_font)
            buy_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, buy_item)

            # 4: Avg Sell Price
            sell_p = f"{pos.avg_sell_price:.2f}" if pos.avg_sell_price > 0 else "-"
            sell_item = QTableWidgetItem(sell_p)
            sell_item.setFont(mono_font)
            sell_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, sell_item)

            # 5: Bid
            bid_p = f"{pos.current_bid:.2f}" if pos.current_bid > 0 else "-"
            bid_item = QTableWidgetItem(bid_p)
            bid_item.setFont(mono_font)
            bid_item.setForeground(QColor("#4fc3f7"))
            bid_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, bid_item)

            # 6: Ask
            ask_p = f"{pos.current_ask:.2f}" if pos.current_ask > 0 else "-"
            ask_item = QTableWidgetItem(ask_p)
            ask_item.setFont(mono_font)
            ask_item.setForeground(QColor("#ff8a80"))
            ask_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, ask_item)

            # 7: LTP
            ltp_item = QTableWidgetItem(f"{pos.current_ltp:.2f}")
            ltp_item.setFont(bold_mono)
            ltp_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 7, ltp_item)

            # 8: Realized P&L
            real_item = QTableWidgetItem(f"{pos.realized_pnl:+,.2f}")
            real_item.setFont(bold_mono)
            real_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            real_color = QColor("#00e676") if pos.realized_pnl > 0 else (QColor("#ff5252") if pos.realized_pnl < 0 else QColor("#8b96ad"))
            real_item.setForeground(real_color)
            self.table.setItem(row, 8, real_item)

            # 9: Unrealized MTM
            unreal_item = QTableWidgetItem(f"{pos.unrealized_pnl:+,.2f}")
            unreal_item.setFont(bold_mono)
            unreal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            unreal_color = QColor("#00e676") if pos.unrealized_pnl > 0 else (QColor("#ff5252") if pos.unrealized_pnl < 0 else QColor("#8b96ad"))
            unreal_item.setForeground(unreal_color)
            self.table.setItem(row, 9, unreal_item)

            # 10: Action button
            if pos.net_qty != 0:
                exit_btn = QPushButton("EXIT")
                exit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #c62828; color: white; font-size: 11px;
                        font-weight: 800; padding: 3px 8px; border-radius: 3px;
                    }
                    QPushButton:hover { background-color: #b71c1c; }
                """)
                exit_btn.setFixedHeight(26)
                exit_btn.clicked.connect(lambda _, k=pos_key: self.close_position_requested.emit(k))
                self.table.setCellWidget(row, 10, exit_btn)
            else:
                closed_lbl = QLabel("CLOSED")
                closed_lbl.setStyleSheet("color: #7d879e; font-size: 10px; font-weight: bold;")
                closed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setCellWidget(row, 10, closed_lbl)
