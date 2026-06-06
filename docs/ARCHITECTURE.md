# MarketPulse Architecture

MarketPulse is designed as a decoupled, multi-tier system with real-time capabilities and AI integration.

## Core Components

### 1. Frontend (Next.js)
- **Framework:** Next.js 13+ App Router
- **Styling:** Tailwind CSS + Lucide Icons
- **State Management:** React hooks + local component state
- **Real-Time:** Native WebSockets connected to FastAPI.

### 2. Backend (FastAPI)
- **Framework:** FastAPI for high-performance async REST APIs.
- **ORM:** SQLAlchemy for robust database modeling.
- **Migrations:** Alembic for automated schema management.
- **WebSockets:** ConnectionManager broadcasting simulated market events.
- **AI Integration:** OpenAI API for LLM reasoning, agents, and semantic embeddings.

### 3. Data Layer
- **PostgreSQL + pgvector:** Stores structured data (users, portfolios, strategies) and unstructured vector embeddings for RAG.
- **Redis:** Provides fast caching and pub/sub message brokering for background tasks.

### 4. Background Services
- **Market Loop:** A background `asyncio` task simulating continuous price ticks.
- **AI Agent Executor:** Handles tool-calling, API usage tracking, rate-limiting, and fallback execution logic.

## Data Flow
1. **Client Request:** Frontend hits REST endpoint (e.g., `/api/v1/backtest/run`).
2. **Controller/Router:** FastAPI validates schema and routes to the service layer.
3. **Service Layer:** Executes domain logic. May call `vectorbt` for computations, `OpenAI` for reasoning, or query PostgreSQL.
4. **Caching:** Services check Redis to reduce external API cost and latency.
5. **Real-time Push:** Background loops push data to connected WebSocket clients via the ConnectionManager.
