# API Reference

All endpoints (except WebSockets) are prefixed with `/api/v1`.
A full interactive Swagger UI is available at `/docs` when the backend is running.

## Authentication
- `POST /auth/login`
  Authenticates a user and returns a JWT access token.
- `GET /auth/me`
  Returns the current authenticated user's profile.

## Stocks & Market Data
- `GET /stocks/{ticker}`
  Retrieves real-time or historical data for a specific ticker.
- `GET /indicators/{ticker}`
  Computes technical indicators (SMA, RSI, MACD) for a ticker.
- `GET /sentiment/{ticker}`
  Fetches recent news and analyzes sentiment using FinBERT.

## AI & RAG
- `POST /agent/chat`
  Sends a query to the AI Financial Analyst agent.
- `POST /rag/query`
  Queries the vector database (SEC filings) using semantic search.
- `POST /rag/ingest`
  Ingests raw documents into the vector database.

## Trading & Portfolio
- `GET /portfolio/`
  Retrieves the user's current holdings and balance.
- `GET /paper-trading/portfolio`
  Retrieves paper trading performance and simulated holdings.
- `POST /strategy/`
  Saves a new algorithmic trading strategy.
- `POST /backtest/run`
  Executes a historical backtest of a strategy using `vectorbt`.

## WebSockets
- `WS /ws/stocks/{ticker}`
  Connects to a real-time WebSocket stream for simulated market updates.
