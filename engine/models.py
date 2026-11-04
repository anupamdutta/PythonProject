"""
Data models for Derivatives Paper Trading
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class ProductType(str, Enum):
    MIS = "MIS"      # Intraday
    NRML = "NRML"    # Overnight Carryforward


class Exchange(str, Enum):
    NFO = "NFO"
    BFO = "BFO"
    MCX = "MCX"
    NSE = "NSE"


DEFAULT_LOT_SIZES = {
    # NFO
    "NIFTY": 75,
    "BANKNIFTY": 30,
    "FINNIFTY": 65,
    "MIDCPNIFTY": 120,
    # BFO
    "SENSEX": 20,
    "BANKEX": 30,
    # MCX
    "CRUDEOIL": 100,
    "CRUDEOILM": 10,
    "NATURALGAS": 1250,
    "NATGASMINI": 250,
    "GOLD": 100,
    "GOLDM": 10,
    "SILVER": 30,
    "SILVERM": 5,
    "COPPER": 2500,
    "ZINC": 5000,
}


def get_default_lot_size(symbol: str) -> int:
    sym_upper = symbol.upper()
    for prefix, lot in DEFAULT_LOT_SIZES.items():
        if sym_upper.startswith(prefix):
            return lot
    return 1


@dataclass
class Quote:
    symbol: str
    exchange: str
    ltp: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    close: float = 0.0       # Pre Close
    bid: float = 0.0         # Best Bid
    ask: float = 0.0         # Best Ask
    bid_qty: int = 0
    ask_qty: int = 0
    lot_size: int = 1
    instrument_token: Optional[int] = None
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class Order:
    order_id: str
    symbol: str
    exchange: str
    action: OrderAction
    order_type: OrderType
    lots: int
    lot_size: int
    quantity: int
    price: float           # Requested price (0 for Market)
    filled_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    product: ProductType = ProductType.MIS
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    rejection_reason: str = ""


@dataclass
class Position:
    symbol: str
    exchange: str
    product: ProductType
    net_qty: int = 0         # Positive for Long, Negative for Short
    lot_size: int = 1
    buy_qty: int = 0
    sell_qty: int = 0
    buy_value: float = 0.0
    sell_value: float = 0.0
    avg_buy_price: float = 0.0
    avg_sell_price: float = 0.0
    current_ltp: float = 0.0
    current_bid: float = 0.0
    current_ask: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    def update_mtm(self, ltp: float, bid: float = 0.0, ask: float = 0.0):
        if ltp > 0:
            self.current_ltp = ltp
        if bid > 0:
            self.current_bid = bid
        if ask > 0:
            self.current_ask = ask

        # Institutional-grade liquidation MTM based on Best Bid / Best Ask
        if self.net_qty > 0:
            # Long position exits by SELLING into Best Bid
            exit_price = self.current_bid if self.current_bid > 0 else self.current_ltp
            if exit_price > 0:
                self.unrealized_pnl = (exit_price - self.avg_buy_price) * self.net_qty
        elif self.net_qty < 0:
            # Short position exits by BUYING from Best Ask
            exit_price = self.current_ask if self.current_ask > 0 else self.current_ltp
            if exit_price > 0:
                self.unrealized_pnl = (self.avg_sell_price - exit_price) * abs(self.net_qty)
        else:
            self.unrealized_pnl = 0.0
