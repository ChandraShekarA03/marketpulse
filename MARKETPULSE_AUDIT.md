# MarketPulse Repository Audit

## Overview

This audit reviews the current `MarketPulse` repository state as of the present codebase. It covers:
- Backend architecture and API route surface
- Service layer responsibilities and dependencies
- Machine learning modules and model support
- WebSocket implementation
- Frontend integration, routing, and UX consistency
- Key findings, risks, and recommended next steps

This review is static and based on repository contents only; runtime behavior was not executed.

---

## 1. Backend Architecture

### 1.1 Entry Point

- `backend/app/main.py`
  - Creates FastAPI app
  - Sets up CORS with `allow_origins=["*"]`
  - Registers routers:
    - `stocks.router`
    - `indicators.router`
    - `prediction.router`
    - `auth.router`
    - `portfolio.router`
    - `sentiment.router`
    - `websocket.router`
    - `agent.router`
  - Defines health check endpoint `GET /health`
  - Auto-creates DB tables via `Base.metadata.create_all(bind=engine)`

### 1.2 Configuration and Database

- `backend/app/core/config.py`
  - Uses `pydantic-settings.BaseSettings`
  - Supports PostgreSQL connection string or fallback to SQLite
  - Defines Redis URL, API keys, JWT secret, access token lifetime
  - Default `API_V1_STR` is `/api/v1` but this is not used consistently in route prefixes

- `backend/app/core/database.py`
  - Defines SQLAlchemy engine and `SessionLocal`
  - `get_db()` yields DB sessions with rollback on exception

### 1.3 Security

- `backend/app/core/security.py`
  - Password hashing with `passlib[bcrypt]`
  - JWT creation with `PyJWT`
  - OAuth2 password bearer token URL uses `settings.API_V1_STR`

- `backend/app/api/dependencies.py`
  - Validates current user via JWT
  - Checks `is_active`
  - Inconsistencies:
    - Imports `from jose import jwt, JWTError` but uses `pyjwt` from `import jwt as pyjwt`
    - `oauth2_scheme` tokenUrl may point to `/api/v1/auth/login` while routes are mounted at `/api/auth/login`

### 1.4 Models

- `backend/app/models/user.py`
  - `User` model with email, hashed password, active flag, create timestamp
  - Relationship to portfolios

- `backend/app/models/portfolio.py`
  - `Portfolio` model with user relation and holdings
  - `Holding` model with ticker, shares, average buy price, added timestamp

- `backend/app/models/prediction.py` is empty and appears not implemented

### 1.5 Schemas

- `backend/app/schemas/auth.py`
  - `UserCreate`, `UserResponse`, `Token`, `TokenData`

- `backend/app/schemas/stock.py`
  - `StockResponse` shape matches AlphaVantage-derived stock fields

- `backend/app/schemas/indicator.py`
  - `IndicatorValues`, `IndicatorResponse`

- `backend/app/schemas/prediction.py`
  - `PredictionResponse`, `EvaluationMetrics`

- `backend/app/schemas/sentiment.py`
  - `SentimentResponse`, `NewsArticle`

- `backend/app/schemas/portfolio.py`
  - `PortfolioCreate`, `PortfolioResponse`, `HoldingCreate`, `HoldingResponse`

- `backend/app/schemas/portfolio_schema.py` is empty and unused

---

## 2. Backend API Routes

### 2.1 Active API Endpoints

| Path | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | none | Health check |
| `/api/auth/register` | POST | none | Register new user |
| `/api/auth/login` | POST | none | JWT login; returns access token |
| `/api/auth/me` | GET | yes | Current authenticated user |
| `/api/stocks/{ticker}` | GET | none | Real-time stock quote |
| `/api/indicators/{ticker}` | GET | none | Technical indicator summary |
| `/api/predict/{ticker}` | GET | none | ML prediction with `model` query param |
| `/api/portfolio` | POST | yes | Create portfolio |
| `/api/portfolio` | GET | yes | List user portfolios |
| `/api/portfolio/{portfolio_id}` | DELETE | yes | Delete portfolio |
| `/api/portfolio/{portfolio_id}/holdings` | POST | yes | Add holding |
| `/api/portfolio/holdings/{holding_id}` | DELETE | yes | Remove holding |
| `/api/sentiment/{ticker}` | GET | none | News sentiment analysis |
| `/ws/stocks/{ticker}` | WebSocket | none | Simulated real-time stock stream |
| `/api/agent/analyze` | POST | none | Agentic analysis request |

### 2.2 Dead/Unused Route Files

The repository contains route modules that are not imported by `main.py`:
- `backend/app/api/routes/indicator_routes.py`
  - Calls undefined `get_indicators`
- `backend/app/api/routes/prediction_routes.py`
  - Calls undefined `predict_stock`

These appear stale and should be removed or reconciled with the active route definitions.

---

## 3. Service Layer Review

### 3.1 Stock Service

