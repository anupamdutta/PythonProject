"""
Zerodha Session & Trading Account Settings Dialog with Instruments Master Updater
"""
import os
import requests
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QWidget, QMessageBox, QDoubleSpinBox, QRadioButton, QButtonGroup,
    QProgressBar
)
from PyQt6.QtCore import pyqtSignal, QThread


INSTRUMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instruments.csv")


class InstrumentsDownloaderThread(QThread):
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            url = "https://api.kite.trade/instruments"
            resp = requests.get(url, timeout=25)
            if resp.status_code == 200:
                with open(INSTRUMENTS_FILE, "wb") as f:
                    f.write(resp.content)
                size_mb = os.path.getsize(INSTRUMENTS_FILE) / (1024 * 1024)
                self.finished_signal.emit(True, f"Successfully updated ({size_mb:.1f} MB)")
            else:
                self.finished_signal.emit(False, f"HTTP Error {resp.status_code}")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class SettingsLoginDialog(QDialog):
    session_configured = pyqtSignal(str, str, str)  # (mode, enctoken, user_id)
    capital_reset = pyqtSignal(float)               # initial_capital
    instruments_updated = pyqtSignal()

    def __init__(self, current_mode="LIVE", current_enctoken="", current_capital=500000.0, current_user_id="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Account & Data Feed Settings")
        self.setFixedSize(560, 500)
        self.current_mode = current_mode
        self.current_enctoken = current_enctoken
        self.current_user_id = current_user_id
        self.current_capital = current_capital
        self._dl_thread = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        tabs = QTabWidget()

        # Tab 1: Live Zerodha Feed Setup
        live_tab = QWidget()
        live_layout = QVBoxLayout(live_tab)
        live_layout.setSpacing(10)

        mode_box = QHBoxLayout()
        self.sim_radio = QRadioButton("Offline Simulation Feed (Weekends)")
        self.live_radio = QRadioButton("Zerodha Live Feed (Session)")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.sim_radio)
        self.mode_group.addButton(self.live_radio)

        if self.current_enctoken.strip() or self.current_mode == "LIVE":
            self.live_radio.setChecked(True)
        else:
            self.sim_radio.setChecked(True)

        mode_box.addWidget(self.sim_radio)
        mode_box.addWidget(self.live_radio)
        live_layout.addLayout(mode_box)

        guide_label = QLabel(
            "<b>How to get your Zerodha enctoken:</b><br>"
            "1. Open <b>kite.zerodha.com</b> in Chrome/Edge and log in normally.<br>"
            "2. Press <b>F12</b> (Developer Tools) &rarr; Go to <b>Application</b> tab.<br>"
            "3. Under <b>Cookies</b> &rarr; <b>kite.zerodha.com</b>, find <b>enctoken</b>.<br>"
            "4. Copy its value and paste it into the box below:"
        )
        guide_label.setStyleSheet("background: #171b26; padding: 10px; border-radius: 4px; font-size: 11px; color: #8b96ad;")
        guide_label.setWordWrap(True)
        live_layout.addWidget(guide_label)

        live_layout.addWidget(QLabel("Paste enctoken:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("e.g. jEf09lGZ...")
        self.token_input.setText(self.current_enctoken)
        self.token_input.textChanged.connect(self._on_token_changed)
        live_layout.addWidget(self.token_input)

        live_layout.addWidget(QLabel("User ID:"))
        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("e.g. Kite User ID")
        self.user_id_input.setText(self.current_user_id)
        live_layout.addWidget(self.user_id_input)

        test_btn = QPushButton("Test Zerodha Connection")
        test_btn.setObjectName("SecondaryBtn")
        test_btn.clicked.connect(self._test_connection)
        live_layout.addWidget(test_btn)

        live_layout.addStretch()
        tabs.addTab(live_tab, "Zerodha Feed")

        # Tab 2: Account Funds / Capital
        cap_tab = QWidget()
        cap_layout = QVBoxLayout(cap_tab)
        cap_layout.setSpacing(12)

        cap_info = QLabel("Configure your total trading funds balance.")
        cap_info.setStyleSheet("color: #7d879e;")
        cap_layout.addWidget(cap_info)

        cap_row = QHBoxLayout()
        cap_row.addWidget(QLabel("Total Capital (₹):"))
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(10000.0, 100000000.0)
        self.capital_spin.setSingleStep(50000.0)
        self.capital_spin.setValue(self.current_capital)
        self.capital_spin.setDecimals(2)
        cap_row.addWidget(self.capital_spin)
        cap_layout.addLayout(cap_row)

        reset_btn = QPushButton("Reset Account & Clear Positions")
        reset_btn.setObjectName("SellBtn")
        reset_btn.clicked.connect(self._reset_capital)
        cap_layout.addWidget(reset_btn)

        cap_layout.addStretch()
        tabs.addTab(cap_tab, "Funds & Balance")

        # Tab 3: Instruments Master (Update instruments.csv)
        inst_tab = QWidget()
        inst_layout = QVBoxLayout(inst_tab)
        inst_layout.setSpacing(12)

        inst_info = QLabel(
            "<b>Zerodha Instruments Master:</b><br>"
            "Zerodha refreshes option contracts and new expiries daily around <b>8:30 AM IST</b>.<br>"
            "Updating this file refreshes all NFO, BFO, and MCX strike prices and autocomplete search."
        )
        inst_info.setStyleSheet("background: #171b26; padding: 10px; border-radius: 4px; font-size: 11px; color: #8b96ad;")
        inst_info.setWordWrap(True)
        inst_layout.addWidget(inst_info)

        # Status of instruments.csv
        self.file_status_lbl = QLabel(self._get_file_status_text())
        self.file_status_lbl.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #4fc3f7;")
        inst_layout.addWidget(self.file_status_lbl)

        self.update_inst_btn = QPushButton("🔄 Download Today's Fresh Instruments")
        self.update_inst_btn.setObjectName("SecondaryBtn")
        self.update_inst_btn.setFixedHeight(34)
        self.update_inst_btn.clicked.connect(self._start_instruments_update)
        inst_layout.addWidget(self.update_inst_btn)

        self.dl_progress = QProgressBar()
        self.dl_progress.setRange(0, 0)  # indeterminate
        self.dl_progress.setVisible(False)
        inst_layout.addWidget(self.dl_progress)

        inst_layout.addStretch()
        tabs.addTab(inst_tab, "Instruments Master")

        layout.addWidget(tabs)

        # Bottom Action Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save & Apply")
        save_btn.setObjectName("BuyBtn")
        save_btn.clicked.connect(self._on_save)

        close_btn = QPushButton("Cancel")
        close_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _get_file_status_text(self) -> str:
        if os.path.exists(INSTRUMENTS_FILE):
            size_mb = os.path.getsize(INSTRUMENTS_FILE) / (1024 * 1024)
            mtime = os.path.getmtime(INSTRUMENTS_FILE)
            dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            return f"Status: Cached on disk ({size_mb:.1f} MB)\nLast Updated: {dt}"
        return "Status: No local file found."

    def _start_instruments_update(self):
        self.update_inst_btn.setEnabled(False)
        self.dl_progress.setVisible(True)
        self.file_status_lbl.setText("Downloading fresh master from Zerodha...")

        self._dl_thread = InstrumentsDownloaderThread()
        self._dl_thread.finished_signal.connect(self._on_instruments_downloaded)
        self._dl_thread.start()

    def _on_instruments_downloaded(self, success: bool, msg: str):
        self.update_inst_btn.setEnabled(True)
        self.dl_progress.setVisible(False)
        self.file_status_lbl.setText(self._get_file_status_text())

        if success:
            self.instruments_updated.emit()
            QMessageBox.information(
                self,
                "Instruments Updated",
                "Fresh derivative contracts downloaded successfully!\nAutocomplete and token mappings have been updated."
            )
        else:
            QMessageBox.critical(self, "Update Failed", f"Failed to download instruments:\n{msg}")

    def _on_token_changed(self, text: str):
        if text.strip():
            self.live_radio.setChecked(True)

    def _test_connection(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Test Failed", "Please enter an enctoken first.")
            return

        headers = {
            "Authorization": f"enctoken {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            resp = requests.get("https://kite.zerodha.com/oms/user/profile", headers=headers, timeout=4.0)
            if resp.status_code == 200 and resp.json().get("status") == "success":
                profile = resp.json().get("data", {})
                name = profile.get("user_name", "")
                uid = profile.get("user_id", "")
                if uid:
                    self.user_id_input.setText(uid)
                self.live_radio.setChecked(True)
                QMessageBox.information(self, "Success", f"Connected to Zerodha successfully!\nUser: {name} ({uid})")
            else:
                QMessageBox.critical(self, "Auth Failed", f"Zerodha returned status {resp.status_code}.\nPlease copy a fresh enctoken from kite.zerodha.com.")
        except Exception as e:
            QMessageBox.critical(self, "Network Error", f"Unable to reach Zerodha servers:\n{str(e)}")

    def _reset_capital(self):
        new_val = self.capital_spin.value()
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            f"Are you sure you want to reset your account balance to ₹{new_val:,.2f}?\nAll open positions and orders will be cleared.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.capital_reset.emit(new_val)
            QMessageBox.information(self, "Account Reset", "Trading account balance and positions have been reset.")

    def _on_save(self):
        token = self.token_input.text().strip()
        user_id = self.user_id_input.text().strip()

        if token and self.live_radio.isChecked():
            mode = "LIVE"
        elif not self.live_radio.isChecked():
            mode = "SIMULATION"
        else:
            mode = "LIVE" if token else "SIMULATION"

        self.session_configured.emit(mode, token, user_id)
        self.accept()
