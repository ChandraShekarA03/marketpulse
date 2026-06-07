"""Order management for paper trading execution."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.paper_trading import PaperOrder, OrderStatus, OrderSide, OrderType
from app.services.stock_service import get_stock_data


class OrderManager:
    """Manages order creation, validation, and execution."""

    @staticmethod
    def create_order(
        db: Session,
        portfolio_id: int,
        ticker: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
    ) -> PaperOrder:
        """Create a new order."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if order_type == OrderType.LIMIT and limit_price is None:
            raise ValueError("Limit price required for LIMIT orders")
        
        if order_type == OrderType.LIMIT and limit_price <= 0:
            raise ValueError("Limit price must be positive")

        order = PaperOrder(
            portfolio_id=portfolio_id,
            ticker=ticker.upper(),
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def fill_order(
        db: Session,
        order: PaperOrder,
        filled_price: float,
        filled_quantity: Optional[float] = None,
    ) -> PaperOrder:
        """Fill an order at specified price and quantity."""
        if filled_price <= 0:
            raise ValueError("Filled price must be positive")
        
        if filled_quantity is None:
            filled_quantity = order.quantity
        
        if filled_quantity > order.quantity:
            raise ValueError(f"Filled quantity ({filled_quantity}) exceeds order quantity ({order.quantity})")
        
        if filled_quantity <= 0:
            raise ValueError("Filled quantity must be positive")

        order.filled_price = filled_price
        order.filled_quantity = filled_quantity
        order.status = OrderStatus.FILLED if filled_quantity == order.quantity else OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def cancel_order(db: Session, order: PaperOrder) -> PaperOrder:
        """Cancel a pending order."""
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot cancel order in {order.status} status")
        
        order.status = OrderStatus.CANCELLED
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def execute_market_order(
        db: Session,
        portfolio_id: int,
        ticker: str,
        side: OrderSide,
        quantity: float,
    ) -> Dict[str, Any]:
        """Execute a market order immediately."""
        # Get current price
        try:
            stock_data = get_stock_data(ticker)
            current_price = stock_data["price"]
        except Exception:
            # Fallback if price service unavailable
            current_price = None
        
        if current_price is None:
            raise ValueError(f"Unable to get current price for {ticker}")

        # Create order
        order = OrderManager.create_order(
            db=db,
            portfolio_id=portfolio_id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
        )

        # Fill order
        filled_order = OrderManager.fill_order(
            db=db,
            order=order,
            filled_price=current_price,
            filled_quantity=quantity,
        )

        return {
            "order_id": filled_order.id,
            "ticker": filled_order.ticker,
            "side": filled_order.side.value,
            "quantity": filled_order.quantity,
            "filled_price": filled_order.filled_price,
            "status": filled_order.status.value,
            "timestamp": filled_order.filled_at,
        }
