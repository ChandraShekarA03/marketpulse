"""Unit tests for paper trading system."""
from datetime import datetime, timedelta
import pytest
from sqlalchemy.orm import Session
from app.models.paper_trading import (
    OrderSide, OrderType, OrderStatus, StrategyDeploymentStatus,
    PaperPortfolio, PaperPosition, PaperOrder, PaperTrade, StrategyDeployment
)
from app.paper_trading.portfolio_engine import PortfolioEngine
from app.paper_trading.order_manager import OrderManager
from app.paper_trading.execution_engine import ExecutionEngine
from app.paper_trading.signal_processor import Signal


class TestPortfolioEngine:
    """Tests for portfolio engine."""

    def test_create_portfolio(self, db: Session):
        """Test portfolio creation."""
        portfolio = PortfolioEngine.create_portfolio(
            db=db,
            user_id=1,
            name="Test Portfolio",
            starting_balance=50000.0,
        )
        assert portfolio.id is not None
        assert portfolio.cash_balance == 50000.0
        assert portfolio.starting_balance == 50000.0
        assert portfolio.name == "Test Portfolio"

    def test_create_portfolio_invalid_balance(self, db: Session):
        """Test portfolio creation with invalid balance."""
        with pytest.raises(ValueError):
            PortfolioEngine.create_portfolio(
                db=db,
                user_id=1,
                name="Test Portfolio",
                starting_balance=-1000.0,
            )

    def test_add_position(self, db: Session, portfolio: PaperPortfolio):
        """Test adding a position."""
        position = PortfolioEngine.add_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=100,
            price=150.0,
        )
        assert position.ticker == "AAPL"
        assert position.shares == 100
        assert position.average_price == 150.0
        assert position.market_value == 15000.0

    def test_add_position_multiple(self, db: Session, portfolio: PaperPortfolio):
        """Test averaging down on multiple buys."""
        # First buy
        PortfolioEngine.add_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=100,
            price=150.0,
        )
        # Second buy (lower price)
        position = PortfolioEngine.add_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=100,
            price=140.0,
        )
        assert position.shares == 200
        assert position.average_price == 145.0  # Average of 150 and 140

    def test_reduce_position(self, db: Session, portfolio: PaperPortfolio):
        """Test reducing a position."""
        PortfolioEngine.add_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=100,
            price=150.0,
        )
        position = PortfolioEngine.reduce_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=50,
        )
        assert position.shares == 50

    def test_reduce_position_insufficient_shares(self, db: Session, portfolio: PaperPortfolio):
        """Test reducing position with insufficient shares."""
        PortfolioEngine.add_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=50,
            price=150.0,
        )
        with pytest.raises(ValueError):
            PortfolioEngine.reduce_position(
                db=db,
                portfolio_id=portfolio.id,
                ticker="AAPL",
                shares=100,
            )


class TestOrderManager:
    """Tests for order manager."""

    def test_create_order(self, db: Session, portfolio: PaperPortfolio):
        """Test order creation."""
        order = OrderManager.create_order(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        assert order.id is not None
        assert order.ticker == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.PENDING

    def test_create_order_invalid_quantity(self, db: Session, portfolio: PaperPortfolio):
        """Test order creation with invalid quantity."""
        with pytest.raises(ValueError):
            OrderManager.create_order(
                db=db,
                portfolio_id=portfolio.id,
                ticker="AAPL",
                side=OrderSide.BUY,
                quantity=-100,
            )

    def test_fill_order(self, db: Session, portfolio: PaperPortfolio):
        """Test filling an order."""
        order = OrderManager.create_order(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
        )
        filled_order = OrderManager.fill_order(
            db=db,
            order=order,
            filled_price=150.0,
        )
        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.filled_price == 150.0
        assert filled_order.filled_quantity == 100

    def test_cancel_order(self, db: Session, portfolio: PaperPortfolio):
        """Test cancelling an order."""
        order = OrderManager.create_order(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
        )
        cancelled_order = OrderManager.cancel_order(db, order)
        assert cancelled_order.status == OrderStatus.CANCELLED

    def test_cancel_order_already_filled(self, db: Session, portfolio: PaperPortfolio):
        """Test cancelling an already filled order."""
        order = OrderManager.create_order(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
        )
        OrderManager.fill_order(db, order, filled_price=150.0)
        with pytest.raises(ValueError):
            OrderManager.cancel_order(db, order)


class TestExecutionEngine:
    """Tests for execution engine."""

    def test_execute_buy_signal(self, db: Session, portfolio: PaperPortfolio):
        """Test executing a buy signal."""
        signal = Signal(
            ticker="AAPL",
            signal_type="BUY",
            strength=1.0,
            price=150.0,
        )
        result = ExecutionEngine.execute_signal(
            db=db,
            portfolio_id=portfolio.id,
            signal=signal,
            position_size_pct=0.1,
        )
        assert result is not None
        assert result["action"] == "BUY"
        assert result["ticker"] == "AAPL"

    def test_execute_sell_signal(self, db: Session, portfolio: PaperPortfolio):
        """Test executing a sell signal."""
        # Create a position first
        PortfolioEngine.add_position(
            db=db,
            portfolio_id=portfolio.id,
            ticker="AAPL",
            shares=100,
            price=150.0,
        )
        signal = Signal(
            ticker="AAPL",
            signal_type="SELL",
            strength=1.0,
            price=160.0,
        )
        result = ExecutionEngine.execute_signal(
            db=db,
            portfolio_id=portfolio.id,
            signal=signal,
        )
        assert result is not None
        assert result["action"] == "SELL"
        assert result["pnl"] > 0  # Should be profitable


class TestSignalProcessor:
    """Tests for signal processor."""

    def test_signal_creation(self):
        """Test signal object creation."""
        signal = Signal(
            ticker="AAPL",
            signal_type="BUY",
            strength=0.8,
            price=150.0,
            rules_matched=["rsi_oversold"],
        )
        assert signal.ticker == "AAPL"
        assert signal.signal_type == "BUY"
        assert signal.strength == 0.8
        signal_dict = signal.to_dict()
        assert signal_dict["ticker"] == "AAPL"


# Fixtures
@pytest.fixture
def db():
    """Get test database session."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def portfolio(db: Session):
    """Create test portfolio."""
    portfolio = PortfolioEngine.create_portfolio(
        db=db,
        user_id=1,
        name="Test Portfolio",
        starting_balance=100000.0,
    )
    yield portfolio
    # Cleanup
    db.delete(portfolio)
    db.commit()
