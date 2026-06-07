import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Real-time"]
)

class ConnectionManager:
    def __init__(self):
        # Maps ticker to a list of connected websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, ticker: str):
        await websocket.accept()
        ticker = ticker.upper()
        if ticker not in self.active_connections:
            self.active_connections[ticker] = []
        self.active_connections[ticker].append(websocket)
        logger.info(f"Client connected to {ticker} stream. Total: {len(self.active_connections[ticker])}")

    def disconnect(self, websocket: WebSocket, ticker: str):
        ticker = ticker.upper()
        if ticker in self.active_connections:
            self.active_connections[ticker].remove(websocket)
            if not self.active_connections[ticker]:
                del self.active_connections[ticker]
            logger.info(f"Client disconnected from {ticker} stream.")

    async def broadcast_to_ticker(self, ticker: str, message: dict):
        ticker = ticker.upper()
        if ticker in self.active_connections:
            # We must use list() to avoid dictionary changed size during iteration issues
            for connection in list(self.active_connections[ticker]):
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send to a websocket on {ticker}: {e}")
                    self.disconnect(connection, ticker)

manager = ConnectionManager()

@router.websocket("/ws/stocks/{ticker}")
async def websocket_stock_endpoint(websocket: WebSocket, ticker: str):
    """
    WebSocket endpoint for real-time stock price streaming.
    """
    await manager.connect(websocket, ticker)
    try:
        while True:
            # Just keep the connection alive and listen
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, ticker)
    except Exception as e:
        logger.error(f"WebSocket error on {ticker}: {e}")
        manager.disconnect(websocket, ticker)

async def market_simulation_loop():
    import random
    base_prices = {}
    while True:
        await asyncio.sleep(2.0)
        # Iterate over all active tickers
        for ticker in list(manager.active_connections.keys()):
            if ticker not in base_prices:
                base_prices[ticker] = 150.0
            
            variation = random.uniform(-0.5, 0.5)
            base_prices[ticker] += variation
            payload = {
                "event": "price_update",
                "ticker": ticker.upper(),
                "price": round(base_prices[ticker], 2),
                "timestamp": asyncio.get_event_loop().time()
            }
            await manager.broadcast_to_ticker(ticker, payload)
