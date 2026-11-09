"""
GammaGrid Derivatives Scalper - Main Application Window
Professional institutional derivatives terminal with flexible resizable headers
"""
import json
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QSplitter, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from engine.models import Quote, Order, OrderAction, OrderType, ProductType
from engine.paper_engine import PaperTradingEngine, POSITIONS_FILE
from engine.data_feed import DataFeedManager

from .watchlist_widget import WatchlistWidget
from .order_panel import OrderPanel
from .positions_table import PositionsWidget, ClosedPositionsWidget
from .orders_table import OrdersWidget
from .login_dialog import SettingsLoginDialog
from .styles import DARK_THEME_QSS


CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GammaGrid Derivatives Scalper - NFO | BFO | MCX (Zerodha Feed)")
        self.resize(1440, 900)

        # Apply dark theme
        self.setStyleSheet(DARK_THEME_QSS)

        # Core simulation engine and data feed
        self.config = self._load_config()
        self.engine = PaperTradingEngine(initial_capital=self.config.get("initial_capital", 500000.0))
        self.feed = DataFeedManager(user_id=self.config.get("user_id", ""))

        self._init_ui()
        self._wire_signals()
        self._load_saved_state()

        # Start data feed
        self.feed.start()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 6, 8, 8)
        root_layout.setSpacing(6)

        # ---------------- TOP METRICS & SCALPER HEADER ----------------
        header_card = QFrame()
        header_card.setObjectName("TopHeaderBar")
        header_card.setFixedHeight(54)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(8, 2, 8, 2)
        h_layout.setSpacing(10)

        # App Branding: GammaGrid Derivatives Scalper
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        app_title = QLabel("GAMMAGRID DERIVATIVES SCALPER")
        app_title.setStyleSheet("font-weight: 900; font-size: 13px; color: #f5f7fa; letter-spacing: 0.6px; font-family: 'Segoe UI', sans-serif;")
        sub_title = QLabel("Developed by Anupam Dutta")
        sub_title.setStyleSheet("font-size: 9px; color: #8b96ad; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        title_box.addWidget(app_title)
        title_box.addWidget(sub_title)
        h_layout.addLayout(title_box)

        # Compact Panic Hotkey Reminder Badge
        esc_badge = QLabel("Press Esc to exit all")
        esc_badge.setObjectName("EscBadge")
        h_layout.addWidget(esc_badge)

        h_layout.addSpacing(4)

        # Metric: Total Capital (Replaced Virtual Capital)
        self.cash_val = self._create_metric_card(h_layout, "TOTAL CAPITAL", f"₹{self.engine.initial_capital:,.2f}")

        # Metric: Margin Used
        self.margin_val = self._create_metric_card(h_layout, "MARGIN USED", "₹0.00")

        # Metric: Realized P&L
        self.realized_val = self._create_metric_card(h_layout, "REALIZED P&L", "₹0.00")

        # Metric: Total MTM (Net P&L)
        mtm_box = QVBoxLayout()
        mtm_box.setSpacing(0)
        mtm_title = QLabel("NET P&L (MTM)")
        mtm_title.setObjectName("MetricTitle")
        self.mtm_val = QLabel("₹0.00")
        self.mtm_val.setObjectName("PositiveMTM")
        mtm_box.addWidget(mtm_title)
        mtm_box.addWidget(self.mtm_val)
        h_layout.addLayout(mtm_box)

        h_layout.addStretch()

        # Mode Indicator Pill
        self.status_badge = QLabel("🟢 ZERODHA LIVE")
        self.status_badge.setObjectName("StatusPillLive")
        h_layout.addWidget(self.status_badge)

        # Quick Mode Toggle Button
        self.mode_toggle_btn = QPushButton("Toggle Mode")
        self.mode_toggle_btn.setObjectName("SecondaryBtn")
        self.mode_toggle_btn.setToolTip("Quick toggle between Live Feed and Offline Simulation Feed")
        self.mode_toggle_btn.clicked.connect(self._toggle_feed_mode)
        h_layout.addWidget(self.mode_toggle_btn)

        # Settings Button
        self.settings_btn = QPushButton("⚙ Feed / Settings")
        self.settings_btn.setObjectName("SecondaryBtn")
        self.settings_btn.clicked.connect(self._open_settings)
        h_layout.addWidget(self.settings_btn)

        # Global Exit All Panic Button
        self.exit_all_btn = QPushButton("EXIT ALL (ESC)")
        self.exit_all_btn.setObjectName("ExitAllBtn")
        self.exit_all_btn.clicked.connect(self.engine.close_all_positions)
        h_layout.addWidget(self.exit_all_btn)

        root_layout.addWidget(header_card)

        # ---------------- MAIN VERTICAL SPLITTER ----------------
        main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. TOP SECTION: FULL WIDTH WATCHLIST
        self.watchlist = WatchlistWidget(config=self.config)
        self.watchlist.setMinimumHeight(280)
        main_vertical_splitter.addWidget(self.watchlist)

        # 2. BOTTOM SECTION: ORDER PANEL ON LEFT + POSITION/ORDER BOOKS ON RIGHT
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Order Entry Panel (Placed below watchlist)
        self.order_panel = OrderPanel()
        self.order_panel.setMinimumWidth(380)
        self.order_panel.setMaximumWidth(460)
        bottom_splitter.addWidget(self.order_panel)

        # TabWidget: Open Positions, Closed Positions & OrderBook
        self.tabs = QTabWidget()
        self.positions_widget = PositionsWidget()
        self.closed_positions_widget = ClosedPositionsWidget()
        self.orders_widget = OrdersWidget()

        self.tabs.addTab(self.positions_widget, "Open Positions (Live MTM)")
        self.tabs.addTab(self.closed_positions_widget, "Closed Positions")
        self.tabs.addTab(self.orders_widget, "OrderBook")
        bottom_splitter.addWidget(self.tabs)

        bottom_splitter.setStretchFactor(0, 3)
        bottom_splitter.setStretchFactor(1, 7)

        bottom_layout.addWidget(bottom_splitter)
        main_vertical_splitter.addWidget(bottom_container)

        # Proportions: Top Watchlist 45%, Bottom Section 55%
        main_vertical_splitter.setStretchFactor(0, 4)
        main_vertical_splitter.setStretchFactor(1, 6)

        root_layout.addWidget(main_vertical_splitter)

    def _create_metric_card(self, parent_layout, title_text, init_value):
        box = QVBoxLayout()
        box.setSpacing(0)
        title = QLabel(title_text)
        title.setObjectName("MetricTitle")
        val = QLabel(init_value)
        val.setObjectName("MetricValue")
        box.addWidget(title)
        box.addWidget(val)
        parent_layout.addLayout(box)
        return val

    def _wire_signals(self):
        # Watchlist -> Order Panel & Feed
        self.watchlist.symbol_selected.connect(self.order_panel.set_active_symbol)
        self.watchlist.quick_order.connect(self._handle_quick_order)
        self.watchlist.symbol_added.connect(self._handle_symbol_added)
        self.watchlist.symbol_removed.connect(self._handle_symbol_removed)
        self.watchlist.watchlist_manually_saved.connect(self._save_watchlist_to_config)
        self.watchlist.watchlist_reloaded.connect(self._handle_watchlist_reloaded)

        # Order Panel -> Engine
        self.order_panel.order_requested.connect(self._handle_order_placement)

        # Positions -> Engine
        self.positions_widget.close_position_requested.connect(self.engine.close_position)
        self.positions_widget.close_all_requested.connect(self.engine.close_all_positions)

        # Orders -> Engine
        self.orders_widget.cancel_order_requested.connect(self.engine.cancel_order)

        # Data Feed -> Watchlist & Engine
        self.feed.quote_received.connect(self._on_quote_received)
        self.feed.connection_status.connect(self._on_feed_status)

        # Engine Callbacks
        self.engine.on_portfolio_update = self._refresh_portfolio_views
        self.engine.on_order_update = self._on_order_updated

    def _on_quote_received(self, quote: Quote):
        self.watchlist.update_quote(quote)
        self.order_panel.update_quote(quote)
        if quote.symbol not in ("NIFTY 50", "SENSEX"):
            self.engine.update_quote(quote)

    def _on_feed_status(self, msg: str, is_active: bool):
        if "Live" in msg or "Connected" in msg:
            self.status_badge.setText("🟢 ZERODHA LIVE")
            self.status_badge.setObjectName("StatusPillLive")
        elif "Simulation" in msg:
            self.status_badge.setText("🟡 SIMULATION")
            self.status_badge.setObjectName("StatusPillSim")
        else:
            self.status_badge.setText(f"🔴 {msg[:20]}")
            self.status_badge.setObjectName("StatusPillSim")

        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def _handle_order_placement(self, odata: dict):
        order = self.engine.place_order(
            symbol=odata["symbol"],
            exchange=odata["exchange"],
            action=odata["action"],
            order_type=odata["order_type"],
            lots=odata["lots"],
            lot_size=odata["lot_size"],
            price=odata["price"],
            product=odata["product"]
        )
        self._refresh_portfolio_views()

    def _handle_quick_order(self, symbol: str, exchange: str, action_str: str):
        quote = self.feed.subscribed_symbols.get(symbol)
        lot_size = quote.lot_size if quote else 1

        action = OrderAction.BUY if action_str == "BUY" else OrderAction.SELL
        self.engine.place_order(
            symbol=symbol,
            exchange=exchange,
            action=action,
            order_type=OrderType.MARKET,
            lots=1,
            lot_size=lot_size,
            price=0.0,
            product=ProductType.NRML
        )
        self._refresh_portfolio_views()

    def _handle_symbol_added(self, symbol: str, exchange: str, lot_size: int):
        self.feed.subscribe(symbol, exchange, lot_size)
        self._save_watchlist_to_config()

    def _handle_symbol_removed(self, symbol: str):
        self.feed.unsubscribe(symbol)
        self._save_watchlist_to_config()

    def _handle_watchlist_reloaded(self, new_symbols: list):
        for item in new_symbols:
            sym = item["symbol"]
            exch = item.get("exchange", "MCX")
            lot = item.get("lot_size", 1)
            self.feed.subscribe(sym, exch, lot)
        self._save_watchlist_to_config()

    def _refresh_portfolio_views(self):
        # Update Top Header Metrics
        self.cash_val.setText(f"₹{self.engine.cash_balance:,.2f}")
        self.margin_val.setText(f"₹{self.engine.margin_used:,.2f}")

        realized = self.engine.total_realized_pnl
        real_sign = "+" if realized >= 0 else ""
        self.realized_val.setText(f"₹{real_sign}{realized:,.2f}")
        self.realized_val.setStyleSheet(f"color: {'#00e676' if realized >= 0 else '#ff5252'}; font-size: 15px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")

        tot_mtm = self.engine.total_mtm
        mtm_sign = "+" if tot_mtm >= 0 else ""
        self.mtm_val.setText(f"₹{mtm_sign}{tot_mtm:,.2f}")
        self.mtm_val.setObjectName("PositiveMTM" if tot_mtm >= 0 else "NegativeMTM")
        self.mtm_val.style().unpolish(self.mtm_val)
        self.mtm_val.style().polish(self.mtm_val)

        # Update Tables
        self.positions_widget.update_positions(self.engine.positions)
        self.closed_positions_widget.update_positions(self.engine.positions)
        self.orders_widget.update_orders(self.engine.orders)

    def _on_order_updated(self, order: Order):
        self._refresh_portfolio_views()

    def _toggle_feed_mode(self):
        if self.feed.mode == "LIVE":
            self.feed.set_simulation_mode()
            self.config["feed_mode"] = "SIMULATION"
        else:
            if not self.feed.enctoken:
                QMessageBox.warning(self, "No enctoken", "Please enter your Zerodha enctoken under 'Feed / Settings' first.")
                return
            self.feed.set_live_zerodha_session(self.feed.enctoken, self.feed.user_id)
            self.config["feed_mode"] = "LIVE"
        self._save_config()

    def _open_settings(self):
        dlg = SettingsLoginDialog(
            current_mode=self.feed.mode,
            current_enctoken=self.feed.enctoken,
            current_capital=self.engine.initial_capital,
            current_user_id=self.feed.user_id,
            parent=self
        )
        dlg.session_configured.connect(self._apply_feed_config)
        dlg.capital_reset.connect(self._apply_capital_reset)
        dlg.instruments_updated.connect(self._reload_instruments_master)
        dlg.exec()

    def _reload_instruments_master(self):
        self.feed._load_local_instruments()
        self.watchlist._setup_autocomplete()
        self.feed._resubscribe_all_ws()

    def _apply_feed_config(self, mode: str, enctoken: str, user_id: str):
        self.config["feed_mode"] = mode
        self.config["enctoken"] = enctoken
        self.config["user_id"] = user_id
        self._save_config()

        if mode == "LIVE" and enctoken:
            self.feed.set_live_zerodha_session(enctoken, user_id)
        else:
            self.feed.set_simulation_mode()

    def _apply_capital_reset(self, capital: float):
        self.config["initial_capital"] = capital
        self._save_config()
        self.engine.reset_account(capital)
        self._refresh_portfolio_views()

    def keyPressEvent(self, event):
        """Emergency Escape key exits all open positions instantly."""
        if event.key() == Qt.Key.Key_Escape:
            self.engine.close_all_positions()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._save_watchlist_to_config()
        self.engine.save_state_to_file()
        self.feed.stop()
        event.accept()

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "initial_capital": 500000.0,
            "feed_mode": "LIVE",
            "enctoken": "",
            "user_id": "",
            "watchlist": []
        }

    def _save_config(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print("Failed to save config:", e)

    def _save_watchlist_to_config(self):
        saved_list = []
        for sym, d in self.watchlist.symbols_data.items():
            saved_list.append({
                "symbol": sym,
                "exchange": d["exchange"],
                "lot_size": d["lot_size"]
            })
        self.config["watchlist"] = saved_list
        self._save_config()

    def _load_saved_state(self):
        token = self.config.get("enctoken", "")
        uid = self.config.get("user_id", "") or self.feed.user_id
        if self.config.get("feed_mode") == "LIVE" and token:
            self.feed.set_live_zerodha_session(token, uid)
        else:
            self.feed.set_simulation_mode()

        wl = self.config.get("watchlist", [])
        for item in wl[:WatchlistWidget.MAX_SYMBOLS]:
            sym = item.get("symbol")
            exch = item.get("exchange", "MCX")
            lot = item.get("lot_size", 1)
            self.watchlist.add_symbol(sym, exch, lot)
            self.feed.subscribe(sym, exch, lot)

        # Also subscribe live quotes for any open positions loaded from positions.json
        for pos_key, pos in self.engine.positions.items():
            if pos.net_qty != 0:
                self.feed.subscribe(pos.symbol, pos.exchange, pos.lot_size)

        # Always subscribe index feeds for header live tickers
        self.feed.subscribe("NIFTY 50", "NSE", 1)
        self.feed.subscribe("SENSEX", "BSE", 1)

        self._refresh_portfolio_views()