- `backend/app/services/stock_service.py`
  - Fetches real-time quote from AlphaVantage `GLOBAL_QUOTE`
  - Fetches historical daily data from AlphaVantage `TIME_SERIES_DAILY`
  - Uses retry logic via `requests.adapters.HTTPAdapter`
  - Caches real-time quotes for 5 minutes and historical data for 1 hour via Redis decorator
  - Issues:
    - `verify=False` disables SSL verification on AlphaVantage requests
    - `response` caching uses Redis only when available; fine, but absence is silently tolerated
    - Rate-limit and API-error handling is present, but downstream flows may treat service unavailability as invalid ticker

### 3.2 Indicator Service

- `backend/app/services/indicator_service.py`
  - Generates RSI, MACD, SMA20, EMA50, Bollinger Bands, ATR, Stochastic Oscillator
  - Returns last available row and derived `trend` + `signal`
  - Requires at least 50 historical points
  - Uses `ta` library and Pandas for feature computation

### 3.3 Prediction Service

- `backend/app/services/prediction_service.py`
  - Trains and predicts using:
    - Linear Regression
    - Random Forest
    - XGBoost
    - LSTM (TensorFlow-based if available)
  - Does feature engineering with lag, RSI, MACD, SMA20, EMA50, volume, ATR volatility
  - Uses sequential split for time-series forecasting
  - Caches prediction responses for 1 hour
  - Notes:
    - LSTM path is conditional on TensorFlow availability; if TensorFlow is absent, only traditional models work
    - `backend/requirements.txt` does not declare `openai`, `transformers`, or `tensorflow`
    - Error handling catches all exceptions and returns 500 with raw exception text in the detail field

### 3.4 Sentiment Service

- `backend/app/services/sentiment_service.py`
  - Fetches news from Finnhub if API key is configured
  - Falls back to canned dummy headlines if no Finnhub key exists
  - Uses `transformers` FinBERT model when available
  - Results degrade to all-neutral dummy analysis when transformers are unavailable
  - Issues:
    - `transformers` is optional; if not installed, sentiment output is not real analysis
    - no explicit dependency on `transformers` is present in backend requirements

### 3.5 Portfolio Service

- `backend/app/services/portfolio_service.py`
  - Creates / lists / deletes portfolios
  - Adds holdings after validating ticker via stock service
  - Removes holdings scoped to user ownership
  - Enriches portfolio with live stock data, current value, profit/loss, allocation percentages, risk score
  - Notes:
    - Holding creation depends on live stock API validation; rate-limiting or API outages may block valid tickers
    - No update endpoints exist for holdings or portfolio details

### 3.6 Cache Service

- `backend/app/services/cache_service.py`
  - Provides Redis-backed caching decorator
  - Uses function name + args as cache key
  - If Redis is unavailable, caching is disabled gracefully
  - Minor issue:
    - Falsy results are skipped from caching because `if result:` is used

---

## 4. WebSocket & Real-Time

- `backend/app/api/routes/websocket.py`
  - Implements `/ws/stocks/{ticker}` WebSocket endpoint
  - Simulates streaming price updates per connected client
  - Broadcasts simulated messages to all subscribers of the same ticker
  - Issues / observations:
    - No real market data feed is connected; this is a simulation
    - Each connected client launches its own loop, which may become inefficient under load
    - Timestamps are generated via event loop time rather than wall-clock timestamp

---

## 5. AI Agent Module

- `backend/app/api/routes/agent.py`
  - Endpoint `POST /api/agent/analyze`
  - Inputs `QueryRequest { query: str }`
  - Returns `AgentResponse` JSON schema

- `backend/app/agents/agent_service.py`
  - Uses OpenAI `AsyncOpenAI` and `run_agent_loop`
  - Requires `OPENAI_API_KEY`
  - Instructs the model to output strict JSON

- `backend/app/agents/executor.py`
  - Executes OpenAI tool-calling loop with tools defined in `app.agents.tools`

- `backend/app/agents/tools.py`
  - Exposes tools for stock price, technical indicators, prediction, sentiment
  - Critical issue: imports `get_portfolio_summary` from `app.services.portfolio_service`, but that function does not exist
  - This import will raise `ImportError` and likely prevent agent router initialization at app startup

---

## 6. Frontend Architecture

### 6.1 Pages Present

- `frontend/src/app/page.tsx` - marketing/home landing page
- `frontend/src/app/dashboard/page.tsx` - interactive dashboard that calls backend APIs for stock data, indicators, predictions, sentiment
- `frontend/src/app/login/page.tsx` - mocked login UI (does not authenticate against backend)
- `frontend/src/app/ai-analyst/page.tsx` - chat interface for agentic analysis
- `frontend/src/app/layout.tsx` - global layout with `Navbar`

### 6.2 Components

- `frontend/src/components/Navbar.tsx`
  - Navigation links: Dashboard, ML Predictions, Portfolio
  - UI branding and menu present

- `frontend/src/components/chat/ChatInterface.tsx`
  - Sends queries to the agent endpoint
  - Hardcodes `http://localhost:8000/api/agent/analyze`
  - Uses browser fetch instead of shared Axios client

- `frontend/src/components/chat/RecommendationCard.tsx`
  - Renders agent recommendation result

### 6.3 API Integration

