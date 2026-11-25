# NeuroLearn — Adaptive Learning Agent for Personalised Study Planning

NeuroLearn is an intelligent, privacy-first adaptive learning system designed for university students. It combines an autonomous 4-Element Learning Agent Architecture, an empirical Ebbinghaus memory retention engine, an explainable study planner, and historical progress analytics to optimize revision scheduling and maximize academic exam performance.

---

## Architecture Overview

```mermaid
graph TD
    subgraph Client ["Client Layer (Vercel Edge CDN)"]
        UI["React 19 SPA (Vite 8, Tailwind v4)"]
        Router["React Router v7 (Lazy Loaded)"]
        Axios["Axios API Client (Bearer JWT Auth)"]
        UI --> Router --> Axios
    end

    subgraph Backend ["Backend API (FastAPI / Render)"]
        Main["FastAPI Application (app/main.py)"]
        CORS["Strict CORS Middleware"]
        AuthMiddleware["JWT Authentication (Argon2id + PyJWT)"]
        
        Main --> CORS --> AuthMiddleware
        
        subgraph Endpoints ["REST API Endpoints (/api)"]
            AuthEP["/auth (Register, Login, Token)"]
            SubjEP["/subjects & /topics"]
            SessEP["/study-sessions (Lifecycle Tracking)"]
            QuizEP["/quizzes (Idempotency Safe)"]
            RecsEP["/recommendations (Explainable AI Hub)"]
            HistEP["/analytics/history (Mastery & Retention Engine)"]
            HealthEP["/health (Sanitized Connectivity Probe)"]
        end
        AuthMiddleware --> Endpoints
    end

    subgraph AIOrchestrator ["Autonomous Learning Core"]
        PA["Performance Agent (Pacing & Scheduling)"]
        CA["Critic Agent (Quiz Diagnosis & Bloom's Gaps)"]
        LA["Learning Agent (Decay Rate Calibration)"]
        PG["Problem Generator (Diagnostic Probes)"]
        ML["Retention Model (Ebbinghaus Forgetting Curve)"]
    end

    subgraph Storage ["Relational Persistence"]
        DB[(PostgreSQL Production / SQLite Local)]
        Migrations["Alembic Migrations Engine"]
    end

    Axios -- "HTTPS (JSON)" --> Main
    Endpoints --> AIOrchestrator
    Endpoints --> DB
    Migrations --> DB
```

---

## Key Features

1. **Autonomous 4-Element Learning Agent Architecture:**
   - **Performance Element:** Constructs prioritized daily study plans based on exam dates, topic mastery gaps, and student daily study capacity.
   - **Critic Element:** Analyzes quiz outcomes, identifies knowledge gaps across Bloom's Taxonomy, and records targeted diagnostics.
   - **Learning Element:** Classifies learning performance trajectories and updates memory stability parameters.
   - **Problem Generator:** Formulates diagnostic probe questions across cognitive complexity tiers.
2. **Cognitive Memory Retention Engine:**
   - Implements Hermann Ebbinghaus's exponential forgetting curve: $R(t) = 100 \cdot e^{-\lambda t}$.
   - Dynamically calibrates decay rate $\lambda$ upon active recall and revision outcomes.
3. **Study Session Lifecycle:**
   - Tracks session states (`pending` &rarr; `in_progress` &rarr; `completed` / `abandoned`).
   - Accurately distinguishes planned duration from actual elapsed study time.
4. **Quiz Submission Idempotency:**
   - Enforces unique tenant-scoped idempotency keys (`uq_user_quiz_idempotency`), preventing duplicate submission scores and race conditions.
5. **Historical Analytics Engine:**
   - Reconstructs chronological topic mastery trajectories using pre-window baselines and Exponential Moving Average (EMA).
   - Separates predicted retention from observed student quiz/revision scores.

---

## Technology Stack

- **Frontend:** React 19, Vite 8, Tailwind CSS v4, React Router v7, Recharts, Axios, Lucide React.
- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Uvicorn.
- **Security:** Argon2id password hashing, PyJWT (HS256) cryptographic tokens.
- **Database:** PostgreSQL (production target via Neon/Supabase/Render) / SQLite (zero-setup local development).

---

## Repository Structure

