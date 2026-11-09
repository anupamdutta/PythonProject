"""
Market Data Feed Provider: High-speed Zerodha WebSocket + Local Instrument Mapping
"""
import os
import csv
import time
import json
import ssl
import struct
import random
import threading
import urllib.parse
import requests
from typing import Dict, List, Optional
import websocket
from PyQt6.QtCore import QObject, pyqtSignal
from .models import Quote, get_default_lot_size


INSTRUMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instruments.csv")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


class DataFeedManager(QObject):
    quote_received = pyqtSignal(object)        # Emits Quote
    connection_status = pyqtSignal(str, bool)  # (status_message, is_connected)

    def __init__(self, user_id: str = ""):
        super().__init__()
        self.mode: str = "LIVE"
        self.enctoken: str = ""
        self.user_id: str = user_id or self._load_user_id_from_config()
        self.subscribed_symbols: Dict[str, Quote] = {}          # symbol -> Quote
        self.token_to_symbol: Dict[int, str] = {}               # token -> symbol
        self.instrument_lookup: Dict[str, dict] = {}            # symbol / exchange:symbol -> {token, lot, exchange}
        self.all_symbols_list: List[str] = []                   # for autocomplete
        self._running: bool = False
        self._sim_thread: Optional[threading.Thread] = None
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None

        self._load_local_instruments()

    def _load_user_id_from_config(self) -> str:
        """Reads user_id from config.json if available."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return str(cfg.get("user_id", "")).strip()
            except Exception as e:
                print("Could not read user_id from config.json:", e)
        return ""

    def _load_local_instruments(self):
        """Loads instruments from local disk cache and checks if daily refresh is needed."""
        if os.path.exists(INSTRUMENTS_FILE):
            try:
                # If file is older than 24 hours, update in background
                age_seconds = time.time() - os.path.getmtime(INSTRUMENTS_FILE)
                if age_seconds > 86400:
                    threading.Thread(target=self._download_and_cache_instruments, daemon=True).start()

                with open(INSTRUMENTS_FILE, mode="r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    lookup = {}
                    sym_list = []
                    for row in reader:
                        sym = row.get("tradingsymbol", "").strip().upper()
                        exch = row.get("exchange", "").strip().upper()
                        tok_str = row.get("instrument_token", "")
                        lot_str = row.get("lot_size", "1")
                        if sym and tok_str.isdigit() and (exch in ("NFO", "BFO", "MCX") or sym in ("NIFTY 50", "SENSEX") or row.get("segment") == "INDICES"):
                            tok = int(tok_str)
                            lot = int(lot_str) if lot_str.isdigit() else 1
                            item = {"token": tok, "lot": lot, "exchange": exch, "symbol": sym}
                            lookup[f"{exch}:{sym}"] = item
                            lookup[sym] = item
                            if exch in ("NFO", "BFO", "MCX"):
                                sym_list.append(sym)
                    self.instrument_lookup = lookup
                    self.all_symbols_list = sorted(list(set(sym_list)))
            except Exception as e:
                print("Error loading local instruments:", e)
        else:
            threading.Thread(target=self._download_and_cache_instruments, daemon=True).start()

    def _download_and_cache_instruments(self):
        try:
            url = "https://api.kite.trade/instruments"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                with open(INSTRUMENTS_FILE, "wb") as f:
                    f.write(resp.content)
                self._load_local_instruments()
        except Exception as e:
            print("Failed to download instruments cache:", e)

    def start(self):
        """Starts worker threads."""
        if self._running:
            return
        self._running = True
        self._sim_thread = threading.Thread(target=self._run_sim_loop, daemon=True)
        self._sim_thread.start()

        if self.mode == "LIVE" and self.enctoken:
            self._start_websocket()

    def stop(self):
        """Stops feeds."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self.connection_status.emit("Disconnected", False)

    def set_simulation_mode(self):
        """Switches to offline simulated ticks."""
        self.mode = "SIMULATION"
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self.connection_status.emit("Simulation Mode Active", True)

    def set_live_zerodha_session(self, enctoken: str, user_id: str = ""):
        """Connects to Zerodha live WebSocket using enctoken."""
        self.enctoken = enctoken.strip()
        if user_id.strip():
            self.user_id = user_id.strip()
        elif not self.user_id:
            self.user_id = self._load_user_id_from_config()
        self.mode = "LIVE"
        self.connection_status.emit("Connecting to Zerodha WebSocket...", False)
        self._start_websocket()

    def _start_websocket(self):
        if not self.enctoken:
            return
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

        enc_encoded = urllib.parse.quote(self.enctoken)
        ws_url = f"wss://ws.zerodha.com/?api_key=kitefront&user_id={self.user_id}&enctoken={enc_encoded}&uid=12345&user-agent=kite3-web&version=3.0.0"

        self._ws = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close
        )
        self._ws_thread = threading.Thread(
            target=lambda: self._ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=15, ping_timeout=10),
            daemon=True
        )
        self._ws_thread.start()

    def _on_ws_open(self, ws):
        self.connection_status.emit("🟢 ZERODHA LIVE (WS Connected)", True)
        self._resubscribe_all_ws()

    def _is_ws_active(self) -> bool:
        return bool(self._ws and self._ws.sock and self._ws.sock.connected)

    def _resubscribe_all_ws(self):
        if not self._is_ws_active() or self.mode != "LIVE":
            return
        tokens = []
        for sym, q in self.subscribed_symbols.items():
            token = q.instrument_token or self._lookup_token(sym, q.exchange)
            if token:
                q.instrument_token = token
                self.token_to_symbol[token] = sym
                tokens.append(token)

        if tokens:
            try:
                self._ws.send(json.dumps({"a": "subscribe", "v": tokens}))
                self._ws.send(json.dumps({"a": "mode", "v": ["full", tokens]}))
            except Exception as e:
                print("WS subscribe error:", e)

    def _lookup_token(self, symbol: str, exchange: str) -> Optional[int]:
        if symbol == "NIFTY 50":
            return 256265
        if symbol == "SENSEX":
            return 265
        key1 = f"{exchange}:{symbol}"
        if key1 in self.instrument_lookup:
            return self.instrument_lookup[key1]["token"]
        if symbol in self.instrument_lookup:
            return self.instrument_lookup[symbol]["token"]
        return None

    def _on_ws_message(self, ws, msg):
        if isinstance(msg, bytes):
            self._parse_binary_ticks(msg)

    def _parse_binary_ticks(self, bin_data: bytes):
        if len(bin_data) < 2:
            return
        count = struct.unpack(">H", bin_data[:2])[0]
        offset = 2

        for _ in range(count):
            if offset + 2 > len(bin_data):
                break
            pkt_len = struct.unpack(">H", bin_data[offset:offset+2])[0]
            offset += 2
            pkt = bin_data[offset:offset+pkt_len]
            offset += pkt_len

            if len(pkt) >= 8:
                token = struct.unpack(">I", pkt[:4])[0]
                ltp_raw = struct.unpack(">I", pkt[4:8])[0]
                ltp = ltp_raw / 100.0

                sym = self.token_to_symbol.get(token)
                if sym and sym in self.subscribed_symbols:
                    q = self.subscribed_symbols[sym]
                    q.ltp = ltp

                    if pkt_len in (28, 32):
                        # Index quote packet (28 or 32 bytes)
                        hi, lo, op, cl = struct.unpack(">IIII", pkt[8:24])
                        q.high = hi / 100.0
                        q.low = lo / 100.0
                        q.open = op / 100.0
                        q.close = cl / 100.0
                        if q.close > 0:
                            q.change = round(q.ltp - q.close, 2)
                            q.change_pct = round((q.change / q.close) * 100, 2)
                    elif pkt_len >= 44:
                        op, hi, lo, cl = struct.unpack(">IIII", pkt[28:44])
                        q.open = op / 100.0
                        q.high = hi / 100.0
                        q.low = lo / 100.0
                        q.close = cl / 100.0

                        if q.close > 0:
                            q.change = round(q.ltp - q.close, 2)
                            q.change_pct = round((q.change / q.close) * 100, 2)

                    # Extract Level 2 Depth: Best Bid & Best Ask (184 bytes)
                    if pkt_len == 184:
                        # Best Bid: quantity (4), price (4), orders (2) starting at offset 64
                        b_qty = struct.unpack(">I", pkt[64:68])[0]
                        b_price = struct.unpack(">I", pkt[68:72])[0] / 100.0
                        # Best Ask: starting at offset 64 + 5*12 = 124
                        s_qty = struct.unpack(">I", pkt[124:128])[0]
                        s_price = struct.unpack(">I", pkt[128:132])[0] / 100.0

                        q.bid = b_price
                        q.bid_qty = b_qty
                        q.ask = s_price
                        q.ask_qty = s_qty

                    self.quote_received.emit(q)

    def _on_ws_error(self, ws, err):
        if self.mode == "LIVE":
            self.connection_status.emit(f"WS Warning: {str(err)[:25]}", False)

    def _on_ws_close(self, ws, close_status_code, close_msg):
        if self.mode == "LIVE" and self._running:
            self.connection_status.emit("Zerodha WS Reconnecting...", False)
            time.sleep(3)
            self._start_websocket()

    def subscribe(self, symbol: str, exchange: str = "MCX", lot_size: Optional[int] = None) -> Quote:
        symbol = symbol.strip().upper()
        if symbol in self.subscribed_symbols:
            return self.subscribed_symbols[symbol]

        token = self._lookup_token(symbol, exchange)

        if token and (f"{exchange}:{symbol}" in self.instrument_lookup or symbol in self.instrument_lookup):
            lookup_lot = self.instrument_lookup.get(f"{exchange}:{symbol}", {}).get("lot") or self.instrument_lookup.get(symbol, {}).get("lot")
            if lookup_lot and (lot_size is None or lot_size <= 1):
                if "CRUDEOIL" in symbol and not "CRUDEOILM" in symbol:
                    lot_size = 100
                elif "CRUDEOILM" in symbol:
                    lot_size = 10
                elif "NATURALGAS" in symbol and not "NATGASMINI" in symbol:
                    lot_size = 1250
                else:
                    lot_size = lookup_lot

        if lot_size is None or lot_size <= 0:
            lot_size = get_default_lot_size(symbol)

        quote = Quote(
            symbol=symbol,
            exchange=exchange,
            ltp=0.0,
            lot_size=lot_size,
            instrument_token=token
        )

        if token:
            self.token_to_symbol[token] = symbol
            if self._is_ws_active() and self.mode == "LIVE":
                try:
                    self._ws.send(json.dumps({"a": "subscribe", "v": [token]}))
                    self._ws.send(json.dumps({"a": "mode", "v": ["full", [token]]}))
                except Exception as e:
                    print("Error sending subscribe frame:", e)

        self.subscribed_symbols[symbol] = quote
        self.quote_received.emit(quote)
        return quote

    def unsubscribe(self, symbol: str):
        symbol = symbol.strip().upper()
        if symbol in self.subscribed_symbols:
            token = self.subscribed_symbols[symbol].instrument_token
            if token and token in self.token_to_symbol:
                del self.token_to_symbol[token]
                if self._ws and self.mode == "LIVE":
                    try:
                        self._ws.send(json.dumps({"a": "unsubscribe", "v": [token]}))
                    except Exception:
                        pass
            del self.subscribed_symbols[symbol]

    def _run_sim_loop(self):
        """Simulated ticks generator (only runs when mode == SIMULATION)."""
        while self._running:
            if self.mode == "SIMULATION":
                for symbol, q in list(self.subscribed_symbols.items()):
                    if symbol == "NIFTY 50":
                        if q.ltp <= 0:
                            q.ltp = 24148.20
                            q.close = 24102.90
                            q.open = 24115.00
                        delta = random.choice([-2, -1, 0, 1, 2]) * 1.5
                        q.ltp = round(max(1000.0, q.ltp + delta), 2)
                        q.change = round(q.ltp - q.close, 2)
                        q.change_pct = round((q.change / q.close) * 100, 2)
                        self.quote_received.emit(q)
                        continue
                    elif symbol == "SENSEX":
                        if q.ltp <= 0:
                            q.ltp = 79486.32
                            q.close = 79606.72
                            q.open = 79510.00
                        delta = random.choice([-2, -1, 0, 1, 2]) * 4.5
                        q.ltp = round(max(1000.0, q.ltp + delta), 2)
                        q.change = round(q.ltp - q.close, 2)
                        q.change_pct = round((q.change / q.close) * 100, 2)
                        self.quote_received.emit(q)
                        continue

                    if q.ltp <= 0:
                        q.ltp = 100.0
                    tick_step = 0.05 if q.ltp < 200 else 0.15
                    delta = random.choice([-2, -1, -1, 0, 1, 1, 2]) * tick_step
                    new_ltp = max(0.50, round(q.ltp + delta, 2))
                    q.ltp = new_ltp

                    if q.ltp > q.high:
                        q.high = q.ltp
                    if q.ltp < q.low or q.low == 0:
                        q.low = q.ltp
                    if q.open == 0:
                        q.open = q.ltp
                    if q.close == 0:
                        q.close = q.ltp

                    close_p = q.close if q.close > 0 else q.open
                    q.change = round(q.ltp - close_p, 2)
                    q.change_pct = round((q.change / close_p * 100) if close_p else 0.0, 2)
                    q.bid = max(0.05, round(q.ltp - tick_step, 2))
                    q.ask = round(q.ltp + tick_step, 2)
                    q.bid_qty = random.randint(1, 20) * q.lot_size
                    q.ask_qty = random.randint(1, 20) * q.lot_size

                    self.quote_received.emit(q)

            time.sleep(1.0)
