"""
Order Entry Panel with Level-2 Bid/Ask Execution Display and Compact Responsive Header
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from engine.models import OrderAction, OrderType, ProductType


class OrderPanel(QWidget):
    order_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_symbol: str = "CRUDEOIL26NOV9150PE"
        self.current_exchange: str = "MCX"
        self.current_lot_size: int = 100
        self.current_ltp: float = 505.00
        self.current_bid: float = 504.00
        self.current_ask: float = 506.00
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header Info Card (2-row compact layout so everything fits cleanly)
        info_frame = QFrame()
        info_frame.setObjectName("MetricCard")
        info_vbox = QVBoxLayout(info_frame)
        info_vbox.setContentsMargins(8, 6, 8, 6)
        info_vbox.setSpacing(3)

        # Row 1: Symbol & Exchange
        r1_layout = QHBoxLayout()
        self.symbol_label = QLabel(self.current_symbol)
        self.symbol_label.setStyleSheet("font-weight: 800; font-size: 12px; color: #f5f7fa; font-family: 'JetBrains Mono', monospace;")

        self.exch_badge = QLabel(self.current_exchange)
        self.exch_badge.setStyleSheet("color: #ffb74d; font-weight: 800; font-size: 10px; background: #10131b; padding: 1px 6px; border-radius: 3px;")

        r1_layout.addWidget(self.symbol_label)
        r1_layout.addSpacing(6)
        r1_layout.addWidget(self.exch_badge)
        r1_layout.addStretch()
        info_vbox.addLayout(r1_layout)

        # Row 2: Bid, Ask, LTP (Clean compact monospace font)
        r2_layout = QHBoxLayout()
        self.bid_lbl = QLabel(f"Bid: ₹{self.current_bid:.2f}")
        self.bid_lbl.setStyleSheet("font-weight: 700; font-size: 11px; color: #4fc3f7; font-family: 'JetBrains Mono', monospace;")

        self.ask_lbl = QLabel(f"Ask: ₹{self.current_ask:.2f}")
        self.ask_lbl.setStyleSheet("font-weight: 700; font-size: 11px; color: #ff8a80; font-family: 'JetBrains Mono', monospace;")

        self.ltp_label = QLabel(f"LTP: ₹{self.current_ltp:.2f}")
        self.ltp_label.setStyleSheet("font-weight: 800; font-size: 11px; color: #00e676; font-family: 'JetBrains Mono', monospace;")

        r2_layout.addWidget(self.bid_lbl)
        r2_layout.addSpacing(8)
        r2_layout.addWidget(self.ask_lbl)
        r2_layout.addSpacing(8)
        r2_layout.addWidget(self.ltp_label)
        r2_layout.addStretch()
        info_vbox.addLayout(r2_layout)

        layout.addWidget(info_frame)

        # BUY / SELL Toggle
        action_layout = QHBoxLayout()
        self.buy_radio = QRadioButton("Buy")
        self.buy_radio.setChecked(True)
        self.buy_radio.setStyleSheet("font-weight: 800; color: #00e676; font-size: 12px;")

        self.sell_radio = QRadioButton("Sell")
        self.sell_radio.setStyleSheet("font-weight: 800; color: #ff5252; font-size: 12px;")

        self.action_group = QButtonGroup(self)
        self.action_group.addButton(self.buy_radio)
        self.action_group.addButton(self.sell_radio)
        self.action_group.buttonClicked.connect(self._update_submit_button_style)

        action_layout.addWidget(self.buy_radio)
        action_layout.addWidget(self.sell_radio)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Lots & Quantity calculation row
        qty_layout = QHBoxLayout()
        lots_label = QLabel("Lots:")
        lots_label.setStyleSheet("color: #7d879e; font-weight: 700; font-size: 11px;")
        self.lots_spin = QSpinBox()
        self.lots_spin.setRange(1, 1000)
        self.lots_spin.setValue(1)
        self.lots_spin.setFixedWidth(75)
        self.lots_spin.valueChanged.connect(self._recalculate_estimate)

        self.qty_summary = QLabel(f"Qty: {self.current_lot_size} ({self.lots_spin.value()} x {self.current_lot_size})")
        self.qty_summary.setStyleSheet("color: #7d879e; font-size: 11px; font-weight: 600;")

        qty_layout.addWidget(lots_label)
        qty_layout.addWidget(self.lots_spin)
        qty_layout.addWidget(self.qty_summary)
        qty_layout.addStretch()
        layout.addLayout(qty_layout)

        # Product and Order Type
        type_layout = QHBoxLayout()
        prod_label = QLabel("Product:")
        prod_label.setStyleSheet("color: #7d879e; font-weight: 700; font-size: 11px;")
        self.product_combo = QComboBox()
        self.product_combo.addItems(["NRML (Carryforward)", "MIS (Intraday)"])

        ord_label = QLabel("Type:")
        ord_label.setStyleSheet("color: #7d879e; font-weight: 700; font-size: 11px;")
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["MARKET", "LIMIT"])
        self.order_type_combo.currentIndexChanged.connect(self._on_type_changed)

        type_layout.addWidget(prod_label)
        type_layout.addWidget(self.product_combo)
        type_layout.addSpacing(10)
        type_layout.addWidget(ord_label)
        type_layout.addWidget(self.order_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Limit Price Row
        self.price_layout = QHBoxLayout()
        price_label = QLabel("Limit Price (₹):")
        price_label.setStyleSheet("color: #7d879e; font-weight: 700; font-size: 11px;")
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.05, 1000000.0)
        self.price_spin.setSingleStep(0.05)
        self.price_spin.setValue(self.current_ltp)
        self.price_spin.setDecimals(2)
        self.price_spin.setEnabled(False)
        self.price_spin.valueChanged.connect(self._recalculate_estimate)

        self.price_layout.addWidget(price_label)
        self.price_layout.addWidget(self.price_spin)
        layout.addLayout(self.price_layout)

        # Execution note & Estimated Value
        calc_box = QHBoxLayout()
        self.exec_note = QLabel("Execution at Best Ask")
        self.exec_note.setStyleSheet("color: #ff8a80; font-size: 10px; font-style: italic;")
        self.estimate_label = QLabel("Value: ₹0.00")
        self.estimate_label.setStyleSheet("color: #f5f7fa; font-size: 12px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")

        calc_box.addWidget(self.exec_note)
        calc_box.addStretch()
        calc_box.addWidget(self.estimate_label)
        layout.addLayout(calc_box)

        # Large Clean BUY / SELL Button
        self.submit_btn = QPushButton("BUY")
        self.submit_btn.setObjectName("BuyBtn")
        self.submit_btn.setFixedHeight(36)
        self.submit_btn.clicked.connect(self._on_submit_order)
        layout.addWidget(self.submit_btn)

        self._recalculate_estimate()

    def set_active_symbol(self, symbol: str, exchange: str, lot_size: int, ltp: float):
        self.current_symbol = symbol
        self.current_exchange = exchange
        self.current_lot_size = lot_size
        self.current_ltp = ltp

        self.symbol_label.setText(symbol)
        self.exch_badge.setText(exchange)
        self.ltp_label.setText(f"LTP: ₹{ltp:.2f}")

        if not self.price_spin.isEnabled():
            self.price_spin.setValue(ltp)

        self._recalculate_estimate()

    def update_quote(self, quote):
        if quote.symbol == self.current_symbol:
            self.current_ltp = quote.ltp
            self.current_bid = quote.bid
            self.current_ask = quote.ask

            self.ltp_label.setText(f"LTP: ₹{quote.ltp:.2f}")
            if quote.bid > 0:
                self.bid_lbl.setText(f"Bid: ₹{quote.bid:.2f}")
            if quote.ask > 0:
                self.ask_lbl.setText(f"Ask: ₹{quote.ask:.2f}")

            if not self.price_spin.isEnabled():
                self.price_spin.setValue(quote.ltp)
            self._recalculate_estimate()

    def _on_type_changed(self, idx):
        is_limit = (self.order_type_combo.currentText() == "LIMIT")
        self.price_spin.setEnabled(is_limit)
        if not is_limit:
            self.price_spin.setValue(self.current_ltp)
        self._recalculate_estimate()

    def _update_submit_button_style(self):
        if self.buy_radio.isChecked():
            self.submit_btn.setText("BUY")
            self.submit_btn.setObjectName("BuyBtn")
            self.exec_note.setText("Execution at Best Ask")
            self.exec_note.setStyleSheet("color: #ff8a80; font-size: 10px; font-style: italic;")
        else:
            self.submit_btn.setText("SELL")
            self.submit_btn.setObjectName("SellBtn")
            self.exec_note.setText("Execution at Best Bid")
            self.exec_note.setStyleSheet("color: #4fc3f7; font-size: 10px; font-style: italic;")

        self.submit_btn.style().unpolish(self.submit_btn)
        self.submit_btn.style().polish(self.submit_btn)
        self._recalculate_estimate()

    def _recalculate_estimate(self):
        lots = self.lots_spin.value()
        total_qty = lots * self.current_lot_size
        self.qty_summary.setText(f"Qty: {total_qty} ({lots} x {self.current_lot_size})")

        if self.order_type_combo.currentText() == "LIMIT":
            price = self.price_spin.value()
        else:
            if self.buy_radio.isChecked():
                price = self.current_ask if self.current_ask > 0 else self.current_ltp
            else:
                price = self.current_bid if self.current_bid > 0 else self.current_ltp

        approx_val = total_qty * price
        self.estimate_label.setText(f"Value: ₹{approx_val:,.2f}")

    def _on_submit_order(self):
        action = OrderAction.BUY if self.buy_radio.isChecked() else OrderAction.SELL
        order_type = OrderType.LIMIT if self.order_type_combo.currentText() == "LIMIT" else OrderType.MARKET
        product = ProductType.MIS if "MIS" in self.product_combo.currentText() else ProductType.NRML
        lots = self.lots_spin.value()
        price = self.price_spin.value() if order_type == OrderType.LIMIT else 0.0

        order_data = {
            "symbol": self.current_symbol,
            "exchange": self.current_exchange,
            "action": action,
            "order_type": order_type,
            "lots": lots,
            "lot_size": self.current_lot_size,
            "price": price,
            "product": product,
        }
        self.order_requested.emit(order_data)
