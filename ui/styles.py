"""
Professional Institutional Scalper Theme QSS Stylesheet
JetBrains Mono font styling with sleek Dark Terminal aesthetic
"""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #10131b;
}

QWidget {
    background-color: #10131b;
    color: #e2e6f0;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

/* Top Navigation & Toolbar */
QFrame#TopHeaderBar {
    background-color: #171b26;
    border-bottom: 2px solid #232a3b;
    padding: 4px 10px;
}

QFrame#MetricCard {
    background-color: #151822;
    border: 1px solid #242b3d;
    border-radius: 4px;
    padding: 4px 10px;
}

QFrame#IndexPill {
    background-color: #151822;
    border: 1px solid #242b3d;
    border-radius: 4px;
}

QLabel#MetricTitle {
    color: #7d879e;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}

QLabel#MetricValue {
    color: #f5f7fa;
    font-size: 15px;
    font-weight: 700;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

QLabel#PositiveMTM {
    color: #00e676;
    font-size: 17px;
    font-weight: 800;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

QLabel#NegativeMTM {
    color: #ff5252;
    font-size: 17px;
    font-weight: 800;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

/* Scalper Escape Badge */
QLabel#EscBadge {
    background-color: #c62828;
    color: #ffffff;
    font-weight: 800;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 3px;
    font-family: 'Segoe UI', sans-serif;
}

/* Status Pill */
QLabel#StatusPillLive {
    background-color: #0c2b1e;
    color: #00e676;
    border: 1px solid #00e67655;
    font-weight: 700;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 3px;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#StatusPillSim {
    background-color: #2b1f0c;
    color: #ffb74d;
    border: 1px solid #ffb74d55;
    font-weight: 700;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 3px;
    font-family: 'Segoe UI', sans-serif;
}

/* Table Styling */
QTableWidget {
    background-color: #131620;
    alternate-background-color: #171b27;
    border: 1px solid #232a3b;
    border-radius: 4px;
    gridline-color: #1d2230;
    selection-background-color: #2962ff33;
    selection-color: #ffffff;
    font-size: 12px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

QTableWidget::item {
    padding: 2px 6px;
    border: none;
}

QHeaderView::section {
    background-color: #191e2b;
    color: #8b96ad;
    padding: 6px 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 2px solid #2962ff;
    border-right: 1px solid #232a3b;
    font-family: 'Segoe UI', sans-serif;
}

/* Tab widget */
QTabWidget::pane {
    border: 1px solid #232a3b;
    background-color: #131620;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #171b26;
    color: #7d879e;
    padding: 7px 16px;
    margin-right: 2px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    font-weight: 700;
    font-size: 11px;
    font-family: 'Segoe UI', sans-serif;
}

QTabBar::tab:selected {
    background-color: #131620;
    color: #388bfd;
    border-top: 2px solid #388bfd;
    border-bottom: 2px solid #131620;
}

/* Inputs & Autocomplete Dropdown */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #10131b;
    border: 1px solid #2a3247;
    border-radius: 3px;
    padding: 5px 8px;
    color: #f5f7fa;
    selection-background-color: #2962ff;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #388bfd;
}

QComboBox::drop-down {
    border: none;
    padding-right: 4px;
}

/* Buttons */
QPushButton {
    background-color: #1d2230;
    border: 1px solid #2d364d;
    border-radius: 3px;
    color: #e2e6f0;
    padding: 5px 10px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton:hover {
    background-color: #262c3e;
    border-color: #3f4b6b;
}

QPushButton#BuyBtn {
    background-color: #00796b;
    border: 1px solid #009688;
    color: #ffffff;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#BuyBtn:hover {
    background-color: #00897b;
}

QPushButton#SellBtn {
    background-color: #b71c1c;
    border: 1px solid #c62828;
    color: #ffffff;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#SellBtn:hover {
    background-color: #c62828;
}

QPushButton#ExitAllBtn {
    background-color: #c62828;
    border: none;
    color: #ffffff;
    font-weight: 800;
    padding: 5px 12px;
    border-radius: 3px;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#ExitAllBtn:hover {
    background-color: #b71c1c;
}

QPushButton#SecondaryBtn {
    background-color: #171b26;
    border: 1px solid #2a3247;
    color: #8b96ad;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#SecondaryBtn:hover {
    border-color: #388bfd;
    color: #f5f7fa;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #10131b;
    width: 7px;
}

QScrollBar::handle:vertical {
    background: #232a3b;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #388bfd;
}

QScrollBar::horizontal {
    border: none;
    background: #10131b;
    height: 7px;
}

QScrollBar::handle:horizontal {
    background: #232a3b;
    min-width: 20px;
    border-radius: 3px;
}
"""
