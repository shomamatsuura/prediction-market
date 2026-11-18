# Prediction Market Analytics

A full-stack analytics platform for prediction markets. It ingests live market data from Polymarket every hour and stores the history in a time series. Users can browse markets, chart how probabilities move over time, spot the biggest movers and keep personal watchlists.

**Live demo:** [your-app.vercel.app](https://your-app.vercel.app) · **Demo video:** [2-minute walkthrough](https://link-to-video)

![Dashboard screenshot](docs/screenshots/dashboard.png)

---

## Features

- **Automated data ingestion.** A background scheduler pulls active markets from Polymarket's public API every hour. Each run upserts the markets and records a probability snapshot, and it runs unattended in production.
- **Historical probability charts.** Interactive line charts show how each market's probability has changed over time.
- **Biggest movers dashboard.** An aggregate view shows the markets with the largest probability swings.
- **Authentication.** Sign-up and sign-in use Clerk. The backend verifies Clerk JWTs against Clerk's JWKS.
- **Personal watchlists.** Signed-in users can save markets and manage their own watchlists.
- **Public browsing.** Anyone can view the market list and market detail pages without an account. Only watchlists require auth.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| **Backend** | FastAPI, Python, Pydantic, SQLAlchemy, Alembic |
| **Database** | PostgreSQL |
| **Scheduling** | APScheduler |
| **Auth** | Clerk |
| **Infra** | Docker, Docker Compose, GitHub Actions |
| **Deployment** | Vercel (frontend), Railway (backend + PostgreSQL) |

---

## Architecture

```mermaid
flowchart LR
    U[Browser] --> FE[Next.js frontend<br/>Vercel]
    FE -->|REST + Clerk JWT| BE[FastAPI backend<br/>Railway]
    FE <-->|sign-in / sign-up| CL[Clerk]
    BE -->|verify JWT via JWKS| CL
    BE <--> DB[(PostgreSQL<br/>Railway)]

    subgraph Ingestion loop
        S[APScheduler<br/>hourly job] -->|fetch markets| PM[Polymarket API]
        S -->|upsert markets +<br/>insert snapshots| DB
    end
```

**Design notes:**

- **Server Components for reads.** Market pages fetch data on the server in Next.js, so most pages don't need client-side `useEffect` fetching.
- **The backend is a long-running process, not serverless.** APScheduler runs inside the FastAPI process, so the backend is deployed on Railway as a persistent service. That keeps the hourly ingestion job alive.
- **Markets and snapshots are separate tables.** A `Market` row holds the market's current metadata. `MarketSnapshot` rows record the probability at each hourly run (one-to-many). The snapshot table powers the charts and the movers dashboard.
- **Ingestion is fault tolerant.** Each run is logged and wrapped in error handling, so a bad API response doesn't crash the scheduler.

### Data model

```
User ──< Watchlist ──< WatchlistItem >── Market ──< MarketSnapshot
```

---

## API Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `GET` | `/markets` | — | List markets (supports query filters, e.g. `?category=politics`) |
| `GET` | `/markets/{id}` | — | Market detail |
| `GET` | `/markets/{id}/snapshots` | — | Historical probability snapshots for charting |
| `GET` | `/watchlists` | ✅ | List the current user's watchlists |
| `POST` | `/watchlists` | ✅ | Create a watchlist |
| `POST` | `/watchlists/{id}/items` | ✅ | Add a market to a watchlist |
| `DELETE` | `/watchlists/{id}/items/{market_id}` | ✅ | Remove a market from a watchlist |

FastAPI generates interactive docs at `/docs` while the backend is running.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A free [Clerk](https://clerk.com) application (for auth keys)
- Optional, for running without Docker: Node.js 20+ and Python 3.11+

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/prediction-market-analytics.git
cd prediction-market-analytics
```

### 2. Configure environment variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/markets
CLERK_JWKS_URL=https://<your-clerk-domain>/.well-known/jwks.json
INGESTION_INTERVAL_MINUTES=60
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

### 3. Run everything with Docker Compose

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

### 4. Run database migrations and seed data

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
```

The seed adds sample data so the UI isn't empty right away. Real Polymarket data starts arriving with the first scheduled ingestion run.

### Running without Docker (optional)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

You still need PostgreSQL. Run just the database with `docker compose up -d postgres`.

---

## Project Structure

```
prediction-market-analytics/
├── frontend/              # Next.js app (App Router, TypeScript)
│   ├── app/               # Routes: /, /markets, /markets/[id], /watchlist
│   └── components/        # UI components (shadcn/ui, Recharts charts)
├── backend/               # FastAPI app
│   ├── main.py            # App entrypoint + scheduler startup
│   ├── models/            # SQLAlchemy models
│   ├── routers/           # API routes
│   ├── ingestion/         # Polymarket client + ingest job
│   ├── auth/              # Clerk JWT verification dependency
│   └── alembic/           # Database migrations
├── .github/workflows/     # CI: lint + test on every push
├── docker-compose.yml
└── README.md
```

---

## CI/CD

- **GitHub Actions** lints and tests the frontend and backend on every push.
- **Vercel** deploys the frontend automatically from `main`.
- **Railway** hosts the FastAPI backend as a persistent service, next to a managed PostgreSQL instance.

---

## Screenshots

| Markets | Market detail + chart | Watchlist |
|---|---|---|
| ![Markets](docs/screenshots/markets.png) | ![Detail](docs/screenshots/market-detail.png) | ![Watchlist](docs/screenshots/watchlist.png) |

---

## Roadmap

- [ ] **Price alerts.** Users set a probability threshold on a market. After each ingestion run the backend checks the thresholds and sends an email through [Resend](https://resend.com) when one is crossed.
- [ ] More data sources beyond Polymarket
- [ ] More analytics (volatility, volume trends)

---

## Data Source

Market data comes from [Polymarket](https://polymarket.com)'s public API. This project isn't affiliated with Polymarket.
