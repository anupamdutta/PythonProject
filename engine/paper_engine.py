"""
Virtual Paper Trading Simulation Engine with Spread Execution & File Persistence
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
from .models import (
    Order, Position, Quote, OrderAction, OrderType, OrderStatus, ProductType
)


POSITIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "positions.json")


class PaperTradingEngine:
    def __init__(self, initial_capital: float = 500000.0):
        self.initial_capital: float = initial_capital
        self.cash_balance: float = initial_capital
        self.positions: Dict[str, Position] = {}  # key: f"{symbol}_{product}"
        self.orders: List[Order] = []
        self.quotes: Dict[str, Quote] = {}
        self.on_portfolio_update: Optional[Callable[[], None]] = None
        self.on_order_update: Optional[Callable[[Order], None]] = None

        # Load persisted positions from file
        self.load_state_from_file()

    def reset_account(self, initial_capital: Optional[float] = None):
        """Resets the account to fresh state and clears positions file."""
        if initial_capital is not None:
            self.initial_capital = initial_capital
        self.cash_balance = self.initial_capital
        self.positions.clear()
        self.orders.clear()
        self.save_state_to_file()
        if self.on_portfolio_update:
            self.on_portfolio_update()

    def update_quote(self, quote: Quote):
        """Receives a new quote tick, updates MTM using Bid/Ask, and checks pending limit orders."""
        self.quotes[quote.symbol] = quote

        # Update MTM for open positions matching this symbol using Best Bid (for Long) and Best Ask (for Short)
        for pos_key, pos in self.positions.items():
            if pos.symbol == quote.symbol and pos.net_qty != 0:
                pos.update_mtm(quote.ltp, quote.bid, quote.ask)

        # Check pending limit orders
        self._check_pending_orders(quote)

        if self.on_portfolio_update:
            self.on_portfolio_update()

    def _check_pending_orders(self, quote: Quote):
        """Matches pending limit orders against latest tick price."""
        for order in self.orders:
            if order.status != OrderStatus.PENDING:
                continue
            if order.symbol != quote.symbol:
                continue

            fill = False
            fill_price = order.price

            if order.action == OrderAction.BUY:
                check_price = quote.ask if quote.ask > 0 else quote.ltp
                if check_price > 0 and check_price <= order.price:
                    fill = True
                    fill_price = min(order.price, check_price)
            elif order.action == OrderAction.SELL:
                check_price = quote.bid if quote.bid > 0 else quote.ltp
                if check_price > 0 and check_price >= order.price:
                    fill = True
                    fill_price = max(order.price, check_price)

            if fill:
                self._execute_fill(order, fill_price)

    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: OrderAction,
        order_type: OrderType,
        lots: int,
        lot_size: int,
        price: float = 0.0,
        product: ProductType = ProductType.MIS,
    ) -> Order:
        """Creates and executes paper order. Market BUY executes at Best Ask, Market SELL at Best Bid."""
        quantity = lots * lot_size
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        order = Order(
            order_id=order_id,
            symbol=symbol,
            exchange=exchange,
            action=action,
            order_type=order_type,
            lots=lots,
            lot_size=lot_size,
            quantity=quantity,
            price=price,
            product=product,
            status=OrderStatus.PENDING,
        )
        self.orders.insert(0, order)

        quote = self.quotes.get(symbol)

        if order_type == OrderType.MARKET:
            if quote and (quote.ltp > 0 or quote.ask > 0 or quote.bid > 0):
                if action == OrderAction.BUY:
                    fill_price = quote.ask if quote.ask > 0 else quote.ltp
                else:
                    fill_price = quote.bid if quote.bid > 0 else quote.ltp

                self._execute_fill(order, fill_price)
            elif price > 0:
                self._execute_fill(order, price)
            else:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = "No market price / bid-ask available"
        elif order_type == OrderType.LIMIT:
            if quote and quote.ltp > 0:
                if action == OrderAction.BUY:
                    check_p = quote.ask if quote.ask > 0 else quote.ltp
                    if check_p <= price:
                        self._execute_fill(order, check_p)
                elif action == OrderAction.SELL:
                    check_p = quote.bid if quote.bid > 0 else quote.ltp
                    if check_p >= price:
                        self._execute_fill(order, check_p)

        self.save_state_to_file()

        if self.on_order_update:
            self.on_order_update(order)
        if self.on_portfolio_update:
            self.on_portfolio_update()

        return order

    def cancel_order(self, order_id: str) -> bool:
        """Cancels a pending order."""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                self.save_state_to_file()
                if self.on_order_update:
                    self.on_order_update(order)
                return True
        return False

    def _execute_fill(self, order: Order, fill_price: float):
        """Fills order, updates position and cash balance."""
        order.filled_price = fill_price
        order.filled_at = datetime.now()
        order.status = OrderStatus.COMPLETE

        pos_key = f"{order.symbol}_{order.product.value}"
        pos = self.positions.get(pos_key)

        if not pos:
            quote = self.quotes.get(order.symbol)
            pos = Position(
                symbol=order.symbol,
                exchange=order.exchange,
                product=order.product,
                lot_size=order.lot_size,
                current_ltp=fill_price,
                current_bid=quote.bid if quote else fill_price,
                current_ask=quote.ask if quote else fill_price
            )
            self.positions[pos_key] = pos

        qty = order.quantity
        trade_value = fill_price * qty

        if order.action == OrderAction.BUY:
            if pos.net_qty >= 0:
                total_cost = (pos.avg_buy_price * pos.net_qty) + trade_value
                pos.net_qty += qty
                pos.avg_buy_price = total_cost / pos.net_qty if pos.net_qty > 0 else 0.0
            else:
                short_qty = abs(pos.net_qty)
                closed_qty = min(short_qty, qty)
                realized = (pos.avg_sell_price - fill_price) * closed_qty
                pos.realized_pnl += realized
                self.cash_balance += realized

                pos.net_qty += qty
                if pos.net_qty > 0:
                    pos.avg_buy_price = fill_price
                elif pos.net_qty == 0:
                    pos.avg_sell_price = 0.0

            pos.buy_qty += qty
            pos.buy_value += trade_value

        elif order.action == OrderAction.SELL:
            if pos.net_qty <= 0:
                total_cost = (pos.avg_sell_price * abs(pos.net_qty)) + trade_value
                pos.net_qty -= qty
                pos.avg_sell_price = total_cost / abs(pos.net_qty) if pos.net_qty < 0 else 0.0
            else:
                long_qty = pos.net_qty
                closed_qty = min(long_qty, qty)
                realized = (fill_price - pos.avg_buy_price) * closed_qty
                pos.realized_pnl += realized
                self.cash_balance += realized

                pos.net_qty -= qty
                if pos.net_qty < 0:
                    pos.avg_sell_price = fill_price
                elif pos.net_qty == 0:
                    pos.avg_buy_price = 0.0

            pos.sell_qty += qty
            pos.sell_value += trade_value

        quote = self.quotes.get(order.symbol)
        pos.update_mtm(fill_price, quote.bid if quote else 0.0, quote.ask if quote else 0.0)

        # Save to file on fill
        self.save_state_to_file()

        if self.on_order_update:
            self.on_order_update(order)

    def close_position(self, pos_key: str):
        """Market exits an open position at realistic Bid/Ask."""
        pos = self.positions.get(pos_key)
        if not pos or pos.net_qty == 0:
            return

        action = OrderAction.SELL if pos.net_qty > 0 else OrderAction.BUY
        qty = abs(pos.net_qty)
        lots = max(1, qty // pos.lot_size)

        quote = self.quotes.get(pos.symbol)
        if action == OrderAction.SELL:
            exit_price = (quote.bid if (quote and quote.bid > 0) else (pos.current_bid or pos.current_ltp))
        else:
            exit_price = (quote.ask if (quote and quote.ask > 0) else (pos.current_ask or pos.current_ltp))

        self.place_order(
            symbol=pos.symbol,
            exchange=pos.exchange,
            action=action,
            order_type=OrderType.MARKET,
            lots=lots,
            lot_size=pos.lot_size,
            price=exit_price or 100.0,
            product=pos.product
        )

    def close_all_positions(self):
        """Closes all open positions immediately."""
        active_keys = [k for k, p in self.positions.items() if p.net_qty != 0]
        for key in active_keys:
            self.close_position(key)

    # ---------------- File Persistence ----------------

    def save_state_to_file(self):
        """Saves open positions, cash balance, and order history to positions.json."""
        try:
            positions_data = {}
            for k, p in self.positions.items():
                if p.net_qty != 0 or p.realized_pnl != 0:
                    positions_data[k] = {
                        "symbol": p.symbol,
                        "exchange": p.exchange,
                        "product": p.product.value,
                        "net_qty": p.net_qty,
                        "lot_size": p.lot_size,
                        "buy_qty": p.buy_qty,
                        "sell_qty": p.sell_qty,
                        "buy_value": p.buy_value,
                        "sell_value": p.sell_value,
                        "avg_buy_price": p.avg_buy_price,
                        "avg_sell_price": p.avg_sell_price,
                        "current_ltp": p.current_ltp,
                        "current_bid": p.current_bid,
                        "current_ask": p.current_ask,
                        "realized_pnl": p.realized_pnl,
                        "unrealized_pnl": p.unrealized_pnl
                    }

            orders_data = []
            for o in self.orders[:50]:  # Save recent 50 orders
                orders_data.append({
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "exchange": o.exchange,
                    "action": o.action.value,
                    "order_type": o.order_type.value,
                    "lots": o.lots,
                    "lot_size": o.lot_size,
                    "quantity": o.quantity,
                    "price": o.price,
                    "filled_price": o.filled_price,
                    "status": o.status.value,
                    "product": o.product.value,
                    "created_at": o.created_at.isoformat(),
                    "filled_at": o.filled_at.isoformat() if o.filled_at else None
                })

            payload = {
                "initial_capital": self.initial_capital,
                "cash_balance": self.cash_balance,
                "positions": positions_data,
                "orders": orders_data,
                "last_saved": datetime.now().isoformat()
            }

            with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print("Failed to save positions file:", e)

    def load_state_from_file(self):
        """Loads persisted positions from positions.json on startup."""
        if not os.path.exists(POSITIONS_FILE):
            return

        try:
            with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.initial_capital = data.get("initial_capital", self.initial_capital)
            self.cash_balance = data.get("cash_balance", self.initial_capital)

            positions_data = data.get("positions", {})
            for k, pd in positions_data.items():
                pos = Position(
                    symbol=pd["symbol"],
                    exchange=pd.get("exchange", "MCX"),
                    product=ProductType(pd["product"]),
                    net_qty=pd["net_qty"],
                    lot_size=pd.get("lot_size", 1),
                    buy_qty=pd.get("buy_qty", 0),
                    sell_qty=pd.get("sell_qty", 0),
                    buy_value=pd.get("buy_value", 0.0),
                    sell_value=pd.get("sell_value", 0.0),
                    avg_buy_price=pd.get("avg_buy_price", 0.0),
                    avg_sell_price=pd.get("avg_sell_price", 0.0),
                    current_ltp=pd.get("current_ltp", 0.0),
                    current_bid=pd.get("current_bid", 0.0),
                    current_ask=pd.get("current_ask", 0.0),
                    realized_pnl=pd.get("realized_pnl", 0.0),
                    unrealized_pnl=pd.get("unrealized_pnl", 0.0)
                )
                self.positions[k] = pos

            # Load orders
            loaded_orders = []
            for od in data.get("orders", []):
                o = Order(
                    order_id=od["order_id"],
                    symbol=od["symbol"],
                    exchange=od.get("exchange", "MCX"),
                    action=OrderAction(od["action"]),
                    order_type=OrderType(od["order_type"]),
                    lots=od.get("lots", 1),
                    lot_size=od.get("lot_size", 1),
                    quantity=od["quantity"],
                    price=od["price"],
                    filled_price=od.get("filled_price", 0.0),
                    status=OrderStatus(od["status"]),
                    product=ProductType(od.get("product", "NRML")),
                    created_at=datetime.fromisoformat(od["created_at"]) if od.get("created_at") else datetime.now(),
                    filled_at=datetime.fromisoformat(od["filled_at"]) if od.get("filled_at") else None
                )
                loaded_orders.append(o)
            self.orders = loaded_orders
        except Exception as e:
            print("Failed to load positions file:", e)

    # ---------------- Metrics ----------------

    @property
    def total_realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    @property
    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def total_mtm(self) -> float:
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def net_liquidation_value(self) -> float:
        return self.initial_capital + self.total_mtm

    @property
    def margin_used(self) -> float:
        used = 0.0
        for pos in self.positions.values():
            if pos.net_qty > 0:
                used += pos.avg_buy_price * pos.net_qty
            elif pos.net_qty < 0:
                used += (pos.current_ltp * abs(pos.net_qty)) * 1.5
        return used

    @property
    def available_margin(self) -> float:
        return max(0.0, self.net_liquidation_value - self.margin_used)
