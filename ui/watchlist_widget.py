"""
Professional 6-Symbol Watchlist with Level-2 Depth (Bid/Ask/OHLC/PrevClose),
Autocomplete Search, Flexible Resizable Headers, and Roomy Action Buttons
"""
import os
import csv
from datetime import datetime, timezone, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QCompleter, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QKeyEvent
from engine.models import Quote, get_default_lot_size


INSTRUMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instruments.csv")


from .edit_watchlist_dialog import EditWatchlistDialog


class WatchlistWidget(QWidget):
    symbol_selected = pyqtSignal(str, str, int, float)  # (symbol, exchange, lot_size, ltp)
    quick_order = pyqtSignal(str, str, str)             # (symbol, exchange, action "BUY"/"SELL")
    symbol_removed = pyqtSignal(str)
    symbol_added = pyqtSignal(str, str, int)            # (symbol, exchange, lot_size)
    watchlist_manually_saved = pyqtSignal()
    watchlist_reloaded = pyqtSignal(list)               # list of dicts

    MAX_SYMBOLS = 6

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config or {}
        self.symbols_data = {}  # symbol -> {exchange, lot_size, quote}
        self.instruments_cache = {}  # sym -> {exch, lot}
        self._init_ui()
        self._setup_autocomplete()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header with title, index feeds (Nifty & Sensex), live IST clock, slot counter & Actions
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        title = QLabel("DERIVATIVES WATCHLIST")
        title.setStyleSheet("font-weight: 800; color: #8b96ad; font-size: 11px; letter-spacing: 0.8px;")
        header_layout.addWidget(title)

        header_layout.addSpacing(2)

        # NIFTY 50 Live Feed Pill
        self.nifty_pill = QFrame()
        self.nifty_pill.setObjectName("IndexPill")
        nifty_layout = QHBoxLayout(self.nifty_pill)
        nifty_layout.setContentsMargins(8, 2, 8, 2)
        nifty_layout.setSpacing(6)
        nifty_name = QLabel("NIFTY 50")
        nifty_name.setStyleSheet("font-weight: 800; color: #8b96ad; font-size: 10px; font-family: 'Segoe UI', sans-serif;")
        self.nifty_ltp = QLabel("--")
        self.nifty_ltp.setStyleSheet("font-weight: 700; color: #f5f7fa; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        self.nifty_chg = QLabel("--")
        self.nifty_chg.setStyleSheet("font-weight: 700; color: #7d879e; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        nifty_layout.addWidget(nifty_name)
        nifty_layout.addWidget(self.nifty_ltp)
        nifty_layout.addWidget(self.nifty_chg)
        header_layout.addWidget(self.nifty_pill)

        # SENSEX Live Feed Pill
        self.sensex_pill = QFrame()
        self.sensex_pill.setObjectName("IndexPill")
        sensex_layout = QHBoxLayout(self.sensex_pill)
        sensex_layout.setContentsMargins(8, 2, 8, 2)
        sensex_layout.setSpacing(6)
        sensex_name = QLabel("SENSEX")
        sensex_name.setStyleSheet("font-weight: 800; color: #8b96ad; font-size: 10px; font-family: 'Segoe UI', sans-serif;")
        self.sensex_ltp = QLabel("--")
        self.sensex_ltp.setStyleSheet("font-weight: 700; color: #f5f7fa; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        self.sensex_chg = QLabel("--")
        self.sensex_chg.setStyleSheet("font-weight: 700; color: #7d879e; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        sensex_layout.addWidget(sensex_name)
        sensex_layout.addWidget(self.sensex_ltp)
        sensex_layout.addWidget(self.sensex_chg)
        header_layout.addWidget(self.sensex_pill)

        # Current Date & Time (IST) Pill
        self.clock_pill = QFrame()
        self.clock_pill.setObjectName("IndexPill")
        clock_layout = QHBoxLayout(self.clock_pill)
        clock_layout.setContentsMargins(8, 2, 8, 2)
        clock_layout.setSpacing(6)
        clock_icon = QLabel("🕒")
        clock_icon.setStyleSheet("font-size: 10px;")
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet("font-weight: 700; color: #4fc3f7; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        clock_layout.addWidget(clock_icon)
        clock_layout.addWidget(self.clock_lbl)
        header_layout.addWidget(self.clock_pill)

        # Clock live timer (updates every second in IST)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        header_layout.addStretch()

        # Slot counter & Controls
        self.slot_counter = QLabel("0 / 6 Symbols")
        self.slot_counter.setStyleSheet("color: #388bfd; font-weight: 800; font-size: 11px;")

        self.edit_btn = QPushButton("✏ Edit")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setToolTip("Edit, reorder, or load watchlist profiles")
        self.edit_btn.clicked.connect(self._open_edit_dialog)

        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setObjectName("SecondaryBtn")
        self.save_btn.setToolTip("Save current watchlist to configuration")
        self.save_btn.clicked.connect(self._on_save_clicked)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background: #1c202d; color: #ff5252; font-size: 10px;
                padding: 2px 8px; border-radius: 3px; font-weight: bold; border: 1px solid #2d364d;
            }
            QPushButton:hover { background: #b71c1c; color: #ffffff; }
        """)
        self.clear_all_btn.clicked.connect(self.clear_all_symbols)

        header_layout.addWidget(self.slot_counter)
        header_layout.addSpacing(6)
        header_layout.addWidget(self.edit_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.clear_all_btn)
        layout.addLayout(header_layout)

        # Add Symbol Row with Autocomplete
        add_layout = QHBoxLayout()
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["MCX", "NFO", "BFO"])
        self.exchange_combo.setFixedWidth(75)

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Search contracts (e.g. CRUDEOIL, NIFTY 24200, SENSEX)...")
        self.symbol_input.returnPressed.connect(self._on_add_clicked)

        self.add_btn = QPushButton("+ Add")
        self.add_btn.setObjectName("SecondaryBtn")
        self.add_btn.setFixedWidth(70)
        self.add_btn.clicked.connect(self._on_add_clicked)

        add_layout.addWidget(self.exchange_combo)
        add_layout.addWidget(self.symbol_input)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)

        # Table with flexible resizable headers and word wrap
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Exch", "Lot", "Bid", "Ask", "LTP", "Chg %",
            "Open", "High", "Low", "Prev Close", "Actions"
        ])

        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Make EVERY table header interactive so user can freely adjust column width!
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        for i in range(12):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        # Default balanced widths (leaving ample space for Actions)
        self.table.setColumnWidth(0, 220)  # Symbol (reduced from stretch so it doesn't hoard space)
        self.table.setColumnWidth(1, 65)   # Exch
        self.table.setColumnWidth(2, 60)   # Lot
        self.table.setColumnWidth(3, 90)   # Bid
        self.table.setColumnWidth(4, 90)   # Ask
        self.table.setColumnWidth(5, 90)   # LTP
        self.table.setColumnWidth(6, 85)   # Chg%
        self.table.setColumnWidth(7, 80)   # Open
        self.table.setColumnWidth(8, 80)   # High
        self.table.setColumnWidth(9, 80)   # Low
        self.table.setColumnWidth(10, 85)  # Prev Close
        self.table.setColumnWidth(11, 165) # Actions (Ample space for Buy, Sell, ✕)

        self.table.itemClicked.connect(self._on_table_row_clicked)
        layout.addWidget(self.table)

    def _setup_autocomplete(self):
        """Loads tradingsymbols into QCompleter for instant search."""
        if not os.path.exists(INSTRUMENTS_FILE):
            return

        symbols_list = []
        try:
            with open(INSTRUMENTS_FILE, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exch = row.get("exchange", "").strip().upper()
                    sym = row.get("tradingsymbol", "").strip().upper()
                    lot_str = row.get("lot_size", "1")
                    if sym and exch in ("NFO", "BFO", "MCX"):
                        lot = int(lot_str) if lot_str.isdigit() else 1
                        self.instruments_cache[sym] = {"exchange": exch, "lot": lot}
                        symbols_list.append(sym)

            symbols_list = sorted(list(set(symbols_list)))
            completer = QCompleter(symbols_list, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setMaxVisibleItems(12)
            completer.activated.connect(self._on_completer_activated)
            self.symbol_input.setCompleter(completer)
        except Exception as e:
            print("Autocomplete load notice:", e)

    def _on_completer_activated(self, text: str):
        sym = text.strip().upper()
        if sym in self.instruments_cache:
            exch = self.instruments_cache[sym]["exchange"]
            idx = self.exchange_combo.findText(exch)
            if idx >= 0:
                self.exchange_combo.setCurrentIndex(idx)

    def _on_save_clicked(self):
        self.watchlist_manually_saved.emit()
        QMessageBox.information(self, "Watchlist Saved", "Current watchlist saved successfully to configuration!")

    def _open_edit_dialog(self):
        completer = getattr(self.symbol_input, "completer", lambda: None)()
        dlg = EditWatchlistDialog(
            current_symbols_data=self.symbols_data,
            completer=completer,
            config=self.config,
            parent=self
        )
        dlg.watchlist_saved.connect(self._apply_edited_watchlist)
        dlg.exec()

    def _apply_edited_watchlist(self, new_symbols_list: list):
        self.clear_all_symbols()
        for item in new_symbols_list:
            sym = item["symbol"]
            exch = item.get("exchange", "MCX")
            lot = item.get("lot_size", 1)
            self.add_symbol(sym, exch, lot)
        self.watchlist_reloaded.emit(new_symbols_list)
        self.watchlist_manually_saved.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                sym_item = self.table.item(row, 0)
                if sym_item:
                    self.remove_symbol(sym_item.text())
        else:
            super().keyPressEvent(event)

    def _on_add_clicked(self):
        text = self.symbol_input.text().strip().upper()
        if not text:
            return
        exch = self.exchange_combo.currentText()
        if self.add_symbol(text, exch):
            self.symbol_input.clear()

    def add_symbol(self, symbol: str, exchange: str, lot_size: int = None) -> bool:
        symbol = symbol.strip().upper()
        if symbol in self.symbols_data:
            QMessageBox.information(self, "Watchlist", f"'{symbol}' is already in your watchlist.")
            return False

        if len(self.symbols_data) >= self.MAX_SYMBOLS:
            QMessageBox.warning(
                self,
                "Watchlist Limit Reached (6 Max)",
                f"Your watchlist has reached the 6-symbol limit.\nClick 'Clear All' or the red '✕' button on any row to free up space."
            )
            return False

        if lot_size is None or lot_size <= 0:
            if symbol in self.instruments_cache:
                lot_size = self.instruments_cache[symbol]["lot"]
                exchange = self.instruments_cache[symbol]["exchange"]
            else:
                lot_size = get_default_lot_size(symbol)

        quote = Quote(symbol=symbol, exchange=exchange, lot_size=lot_size)
        self.symbols_data[symbol] = {
            "exchange": exchange,
            "lot_size": lot_size,
            "quote": quote
        }

        self._refresh_table()
        self._update_counter()
        self.symbol_added.emit(symbol, exchange, lot_size)
        self.symbol_selected.emit(symbol, exchange, lot_size, quote.ltp)
        return True

    def remove_symbol(self, symbol: str):
        symbol = symbol.strip().upper()
        if symbol in self.symbols_data:
            del self.symbols_data[symbol]
            self.symbol_removed.emit(symbol)
            self._refresh_table()
            self._update_counter()

    def clear_all_symbols(self):
        if not self.symbols_data:
            return
        symbols_to_remove = list(self.symbols_data.keys())
        for sym in symbols_to_remove:
            self.remove_symbol(sym)

    def _update_clock(self):
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist_tz)
        self.clock_lbl.setText(now_ist.strftime("%d-%b-%Y %H:%M:%S IST"))

    def _update_index_pill(self, index_type: str, quote: Quote):
        if quote.ltp <= 0:
            return
        color = "#00e676" if quote.change >= 0 else "#ff5252"
        sign = "+" if quote.change >= 0 else ""
        chg_text = f"{sign}{quote.change:,.2f} ({sign}{quote.change_pct:.2f}%)"

        if index_type == "nifty":
            self.nifty_ltp.setText(f"{quote.ltp:,.2f}")
            self.nifty_chg.setText(chg_text)
            self.nifty_chg.setStyleSheet(f"font-weight: 700; color: {color}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        elif index_type == "sensex":
            self.sensex_ltp.setText(f"{quote.ltp:,.2f}")
            self.sensex_chg.setText(chg_text)
            self.sensex_chg.setStyleSheet(f"font-weight: 700; color: {color}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")

    def update_quote(self, quote: Quote):
        """Called when a live quote tick arrives."""
        if quote.symbol in ("NIFTY 50", "NSE:NIFTY 50"):
            self._update_index_pill("nifty", quote)
            return
        elif quote.symbol in ("SENSEX", "BSE:SENSEX"):
            self._update_index_pill("sensex", quote)
            return

        if quote.symbol not in self.symbols_data:
            return

        self.symbols_data[quote.symbol]["quote"] = quote

        for row in range(self.table.rowCount()):
            sym_item = self.table.item(row, 0)
            if sym_item and sym_item.text() == quote.symbol:
                # Bid
                bid_item = self.table.item(row, 3)
                if bid_item and quote.bid > 0:
                    bid_item.setText(f"{quote.bid:.2f}")

                # Ask
                ask_item = self.table.item(row, 4)
                if ask_item and quote.ask > 0:
                    ask_item.setText(f"{quote.ask:.2f}")

                # LTP
                ltp_item = self.table.item(row, 5)
                if ltp_item and quote.ltp > 0:
                    ltp_item.setText(f"{quote.ltp:.2f}")

                # Chg %
                chg_item = self.table.item(row, 6)
                if chg_item:
                    sign = "+" if quote.change_pct >= 0 else ""
                    chg_item.setText(f"{sign}{quote.change_pct:.2f}%")
                    color = QColor("#00e676") if quote.change_pct >= 0 else QColor("#ff5252")
                    chg_item.setForeground(color)

                # Open
                op_item = self.table.item(row, 7)
                if op_item and quote.open > 0:
                    op_item.setText(f"{quote.open:.2f}")

                # High
                hi_item = self.table.item(row, 8)
                if hi_item and quote.high > 0:
                    hi_item.setText(f"{quote.high:.2f}")

                # Low
                lo_item = self.table.item(row, 9)
                if lo_item and quote.low > 0:
                    lo_item.setText(f"{quote.low:.2f}")

                # Prev Close
                cl_item = self.table.item(row, 10)
                if cl_item and quote.close > 0:
                    cl_item.setText(f"{quote.close:.2f}")
                break

    def _refresh_table(self):
        self.table.setRowCount(0)
        mono_font = QFont("JetBrains Mono", 10)
        bold_mono = QFont("JetBrains Mono", 10, QFont.Weight.Bold)

        for symbol, data in self.symbols_data.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            quote = data["quote"]
            exch = data["exchange"]
            lot = data["lot_size"]

            # 0: Symbol
            sym_item = QTableWidgetItem(symbol)
            sym_item.setFont(bold_mono)
            self.table.setItem(row, 0, sym_item)

            # 1: Exchange badge
            exch_item = QTableWidgetItem(exch)
            exch_color = QColor("#ffb74d") if exch == "MCX" else (QColor("#ce93d8") if exch == "BFO" else QColor("#4fc3f7"))
            exch_item.setForeground(exch_color)
            exch_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            exch_item.setFont(bold_mono)
            self.table.setItem(row, 1, exch_item)

            # 2: Lot size
            lot_item = QTableWidgetItem(str(lot))
            lot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            lot_item.setFont(mono_font)
            self.table.setItem(row, 2, lot_item)

            # 3: Best Bid (Cyan)
            bid_val = f"{quote.bid:.2f}" if quote.bid > 0 else "-"
            bid_item = QTableWidgetItem(bid_val)
            bid_item.setForeground(QColor("#4fc3f7"))
            bid_item.setFont(bold_mono)
            bid_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, bid_item)

            # 4: Best Ask (Pink / Coral)
            ask_val = f"{quote.ask:.2f}" if quote.ask > 0 else "-"
            ask_item = QTableWidgetItem(ask_val)
            ask_item.setForeground(QColor("#ff8a80"))
            ask_item.setFont(bold_mono)
            ask_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, ask_item)

            # 5: LTP
            ltp_val = f"{quote.ltp:.2f}" if quote.ltp > 0 else "-"
            ltp_item = QTableWidgetItem(ltp_val)
            ltp_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ltp_item.setFont(bold_mono)
            self.table.setItem(row, 5, ltp_item)

            # 6: Chg %
            sign = "+" if quote.change_pct >= 0 else ""
            chg_item = QTableWidgetItem(f"{sign}{quote.change_pct:.2f}%")
            chg_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            chg_color = QColor("#00e676") if quote.change_pct >= 0 else QColor("#ff5252")
            chg_item.setForeground(chg_color)
            chg_item.setFont(bold_mono)
            self.table.setItem(row, 6, chg_item)

            # 7: Open
            op_val = f"{quote.open:.2f}" if quote.open > 0 else "-"
            op_item = QTableWidgetItem(op_val)
            op_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            op_item.setForeground(QColor("#8b96ad"))
            op_item.setFont(mono_font)
            self.table.setItem(row, 7, op_item)

            # 8: High
            hi_val = f"{quote.high:.2f}" if quote.high > 0 else "-"
            hi_item = QTableWidgetItem(hi_val)
            hi_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            hi_item.setForeground(QColor("#80cbc4"))
            hi_item.setFont(mono_font)
            self.table.setItem(row, 8, hi_item)

            # 9: Low
            lo_val = f"{quote.low:.2f}" if quote.low > 0 else "-"
            lo_item = QTableWidgetItem(lo_val)
            lo_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lo_item.setForeground(QColor("#ef9a9a"))
            lo_item.setFont(mono_font)
            self.table.setItem(row, 9, lo_item)

            # 10: Prev Close
            cl_val = f"{quote.close:.2f}" if quote.close > 0 else "-"
            cl_item = QTableWidgetItem(cl_val)
            cl_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cl_item.setForeground(QColor("#8b96ad"))
            cl_item.setFont(mono_font)
            self.table.setItem(row, 10, cl_item)

            # 11: Actions (Spacious Buy, Sell, ✕ buttons)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 3, 4, 3)
            action_layout.setSpacing(6)

            b_btn = QPushButton("Buy")
            b_btn.setObjectName("BuyBtn")
            b_btn.setFixedSize(46, 26)
            b_btn.setToolTip(f"Buy 1 Lot of {symbol}")
            b_btn.clicked.connect(lambda _, s=symbol, e=exch: self.quick_order.emit(s, e, "BUY"))

            s_btn = QPushButton("Sell")
            s_btn.setObjectName("SellBtn")
            s_btn.setFixedSize(46, 26)
            s_btn.setToolTip(f"Sell 1 Lot of {symbol}")
            s_btn.clicked.connect(lambda _, s=symbol, e=exch: self.quick_order.emit(s, e, "SELL"))

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #241b22; color: #ff5252; font-weight: bold;
                    border: 1px solid #ff5252; border-radius: 3px; font-size: 11px;
                }
                QPushButton:hover { background-color: #b71c1c; color: white; }
            """)
            del_btn.setFixedSize(28, 26)
            del_btn.setToolTip(f"Remove {symbol} from watchlist")
            del_btn.clicked.connect(lambda _, s=symbol: self.remove_symbol(s))

            action_layout.addWidget(b_btn)
            action_layout.addWidget(s_btn)
            action_layout.addWidget(del_btn)
            action_layout.addStretch()
            self.table.setCellWidget(row, 11, action_widget)

    def _on_table_row_clicked(self, item):
        row = item.row()
        sym_item = self.table.item(row, 0)
        if not sym_item:
            return
        sym = sym_item.text()
        if sym in self.symbols_data:
            d = self.symbols_data[sym]
            self.symbol_selected.emit(sym, d["exchange"], d["lot_size"], d["quote"].ltp)

    def _update_counter(self):
        count = len(self.symbols_data)
        color = "#ff5252" if count >= self.MAX_SYMBOLS else "#388bfd"
        self.slot_counter.setText(f"{count} / {self.MAX_SYMBOLS} Symbols")
        self.slot_counter.setStyleSheet(f"color: {color}; font-weight: 800; font-size: 11px;")
