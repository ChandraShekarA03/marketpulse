from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class OrderSide(str, enum.Enum):
    """Buy or sell order side"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, enum.Enum):
    """Order type for paper trading"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, enum.Enum):
    """Order execution status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class StrategyDeploymentStatus(str, enum.Enum):
    """Strategy deployment status"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"


class PaperPortfolio(Base):
    """Paper trading portfolio for simulated trading"""
    __tablename__ = "paper_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    cash_balance = Column(Float, nullable=False, default=100000.0)
    starting_balance = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="paper_portfolios")
    positions = relationship("PaperPosition", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("PaperOrder", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("PaperTrade", back_populates="portfolio", cascade="all, delete-orphan")
    deployments = relationship("StrategyDeployment", back_populates="portfolio", cascade="all, delete-orphan")


class PaperPosition(Base):
    """Active position in a paper portfolio"""
    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    shares = Column(Float, nullable=False, default=0.0)
    average_price = Column(Float, nullable=False, default=0.0)
    market_value = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    last_price = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolio = relationship("PaperPortfolio", back_populates="positions")


class PaperOrder(Base):
    """Simulated order execution record"""
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    order_type = Column(Enum(OrderType), nullable=False, default=OrderType.MARKET)
    limit_price = Column(Float, nullable=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    filled_price = Column(Float, nullable=True)
    filled_quantity = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    filled_at = Column(DateTime(timezone=True), nullable=True)

    portfolio = relationship("PaperPortfolio", back_populates="orders")


class PaperTrade(Base):
    """Closed trade record (entry + exit)"""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    shares = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    portfolio = relationship("PaperPortfolio", back_populates="trades")


class StrategyDeployment(Base):
    """Strategy deployment record linking strategy to paper portfolio"""
    __tablename__ = "strategy_deployments"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    paper_portfolio_id = Column(Integer, ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(StrategyDeploymentStatus), nullable=False, default=StrategyDeploymentStatus.ACTIVE)
    last_signal_at = Column(DateTime(timezone=True), nullable=True)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    strategy = relationship("Strategy")
    portfolio = relationship("PaperPortfolio", back_populates="deployments")
