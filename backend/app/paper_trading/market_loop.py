"""Background market loop for continuous paper trading updates."""
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.paper_trading import StrategyDeploymentStatus
from app.paper_trading.execution_engine import ExecutionEngine
from app.paper_trading.portfolio_engine import PortfolioEngine
from app.paper_trading.signal_processor import SignalProcessor
import logging
import asyncio

logger = logging.getLogger(__name__)


class MarketLoop:
    """Continuous market loop for paper trading strategy execution."""

    # Configuration
    UPDATE_INTERVAL_SECONDS = 60  # Update every minute
    PRICE_UPDATE_INTERVAL_SECONDS = 300  # Update prices every 5 minutes
    SIGNAL_EVAL_INTERVAL_SECONDS = 600  # Evaluate signals every 10 minutes
    LOOKBACK_DAYS = 30

    def __init__(self):
        self.running = False
        self.last_price_update = None
        self.last_signal_eval = None
        self.market_loop_task = None

    async def start(self):
        """Start the market loop background task."""
        if self.running:
            logger.warning("Market loop already running")
            return

        self.running = True
        logger.info("Starting paper trading market loop")
        
        # Run the loop in a background task
        self.market_loop_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the market loop."""
        self.running = False
        if self.market_loop_task:
            self.market_loop_task.cancel()
        logger.info("Paper trading market loop stopped")

    async def _run_loop(self):
        """Main loop that runs continuously."""
        while self.running:
            try:
                await self._process_cycle()
                await asyncio.sleep(self.UPDATE_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Error in market loop cycle: {e}")
                await asyncio.sleep(self.UPDATE_INTERVAL_SECONDS)

    async def _process_cycle(self):
        """Process one market update cycle."""
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            # Check if we should update prices
            should_update_prices = (
                self.last_price_update is None
                or (now - self.last_price_update).total_seconds() >= self.PRICE_UPDATE_INTERVAL_SECONDS
            )

            # Check if we should evaluate signals
            should_eval_signals = (
                self.last_signal_eval is None
                or (now - self.last_signal_eval).total_seconds() >= self.SIGNAL_EVAL_INTERVAL_SECONDS
            )

            if should_update_prices:
                await self._update_all_prices(db)
                self.last_price_update = now

            if should_eval_signals:
                await self._evaluate_all_strategies(db)
                self.last_signal_eval = now

        except Exception as e:
            logger.error(f"Error in market loop cycle: {e}")
        finally:
            db.close()

    async def _update_all_prices(self, db: Session):
        """Update prices for all active portfolios."""
        from app.models.paper_trading import PaperPortfolio

        portfolios = db.query(PaperPortfolio).all()
        updated_count = 0

        for portfolio in portfolios:
            try:
                result = PortfolioEngine.update_position_prices(db, portfolio.id)
                updated_count += 1
                logger.debug(f"Updated prices for portfolio {portfolio.id}: {result['positions_updated']} positions")
            except Exception as e:
                logger.warning(f"Error updating prices for portfolio {portfolio.id}: {e}")

        logger.info(f"Price update cycle complete: {updated_count}/{len(portfolios)} portfolios")

    async def _evaluate_all_strategies(self, db: Session):
        """Evaluate all active strategy deployments and execute signals."""
        from app.models.paper_trading import StrategyDeployment

        deployments = db.query(StrategyDeployment).filter(
            StrategyDeployment.status == StrategyDeploymentStatus.ACTIVE
        ).all()

        if not deployments:
            logger.debug("No active strategy deployments to evaluate")
            return

        execution_results = []

        for deployment in deployments:
            try:
                portfolio_id = deployment.paper_portfolio_id
                strategy = deployment.strategy

                # Evaluate strategy (this would need tickers from strategy definition)
                logger.info(f"Evaluating strategy {strategy.id} for portfolio {portfolio_id}")

                # For now, we'll need to extend this when strategies define tickers
                # signals = SignalProcessor.evaluate_multiple_strategies(
                #     db=db,
                #     portfolio_deployments=[deployment],
                #     lookback_days=self.LOOKBACK_DAYS,
                # )

                # if signals:
                #     # Rank signals by strength
                #     signals = SignalProcessor.rank_signals(signals)
                #
                #     # Execute signals
                #     result = ExecutionEngine.execute_signals_batch(
                #         db=db,
                #         portfolio_id=portfolio_id,
                #         signals=signals,
                #         position_size_pct=0.05,
                #     )
                #     execution_results.append(result)
                #
                #     # Update deployment timestamp
                #     deployment.last_signal_at = datetime.utcnow()
                #     db.commit()

            except Exception as e:
                logger.error(f"Error evaluating deployment {deployment.id}: {e}")

        if execution_results:
            logger.info(f"Signal evaluation cycle complete: {len(execution_results)} deployments executed")

    async def process_manual_signal(
        self,
        portfolio_id: int,
        signal: Any,  # Signal object
        position_size_pct: float = 0.05,
    ) -> Dict[str, Any]:
        """Process a manual signal immediately."""
        db = SessionLocal()
        try:
            result = ExecutionEngine.execute_signal(
                db=db,
                portfolio_id=portfolio_id,
                signal=signal,
                position_size_pct=position_size_pct,
            )
            return result
        finally:
            db.close()

    async def process_signal_batch(
        self,
        portfolio_id: int,
        signals: List[Any],
        position_size_pct: float = 0.05,
    ) -> Dict[str, Any]:
        """Process multiple signals immediately."""
        db = SessionLocal()
        try:
            result = ExecutionEngine.execute_signals_batch(
                db=db,
                portfolio_id=portfolio_id,
                signals=signals,
                position_size_pct=position_size_pct,
            )
            return result
        finally:
            db.close()


# Global market loop instance
market_loop = MarketLoop()


async def get_market_loop() -> MarketLoop:
    """Get the global market loop instance."""
    return market_loop
