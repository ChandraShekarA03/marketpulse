# Local Development Setup

## Prerequisites
- Docker & Docker Compose
- Node.js (18+)
- Python (3.11+)

## Full Stack via Docker
The easiest way to run MarketPulse is via the included `docker-compose.yml`.

1. Copy `.env.example` to `.env` and fill in API keys:
   ```bash
   cp .env.example .env
   ```
2. Build and start services:
   ```bash
   docker-compose up --build
   ```
3. Visit `http://localhost:3000`

## Manual Setup

### 1. Database & Cache
Run PostgreSQL and Redis via Docker:
```bash
docker-compose up postgres redis -d
```

### 2. Backend
1. Create a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   alembic upgrade head
   ```
4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 3. Frontend
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Run development server:
   ```bash
   npm run dev
   ```
