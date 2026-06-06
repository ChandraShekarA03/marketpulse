# MarketPulse AI - Advanced AI Roadmap (Phase 10)

This document outlines the architectural vision for future iterations of MarketPulse AI, scaling it from a predictive engine to an autonomous, agentic platform.

## 1. Agentic AI Analyst
**Goal:** Replace static dashboards with an interactive AI agent that answers dynamic financial queries.
**Architecture:**
- **Core Engine:** Large Language Model (e.g., GPT-4 or local Llama 3) accessed via a new FastAPI endpoint (`/api/agent`).
- **Tools Capability:** Equip the agent with function-calling capabilities mapping to existing MarketPulse services:
  - `get_stock_data(ticker)`
  - `get_technical_indicators(ticker)`
  - `get_predictions(ticker)`
  - `get_sentiment(ticker)`
- **Workflow:** User asks "Should I buy AAPL?". The agent queries the API tools, analyzes the combined Technical + ML + Sentiment data, and outputs a synthesized, human-readable recommendation.

## 2. RAG Financial Assistant (Retrieval-Augmented Generation)
**Goal:** Provide grounded context by querying SEC filings and internal portfolio data.
**Architecture:**
- **Vector Database:** Integrate Pinecone or pgvector (since we use Postgres).
- **Data Pipeline:** A Celery background task ingests 10-K and 10-Q documents, chunks them, embeds them via OpenAI/HuggingFace, and stores them in the vector DB.
- **RAG Engine:** The Agentic AI queries the vector DB to retrieve relevant paragraphs before answering questions.

## 3. Auto Strategy Generation & Backtesting Engine
**Goal:** Allow users to simulate trading strategies over historical data.
**Architecture:**
- **Backtesting Service:** A new high-performance Python microservice using `Backtrader` or `vectorbt`.
- **Inputs:** Users pass logic (e.g., "Buy if MACD crosses signal and RSI < 30") via the UI.
- **Processing:** Service executes the logic against the cached historical data returning metrics (Sharpe Ratio, Max Drawdown).

## 4. Reinforcement Learning (RL) Trader
**Goal:** An autonomous trading bot that learns optimal entry/exit strategies through simulated environments.
**Architecture:**
- **Environment:** Build an OpenAI Gym environment wrapped around historical price data.
- **State Space:** Lagged prices, volume, RSI, MACD, and portfolio balance.
- **Action Space:** Buy, Sell, Hold, and Position Sizing.
- **Algorithms:** Implement PPO (Proximal Policy Optimization) using Ray/RLlib or Stable Baselines3.
- **Deployment:** The RL bot runs as a separate background daemon, emitting trading signals via the WebSocket channel established in Phase 8.