```text
NeuroLearn/
├── backend/
│   ├── alembic/              # Database schema migration scripts
│   ├── app/
│   │   ├── agents/           # Performance, Critic, Learning, Problem Generator, Orchestrator
│   │   ├── api/              # FastAPI routers and route handlers
│   │   ├── core/             # Configuration (Pydantic Settings) and security utilities
│   │   ├── db/               # Database Base and session lifecycle
│   │   ├── ml/               # Ebbinghaus retention model, feature extractor, decay calibrator
│   │   ├── models/           # SQLAlchemy declarative ORM models
│   │   ├── schemas/          # Pydantic input/output validation models
│   │   └── services/         # Decoupled business logic (Activity, Planner, Analytics)
│   ├── tests/                # Automated pytest suite (192 unit & integration tests)
│   ├── requirements.txt      # Backend Python dependencies
│   └── .env.example          # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable layout and UI components
│   │   ├── context/          # AuthContext and state providers
│   │   ├── pages/            # Dashboard, Planner, Subjects, Analytics, Recommendations
│   │   ├── services/         # Axios API clients, normalizers, mock toggles
│   │   └── App.jsx           # Root application router with lazy code splitting
│   ├── package.json          # Frontend dependencies and build scripts
│   ├── vercel.json           # Vercel SPA routing and asset cache configuration
│   └── .env.production.example # Frontend production environment template
├── Dockerfile                # Production container specification for backend
├── render.yaml               # Render infrastructure-as-code deployment blueprint
└── README.md                 # Project documentation
```

---

## Local Development Setup

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run automated tests
pytest -q

# Start local backend server (SQLite default)
uvicorn app.main:app --port 8000 --reload
```
API docs available at: `http://localhost:8000/api/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend development server available at: `http://localhost:5173`.

---

## Production Deployment Guide

### Recommended Topology
- **Frontend:** Vercel (Edge CDN)
- **Backend:** Render (Python Web Service)
- **Database:** Neon or Supabase (Managed PostgreSQL)

### 1. Database Provisioning & Migrations
1. Provision a PostgreSQL instance (e.g., on Neon or Supabase).
2. Note the connection URI: `postgresql://user:password@host:5432/neurolearn?sslmode=require`.
3. Set `SQLALCHEMY_DATABASE_URI` in the backend environment.
4. Execute migrations:
   ```bash
   alembic upgrade head
   ```

### 2. Backend Deployment (Render)
- Deploy using the root [render.yaml](file:///c:/Users/Aditya%20Kumar/NeuroLearn/render.yaml) blueprint or as a Web Service.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Required Environment Variables:**
  - `ENVIRONMENT=production`
  - `DEBUG=false`
  - `JWT_SECRET=<secure-random-32-byte-string>`
  - `SQLALCHEMY_DATABASE_URI=<postgresql-connection-string>`
  - `BACKEND_CORS_ORIGINS=["https://your-frontend.vercel.app"]`
  - `ACCESS_TOKEN_EXPIRE_MINUTES=120`

### 3. Frontend Deployment (Vercel)
- Root Directory: `frontend`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`
- **Required Environment Variables:**
  - `VITE_API_BASE_URL=https://your-backend.onrender.com/api`
  - `VITE_MOCK_AUTH=false`
  - `VITE_MOCK_USER=false`
  - `VITE_MOCK_DASHBOARD=false`
  - `VITE_MOCK_SUBJECTS=false`
  - `VITE_MOCK_PLANNER=false`
  - `VITE_MOCK_ANALYTICS=false`
  - `VITE_MOCK_RECOMMENDATIONS=false`
  - `VITE_MOCK_DIAGNOSTIC=false`

---

## Known Limitations & Planned Enhancements

1. **Stateless JWT Revocation:**
   - Tokens remain valid until expiration ($exp$). Real-time immediate logout revocation requires an auxiliary Redis/database blacklist in high-security environments.
2. **API Rate Limiting:**
   - Production ingress reverse-proxies (e.g. Cloudflare / Render rate limits) should be used for brute-force protection on `/api/auth/login`.
3. **Live PostgreSQL CI Testing:**
   - Backend test infrastructure natively supports PostgreSQL via `TEST_DATABASE_URL`, pending external database container provisioning in CI.
