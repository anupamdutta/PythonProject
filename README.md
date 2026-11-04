# GammaGrid Derivatives Scalper
### High-Performance NFO • BFO • MCX Options Terminal (Python PyQt6)
*Developed by Anupam Dutta*

GammaGrid is a desktop trading and simulation terminal built with **Python 3** and **PyQt6** for Indian equity and commodity derivatives (NSE NFO, BSE BFO, and MCX). It connects directly to live market feeds using a **read-only Zerodha Kite session (`enctoken`)** with **zero API subscription costs** (no ₹2,000/mo fee needed), or runs in an **Offline Simulation Feed** for testing on weekends and after-market hours.

---

## Key Features

1. **Focused 6-Contract Watchlist:**
   - Enforces a strict 6-symbol limit for disciplined scalping.
   - Live **Level-2 Market Depth**: Displays **Best Bid** (Cyan), **Best Ask** (Pink/Coral), **LTP**, **Change %**, **Open**, **High**, **Low**, and **Previous Close**.
   - Flexible, resizable table headers with word-wrap.
   - Quick **`[Buy]`**, **`[Sell]`**, and **`[✕]`** action buttons.
   - **Watchlist Profiles & Reordering:** Easily edit, move up/down, clear, save, and reload custom profiles (e.g. *MCX Crude & NatGas*, *Nifty & BankNifty ATM*, *Sensex Expiry*).

2. **Realistic Spread Execution & Valuation:**
   - **Market BUY:** Automatically fills at the real-time **Best Ask**.
   - **Market SELL:** Automatically fills at the real-time **Best Bid**.
   - **MTM Valuation:** Long positions are liquidated into the **Best Bid**; Short positions are covered from the **Best Ask**.
   - Supports **MIS (Intraday)** and **NRML (Carryforward)** product types.
   - Supports **Market** and **Limit** orders with automatic pending limit order triggers.

3. **Position & State Persistence:**
   - All open positions, trade history, cash balances, and average prices are saved to `positions.json`.
   - On relaunch, active positions automatically resume tracking with live WebSocket feeds.

4. **Zero-Cost Live Zerodha Data Feed:**
   - Direct streaming over WebSocket (`wss://ws.zerodha.com`) with binary packet unpacking.
   - Automatic local caching of Zerodha's complete instrument directory (`instruments.csv`, 220,000+ contracts).
   - Instant search autocomplete (`QCompleter`) for all NFO, BFO, and MCX contracts.
   - Emergency panic key: **`Esc`** closes all open positions instantly.

5. **Aesthetics & Typography:**
   - High-contrast institutional dark theme with **JetBrains Mono** typography.

---

## Installation & Setup

### Prerequisites
* Python 3.10+
* Git

### 1. Clone the Repository
```bash
git clone https://github.com/anupamdutta/PythonProject.git
cd PythonProject
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
```bash
python main.py
```
*(On Windows, you can also double-click `run.bat`)*

---

## Connecting Live Zerodha Market Data (Free Read-Only)

1. Open **[kite.zerodha.com](https://kite.zerodha.com)** in Chrome or Edge and log in.
2. Press **`F12`** &rarr; Go to **Application** &rarr; **Cookies** &rarr; `https://kite.zerodha.com`.
3. Copy the value of the **`enctoken`** cookie.
4. In GammaGrid Scalper, click **`⚙ Feed / Settings`** &rarr; Select **`Zerodha Live Feed`** &rarr; Paste your token &rarr; Click **`Test Zerodha Connection`** &rarr; **`Save & Apply`**.

---

## License
MIT License. Open-source for research, paper trading, and educational purposes.