- `frontend/src/lib/api.ts`
  - Axios instance with base URL from `NEXT_PUBLIC_API_URL` or fallback to `http://localhost:8000/api`
  - JWT Authorization header support from `localStorage`

- `frontend/src/app/dashboard/page.tsx`
  - Uses `api.get` for `/stocks/{ticker}`, `/predict/{ticker}?model=randomforest`, `/indicators/{ticker}`, `/sentiment/{ticker}`
  - Displays stock summary, prediction metrics, sentiment gauge, indicators

### 6.4 Missing / Broken Frontend Routes

- `frontend/src/app/portfolio/` exists but is empty; no `page.tsx` is present
- `frontend/src/app/predictions/` exists but is empty; no `page.tsx` is present
- Navbar contains links to `/portfolio` and `/predictions` that will produce 404 currently
- There is no visible link to the `AI Analyst` page, despite it existing at `/ai-analyst`

### 6.5 Frontend Dependency Observations

- `frontend/package.json` includes packages that are not currently used in visible code:
  - `@tanstack/react-query`
  - `zustand`
  - `recharts`
- `frontend/src/services/` and `frontend/src/types/` are empty folders

---

## 7. Deployment / Environment Review

- `docker-compose.yml`
  - Defines `postgres` and `redis` services
  - Does not include backend or frontend service definitions
  - Suggests local containerized DB/cache only; backend and frontend must be run separately

- Backend expects environment variables from `.env` or host env
  - `POSTGRES_SERVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `REDIS_HOST`, `REDIS_PORT`
  - `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `OPENAI_API_KEY`
  - `SECRET_KEY`

- Frontend uses `NEXT_PUBLIC_API_URL` for remote API URL override

---

## 8. Key Findings and Risks

1. **Agent startup failure risk**
   - `app.agents.tools` imports nonexistent `get_portfolio_summary`, likely preventing the agent route from loading.

2. **Dead code and stale modules**
   - `indicator_routes.py`, `prediction_routes.py`, `backend/app/models/prediction.py`, `backend/app/schemas/portfolio_schema.py` are unused or empty.

3. **API versioning inconsistency**
   - `settings.API_V1_STR` defaults to `/api/v1`, but API endpoints are mounted at `/api/...` without that prefix.
   - This misalignment also affects OAuth2 token URL configuration.

4. **Frontend routing mismatch**
   - Navbar links to `/portfolio` and `/predictions`, but those page routes are not implemented.
   - `ai-analyst` page exists but is not surfaced in navigation.

5. **Dependency mismatch / missing packages**
   - Backend requirements omit `openai`, `transformers`, and potentially `tensorflow` if LSTM support is expected.
   - Backend imports `jose.jwt` but `python-jose` is not declared.

6. **Security and production readiness**
   - CORS allows all origins with credentials.
   - Default `SECRET_KEY` is insecure.
   - `stock_service` disables SSL verification for third-party API calls.

7. **Empty test coverage**
   - `tests/` folder is empty; automated tests are absent.

---

## 9. Recommendations

### Short-term fixes

- Remove or reconcile stale route files and unused schema/model files.
- Fix agent import error by either implementing `get_portfolio_summary` or removing the unused import from `app.agents.tools`.
- Align `API_V1_STR` with mounted route prefixes or change token URL configuration to reflect actual paths.
- Change `frontend/src/components/chat/ChatInterface.tsx` to use the shared Axios client and environment-configured base URL.
- Implement or remove empty frontend pages for `portfolio` and `predictions`; expose `/ai-analyst` in navigation if retained.
- Add `openai`, `transformers`, and `python-jose` to backend requirements if those features are intended to be active.
- Replace `verify=False` in stock API calls with secure TLS validation.
- Add initial API tests for backend endpoints and core services.

### Medium-term improvements

- Restrict CORS origins and enable stricter security policies in production.
- Add proper token-based authentication for frontend sign-in flows.
- Introduce an actual live market data feed or background task for WebSocket streaming.
- Add frontend type-safe API wrappers in `frontend/src/services` and reuse them across pages.
- Add missing portfolio prediction UI flows or remove unused navigation.
- Harden error handling so user-facing API errors are clear and not leaked raw exception messages.

### Strategic enhancements

- Add a backend service entrypoint to `docker-compose.yml` so the full stack can be launched with Docker.
- Add test coverage for ML model output, indicator generation, sentiment fallback, and portfolio enrichment.
- Consider aligning the backend with REST versioning best practices, e.g. `/api/v1/...` across all routers.
- Audit deployment secrets and environment management, especially `OPENAI_API_KEY` and `SECRET_KEY` handling.

---

## 10. Suggested Next Priorities

1. Fix the agent import/startup issue.
2. Remove or refactor stale backend route modules.
3. Repair frontend navigation and route coverage for the pages shown in `Navbar`.
4. Add a basic test suite for API routes and service logic.
5. Harden backend config around CORS, secrets, and TLS.

---

## 11. Notes

- This audit is based on repository structure and file contents only; no runtime validation or tests were executed.
- Any future changes should be accompanied by unit/integration tests for the backend API and critical frontend flows.
