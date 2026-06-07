import logging
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import stocks
from app.api.routes import indicators
from app.api.routes import prediction
from app.api.routes import auth
from app.api.routes import portfolio
from app.api.routes import sentiment
from app.api.routes import websocket
from app.api.routes import agent
from app.api.routes import rag
from app.api.routes import strategy
from app.api.routes import backtest
from app.api.routes import paper_trading
from app.core.config import settings
from app.core.database import engine, Base
from app.rag.migrations import ensure_pgvector_extension
from app.models import user, portfolio as portfolio_model
import app.models.agent
import app.models.document
import app.models.strategy
import app.models.backtest
import app.models.paper_trading

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests = requests
        self.window_seconds = window_seconds
        self.clients: dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        history = self.clients[client_ip]
        now = time.time()
        while history and now - history[0] > self.window_seconds:
            history.popleft()
        history.append(now)
        if len(history) > self.requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"status": "error", "detail": "Too many requests. Please try again later."},
            )
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure pgvector extension
ensure_pgvector_extension(engine)
# Base.metadata.create_all(bind=engine)  # Replaced by Alembic migrations

app = FastAPI(
    title="MarketPulse AI",
    description="AI-powered stock intelligence platform",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("HTTP error %s %s: %s", request.method, request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "detail": "Internal server error"},
    )

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "MarketPulse AI API is running."}

@app.on_event("startup")
async def validate_environment():
    if settings.SECRET_KEY == "supersecretkey":
        logger.warning("Using default SECRET_KEY. Set a strong SECRET_KEY in production.")
    if not settings.BACKEND_CORS_ORIGINS:
        logger.warning("BACKEND_CORS_ORIGINS is not configured. Defaulting to localhost:3000.")
    
    # Start the paper trading market loop
    from app.paper_trading.market_loop import market_loop
    await market_loop.start()
    logger.info("Paper trading market loop started")

    # Start the websocket simulation loop
    from app.api.routes.websocket import market_simulation_loop
    import asyncio
    asyncio.create_task(market_simulation_loop())
    logger.info("WebSocket market simulation loop started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    from app.paper_trading.market_loop import market_loop
    await market_loop.stop()
    logger.info("Paper trading market loop stopped")

# Include routers under versioned API prefix
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(stocks.router, prefix=settings.API_V1_STR)
app.include_router(indicators.router, prefix=settings.API_V1_STR)
app.include_router(prediction.router, prefix=settings.API_V1_STR)
app.include_router(portfolio.router, prefix=settings.API_V1_STR)
app.include_router(sentiment.router, prefix=settings.API_V1_STR)
app.include_router(agent.router, prefix=settings.API_V1_STR)
app.include_router(rag.router, prefix=settings.API_V1_STR)
app.include_router(strategy.router, prefix=settings.API_V1_STR)
app.include_router(backtest.router, prefix=settings.API_V1_STR)
app.include_router(paper_trading.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router)

# Future routers to include:
# app.include_router(sentiment.router)