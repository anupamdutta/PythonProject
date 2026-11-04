"""
Edit & Manage Watchlist Dialog
Allows manual editing, reordering, custom profiles, and saving watchlist configurations
"""
import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QWidget, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from engine.models import get_default_lot_size


class EditWatchlistDialog(QDialog):
    watchlist_saved = pyqtSignal(list)  # list of dicts: [{"symbol": ..., "exchange": ..., "lot_size": ...}]

    MAX_SYMBOLS = 6

    def __init__(self, current_symbols_data: dict, completer=None, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit & Manage Watchlist")
        self.setFixedSize(580, 520)
        self.current_symbols = []
        for sym, d in current_symbols_data.items():
            self.current_symbols.append({
                "symbol": sym,
                "exchange": d.get("exchange", "MCX"),
                "lot_size": d.get("lot_size", 1)
            })
        self.completer = completer
        self.config = config or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info
        header_box = QVBoxLayout()
        header_title = QLabel("EDIT WATCHLIST CONTRACTS")
        header_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #f5f7fa; letter-spacing: 0.6px;")
        header_sub = QLabel(f"Reorder, add, remove, or save preset profiles (Maximum {self.MAX_SYMBOLS} contracts).")
        header_sub.setStyleSheet("font-size: 11px; color: #8b96ad;")
        header_box.addWidget(header_title)
        header_box.addWidget(header_sub)
        layout.addLayout(header_box)

        # Profiles Row
        profiles_card = QFrame()
        profiles_card.setObjectName("MetricCard")
        p_layout = QHBoxLayout(profiles_card)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(8)

        p_label = QLabel("Profiles:")
        p_label.setStyleSheet("font-weight: 700; color: #7d879e; font-size: 11px;")
        self.profile_combo = QComboBox()
        self.profile_combo.addItems([
            "-- Select Saved Profile --",
            "MCX Crude & NatGas",
            "Nifty & BankNifty ATM",
            "Sensex & Bankex (BFO)"
        ])
        # Load user saved profiles from config if any
        user_profiles = self.config.get("saved_profiles", {})
        for name in user_profiles.keys():
            if self.profile_combo.findText(name) < 0:
                self.profile_combo.addItem(name)

        load_p_btn = QPushButton("Load")
        load_p_btn.setObjectName("SecondaryBtn")
        load_p_btn.clicked.connect(self._load_selected_profile)

        save_p_btn = QPushButton("Save As Profile")
        save_p_btn.setObjectName("SecondaryBtn")
        save_p_btn.clicked.connect(self._save_as_new_profile)

        p_layout.addWidget(p_label)
        p_layout.addWidget(self.profile_combo)
        p_layout.addWidget(load_p_btn)
        p_layout.addWidget(save_p_btn)
        layout.addWidget(profiles_card)

        # Add Symbol Row
        add_box = QHBoxLayout()
        self.exch_combo = QComboBox()
        self.exch_combo.addItems(["MCX", "NFO", "BFO"])
        self.exch_combo.setFixedWidth(75)

        self.input_sym = QLineEdit()
        self.input_sym.setPlaceholderText("Search & add contract...")
        if self.completer:
            self.input_sym.setCompleter(self.completer)
        self.input_sym.returnPressed.connect(self._add_symbol)

        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("SecondaryBtn")
        add_btn.setFixedWidth(70)
        add_btn.clicked.connect(self._add_symbol)

        add_box.addWidget(self.exch_combo)
        add_box.addWidget(self.input_sym)
        add_box.addWidget(add_btn)
        layout.addLayout(add_box)

        # List & Order Controls
        mid_layout = QHBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #131620; border: 1px solid #232a3b;
                border-radius: 4px; padding: 4px; font-family: 'JetBrains Mono', monospace; font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 10px; border-bottom: 1px solid #1a1e2b; color: #f5f7fa;
            }
            QListWidget::item:selected {
                background-color: #2962ff33; color: #ffffff; border-left: 3px solid #388bfd;
            }
        """)
        self._refresh_list_widget()

        # Reorder & Delete Buttons Column
        reorder_vbox = QVBoxLayout()
        reorder_vbox.setSpacing(8)

        up_btn = QPushButton("▲ Up")
        up_btn.setObjectName("SecondaryBtn")
        up_btn.clicked.connect(self._move_up)

        down_btn = QPushButton("▼ Down")
        down_btn.setObjectName("SecondaryBtn")
        down_btn.clicked.connect(self._move_down)

        del_btn = QPushButton("✕ Remove")
        del_btn.setStyleSheet("background-color: #2b1f24; color: #ff5252; font-weight: bold; border: 1px solid #ff5252;")
        del_btn.clicked.connect(self._remove_selected)

        reorder_vbox.addWidget(up_btn)
        reorder_vbox.addWidget(down_btn)
        reorder_vbox.addWidget(del_btn)
        reorder_vbox.addStretch()

        mid_layout.addWidget(self.list_widget)
        mid_layout.addLayout(reorder_vbox)
        layout.addLayout(mid_layout)

        # Slot Counter
        self.counter_lbl = QLabel(f"Total: {len(self.current_symbols)} / {self.MAX_SYMBOLS} Contracts")
        self.counter_lbl.setStyleSheet("font-weight: 700; color: #388bfd; font-size: 11px;")
        layout.addWidget(self.counter_lbl)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save & Apply")
        save_btn.setObjectName("BuyBtn")
        save_btn.setFixedHeight(34)
        save_btn.clicked.connect(self._on_save_and_apply)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _refresh_list_widget(self):
        self.list_widget.clear()
        for idx, item in enumerate(self.current_symbols):
            sym = item["symbol"]
            exch = item["exchange"]
            lot = item.get("lot_size", 1)
            display_text = f"#{idx+1}  [{exch}]  {sym:<26} (Lot: {lot})"
            list_item = QListWidgetItem(display_text)
            self.list_widget.addItem(list_item)
        if hasattr(self, "counter_lbl"):
            self.counter_lbl.setText(f"Total: {len(self.current_symbols)} / {self.MAX_SYMBOLS} Contracts")

    def _add_symbol(self):
        sym = self.input_sym.text().strip().upper()
        if not sym:
            return

        if len(self.current_symbols) >= self.MAX_SYMBOLS:
            QMessageBox.warning(self, "Limit Reached", f"Maximum {self.MAX_SYMBOLS} contracts allowed.")
            return

        for item in self.current_symbols:
            if item["symbol"] == sym:
                QMessageBox.information(self, "Duplicate", f"'{sym}' is already in the watchlist.")
                return

        exch = self.exch_combo.currentText()
        lot = get_default_lot_size(sym)
        self.current_symbols.append({"symbol": sym, "exchange": exch, "lot_size": lot})
        self.input_sym.clear()
        self._refresh_list_widget()

    def _remove_selected(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.current_symbols):
            del self.current_symbols[row]
            self._refresh_list_widget()

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.current_symbols[row - 1], self.current_symbols[row] = (
                self.current_symbols[row],
                self.current_symbols[row - 1],
            )
            self._refresh_list_widget()
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.current_symbols) - 1:
            self.current_symbols[row + 1], self.current_symbols[row] = (
                self.current_symbols[row],
                self.current_symbols[row + 1],
            )
            self._refresh_list_widget()
            self.list_widget.setCurrentRow(row + 1)

    def _load_selected_profile(self):
        text = self.profile_combo.currentText()
        if text == "MCX Crude & NatGas":
            self.current_symbols = [
                {"symbol": "CRUDEOIL26NOV9150PE", "exchange": "MCX", "lot_size": 100},
                {"symbol": "CRUDEOIL26NOV9100CE", "exchange": "MCX", "lot_size": 100},
                {"symbol": "CRUDEOIL26NOVFUT", "exchange": "MCX", "lot_size": 100},
                {"symbol": "NATURALGAS26NOV240PE", "exchange": "MCX", "lot_size": 1250},
                {"symbol": "NATURALGAS26NOV250CE", "exchange": "MCX", "lot_size": 1250},
            ]
        elif text == "Nifty & BankNifty ATM":
            self.current_symbols = [
                {"symbol": "NIFTY26NOV24200CE", "exchange": "NFO", "lot_size": 65},
                {"symbol": "NIFTY26NOV24200PE", "exchange": "NFO", "lot_size": 65},
                {"symbol": "BANKNIFTY26NOV52000CE", "exchange": "NFO", "lot_size": 30},
                {"symbol": "BANKNIFTY26NOV52000PE", "exchange": "NFO", "lot_size": 30},
            ]
        elif text == "Sensex & Bankex (BFO)":
            self.current_symbols = [
                {"symbol": "SENSEX26NOV79500CE", "exchange": "BFO", "lot_size": 20},
                {"symbol": "SENSEX26NOV79500PE", "exchange": "BFO", "lot_size": 20},
                {"symbol": "BANKEX26NOV58000CE", "exchange": "BFO", "lot_size": 30},
                {"symbol": "BANKEX26NOV58000PE", "exchange": "BFO", "lot_size": 30},
            ]
        elif text in self.config.get("saved_profiles", {}):
            self.current_symbols = list(self.config["saved_profiles"][text])
        self._refresh_list_widget()

    def _save_as_new_profile(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Profile", "Enter a name for this watchlist profile:")
        if ok and name.strip():
            name = name.strip()
            if "saved_profiles" not in self.config:
                self.config["saved_profiles"] = {}
            self.config["saved_profiles"][name] = list(self.current_symbols)
            if self.profile_combo.findText(name) < 0:
                self.profile_combo.addItem(name)
            self.profile_combo.setCurrentText(name)
            QMessageBox.information(self, "Profile Saved", f"Profile '{name}' saved successfully!")

    def _on_save_and_apply(self):
        self.watchlist_saved.emit(self.current_symbols)
        self.accept()
