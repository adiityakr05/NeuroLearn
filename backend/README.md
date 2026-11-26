# NeuroLearn Backend API

Python FastAPI backend for **NeuroLearn** — Adaptive Learning Agent for Personalised Study Planning.

---

## 1. Overview & Architecture

The backend follows a modular, domain-driven architecture structured around:
- **FastAPI:** High-performance async Python web framework.
- **SQLAlchemy 2:** Type-safe declarative ORM with dual SQLite / PostgreSQL support.
- **Alembic:** Database migrations tracking schema versions.
- **Pydantic v2 & Settings:** Clean validation and environment configuration.
- **Learning Agent Modules (`app/agents/`):** Dedicated stubs for Performance Element, Critic, Learning Element, and Problem Generator.
- **ML Modules (`app/ml/`):** Dedicated stubs for retention prediction and mastery calculation.

```text
backend/
├── alembic/                   # Alembic database migrations
│   ├── versions/              # Migration revision scripts
│   └── env.py                 # Migration runtime configuration
├── app/
│   ├── api/
│   │   ├── deps.py            # Common API dependencies (JWT auth & get_current_user)
│   │   └── v1/
│   │       ├── endpoints/     # HTTP route handlers (health, auth, users, subjects, topics, study_sessions, quizzes, revisions, analytics, planner, recommendations)
│   │       └── router.py      # Unified API v1 router
│   ├── core/
│   │   ├── config.py          # Pydantic Settings & environment variables
│   │   └── security.py        # Argon2 password hashing & PyJWT token utilities
│   ├── db/
│   │   ├── base.py            # DeclarativeBase for models
│   │   └── session.py         # SQLAlchemy engine and session dependency
│   ├── models/                # SQLAlchemy database models
│   │   └── entities.py        # User, Subject, Topic, StudySession, QuizAttempt, RevisionHistory, Recommendation
│   ├── schemas/               # Pydantic request/response schemas
│   │   ├── auth.py            # Token, TokenPayload, LoginRequest
│   │   └── entities.py        # Validation schemas for all database entities
│   ├── services/              # Decoupled business logic
│   │   ├── user_service.py    # User creation, authentication, and profile updates
│   │   ├── curriculum_service.py # Subject & Topic CRUD business logic
│   │   ├── activity_service.py # Study sessions, quiz attempts, revisions & progress statistics
│   │   ├── planner_service.py # Daily/weekly planner & recommendation workflows
│   │   └── agent_adapters.py  # Decoupled interface adapters for AI Agent & ML models
│   ├── agents/                # 4-Element Learning Agent implementations
│   ├── ml/                    # Memory retention & mastery ML models
│   └── main.py                # FastAPI entry point & CORS configuration
├── tests/                     # Pytest suite
│   ├── test_health.py
│   ├── test_models.py
│   ├── test_migrations.py
│   ├── test_auth.py           # Comprehensive auth & user management tests
│   ├── test_curriculum.py     # Subjects & Topics CRUD, security & isolation tests
│   ├── test_activities.py     # Study sessions, quizzes, revisions & progress tests
│   └── test_planner.py        # Planner schedules, rescheduling & recommendation tests
├── alembic.ini                # Alembic CLI configuration
├── .env.example               # Environment variables template
├── .gitignore
├── requirements.txt           # Project dependencies
└── README.md
```

---

## 2. Database Models Schema & Relationships

The database models are implemented using **SQLAlchemy 2** type annotations (`Mapped`, `mapped_column`):

1. **`User` (`users` table):**
   - Stores student credentials (`email`, `hashed_password`, `full_name`, `program`, `semester`).
   - One-to-many relationship with `Subject`, `StudySession`, `QuizAttempt`, and `Recommendation`.
2. **`Subject` (`subjects` table):**
   - Stores academic subject details (`name`, `code`, `color`, `target_mastery`, `exam_date`).
   - Foreign key to `User` (`CASCADE` delete). Unique constraint on `(user_id, code)`.
   - One-to-many relationship with `Topic`, `StudySession`, and `Recommendation`.
3. **`Topic` (`topics` table):**
   - Modules within a subject (`name`, `difficulty`, `mastery_score`, `retention_score`, `decay_rate_lambda`, `completed`).
   - Foreign key to `Subject` (`CASCADE` delete). Unique constraint on `(subject_id, name)`.
   - One-to-many relationship with `StudySession`, `QuizAttempt`, `RevisionHistory`, and `Recommendation`.
4. **`StudySession` (`study_sessions` table):**
   - Scheduled study tasks (`date`, `time_slot`, `duration_minutes`, `status`, `priority`, `retention_score`, `ai_reason`).
   - Foreign keys to `User`, `Subject`, and optional `Topic`.
5. **`QuizAttempt` (`quiz_attempts` table):**
   - Diagnostic tests tracking actual recall accuracy (`score`, `accuracy`, `critic_notes`, `critic_evaluated`).
   - Foreign keys to `User` and `Topic`.
6. **`RevisionHistory` (`revision_history` table):**
   - Longitudinal memory review log (`revision_date`, `score`, `interval_days`, `repetition_number`, `note`).
   - Foreign key to `Topic` (`CASCADE` delete).
7. **`Recommendation` (`recommendations` table):**
   - 4-element agent proposals (`agent_element`, `type`, `priority`, `title`, `reason_detail`, `suggested_slot`, `status`).
   - Foreign keys to `User`, optional `Subject`, and optional `Topic`.

---

## 3. Database Migrations with Alembic

Alembic is configured to read the active `SQLALCHEMY_DATABASE_URI` dynamically from `app.core.config.settings`.

### Common Alembic Commands:

1. **Apply all pending migrations:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Check current migration version:**
   ```bash
   alembic current
   ```

3. **Generate a new migration after editing models:**
   ```bash
   alembic revision --autogenerate -m "Describe your schema changes"
   ```

4. **Rollback one migration step:**
   ```bash
   alembic downgrade -1
   ```

---

## 4. Authentication & Security Architecture

NeuroLearn implements stateless JSON Web Token (JWT) authentication backed by high-entropy Argon2 password hashing.

### Security Highlights
- **Password Hashing:** Argon2 via `argon2-cffi`. Transparent automatic re-hashing if algorithm parameters upgrade. Passwords are never stored in plaintext and never leaked in schemas.
- **Token Mechanism:** Cryptographically signed HS256 JWT access tokens with strict expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **OAuth2 Compatible:** Uses `OAuth2PasswordBearer` conforming to the OpenAPI / Swagger specification (`/api/auth/login`).
- **Profile Tamper Protection:** Protected user endpoints ensure that unalterable attributes (`id`, `email`, `hashed_password`, `is_active`) cannot be modified via profile update payloads.

### Generating a Production Secret Key
Use Python's `secrets` module to generate a cryptographically strong 32-byte URL-safe secret for `JWT_SECRET`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Configure this in your `backend/.env` file:
```env
JWT_SECRET=your-32-byte-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### Authentication & User Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register a new student account (`201 Created`) | No |
| `POST` | `/api/auth/login` | Authenticate with JSON `{"email", "password"}` | No |
| `POST` | `/api/auth/token` | OAuth2 form authentication for Swagger UI (`username`, `password`) | No |
| `GET` | `/api/auth/me` | Fetch currently authenticated user profile | Yes (Bearer) |
| `GET` | `/api/users/me` | Fetch currently authenticated user profile | Yes (Bearer) |
| `PATCH` | `/api/users/me` | Update mutable profile fields (`full_name`, `program`, `semester`, `avatar_url`) | Yes (Bearer) |

### Interactive Swagger UI Authentication
1. Navigate to [http://localhost:8000/api/docs](http://localhost:8000/api/docs).
2. Click the **Authorize** button (top right of Swagger UI).
3. Under the `OAuth2PasswordBearer` flow, enter your email into the `username` field and your password into the `password` field, then click **Authorize**.
4. Swagger UI will automatically call `POST /api/auth/token` with `application/x-www-form-urlencoded` credentials and inject the Bearer token for all requests.
5. All locked endpoints (`/api/auth/me`, `/api/users/me`) can now be tested interactively.

---

## 5. Subjects & Topics Curriculum API

All curriculum endpoints require Bearer JWT authentication. Data isolation is strictly enforced per student account.

### Subject Endpoints (`/api/subjects`)

| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `POST` | `/api/subjects` | Create subject for authenticated student (`201`) | None |
| `GET` | `/api/subjects` | List owned subjects with nested topics | `skip` (int), `limit` (int), `search` (str) |
| `GET` | `/api/subjects/{subject_id}` | Retrieve single subject with nested topics | None |
| `PATCH` | `/api/subjects/{subject_id}` | Update permitted subject fields | None |
| `DELETE` | `/api/subjects/{subject_id}` | Delete subject and cascade delete child topics (`204`) | None |

### Topic Endpoints (`/api/topics` & `/api/subjects/{subject_id}/topics`)

| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `POST` | `/api/subjects/{subject_id}/topics` | Create a topic under an owned subject (`201`) | None |
| `GET` | `/api/subjects/{subject_id}/topics` | List topics under an owned subject | `skip` (int), `limit` (int), `search` (str) |
| `GET` | `/api/topics/{topic_id}` | Retrieve individual topic by ID | None |
| `PATCH` | `/api/topics/{topic_id}` | Update permitted topic fields | None |
| `DELETE` | `/api/topics/{topic_id}` | Delete a topic (`204`) | None |

### Request & Response Examples

#### Create Subject (`POST /api/subjects`):
```json
// Request
{
  "name": "Machine Learning",
  "code": "CS601",
  "color": "#6366F1",
  "description": "Foundations of Supervised and Unsupervised Learning",
  "target_mastery": 85.0
}

// Response (201 Created)
{
  "id": "e4b1c201-1b2c-4f8d-a8d6-3e79e656d012",
  "user_id": "90e2cf70-5b5c-4da9-b310-7e1e6ba5458f",
  "name": "Machine Learning",
  "code": "CS601",
  "color": "#6366F1",
  "description": "Foundations of Supervised and Unsupervised Learning",
  "target_mastery": 85.0,
  "exam_date": null,
  "created_at": "2026-11-23T23:25:00Z",
  "updated_at": "2026-11-23T23:25:00Z"
}
```

#### Create Topic (`POST /api/subjects/{subject_id}/topics`):
```json
// Request
{
  "name": "Neural Networks: Backpropagation Math",
  "difficulty": "Hard",
  "mastery_score": 50.0,
  "retention_score": 70.0,
  "completed": false
}

// Response (201 Created)
{
  "id": "52f6c042-4f3b-4895-888e-6701bbab4387",
  "subject_id": "e4b1c201-1b2c-4f8d-a8d6-3e79e656d012",
  "name": "Neural Networks: Backpropagation Math",
  "difficulty": "Hard",
  "mastery_score": 50.0,
  "retention_score": 70.0,
  "decay_rate_lambda": 0.08,
  "completed": false,
  "last_revised": null,
  "next_revision": null,
  "created_at": "2026-11-23T23:26:00Z",
  "updated_at": "2026-11-23T23:26:00Z"
}
```

---

## 6. Study Activity & Progress Tracking APIs

Authenticated endpoints for logging student activities, quizzes, revisions, and aggregate performance.

### 1. Study Sessions (`/api/study-sessions`)

| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `POST` | `/api/study-sessions` | Create a study session (`201 Created`) | None |
| `GET` | `/api/study-sessions` | List sessions with filters | `subject_id`, `topic_id`, `start_date`, `end_date`, `status`, `skip`, `limit` |
| `GET` | `/api/study-sessions/{session_id}` | Retrieve individual session by ID | None |
| `PATCH` | `/api/study-sessions/{session_id}` | Update status, duration, notes, slot | None |
| `DELETE` | `/api/study-sessions/{session_id}` | Delete a study session (`204`) | None |

### 2. Quiz Attempts (`/api/quiz-attempts`)

| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `POST` | `/api/quiz-attempts` | Record a quiz attempt (`201 Created`) | None |
| `GET` | `/api/quiz-attempts` | List quiz attempts with filters | `subject_id`, `topic_id`, `start_date`, `end_date`, `skip`, `limit` |
| `GET` | `/api/quiz-attempts/{attempt_id}` | Retrieve individual quiz attempt | None |

### 3. Revision History (`/api/revision-history`)

| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `POST` | `/api/revision-history` | Record a topic revision (`201 Created`) | None |
| `GET` | `/api/revision-history` | List revisions with filters | `topic_id`, `start_date`, `end_date`, `skip`, `limit` |
| `GET` | `/api/revision-history/{revision_id}` | Retrieve individual revision log | None |

### 4. Progress Tracking (`/api/analytics/progress`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/analytics/progress` | Computes live real-time aggregate statistics (study time, completed sessions, topic/subject mastery, quiz accuracy averages, and overall progress) |

---

## 7. Study Planner & AI Recommendations APIs

Authenticated endpoints for adaptive study planning, scheduling, rescheduling, and AI recommendations.

### 1. Study Planner (`/api/study-plan`)

| Method | Endpoint | Description | Query / Body Parameters |
|---|---|---|---|
| `GET` | `/api/study-plan` | Retrieve daily study plan & summary metrics | `date` (YYYY-MM-DD, defaults to today UTC) |
| `GET` | `/api/study-plan/week` | Retrieve weekly study schedule agenda | None |
| `POST` | `/api/study-plan/reschedule` | Reschedule a study session | `taskId`, `newDate`, `newSlot`, `reason` |
| `POST` | `/api/study-plan/complete` | Mark task completed / toggle status | `taskId`, `status` (`completed`, `pending`, `skipped`) |

### 2. AI Recommendations & Feedback (`/api/recommendations`)

| Method | Endpoint | Description | Query / Body Parameters |
|---|---|---|---|
| `GET` | `/api/recommendations` | List recommendations with filters | `status`, `agent_element`, `skip`, `limit` |
| `GET` | `/api/recommendations/hub` | Get grouped hub payload (active, history, 4-element counts) | None |
| `GET` | `/api/recommendations/{id}` | Retrieve recommendation details | None |
| `POST` | `/api/recommendations/{id}/accept` | Accept recommendation & automatically schedule study session | None |
| `POST` | `/api/recommendations/{id}/dismiss` | Dismiss recommendation | None |
| `POST` | `/api/recommendations/{id}/feedback` | Record student feedback on recommendation | `helpful` (bool), `note` (str) |

### 3. AI/ML Module Integration Contracts (`app/services/agent_adapters.py`)

NeuroLearn uses decoupled adapter interfaces (`AIAgentAdapter` and `MLRetentionAdapter`) to prepare for teammate's independent modules:
- **`AIAgentAdapter.generate_recommendations(user_id, student_history)`**: Formulates proposals categorized by 4 agent elements (*Performance Element*, *Critic*, *Learning Element*, *Problem Generator*).
- **`AIAgentAdapter.evaluate_quiz_critique(attempt_id, score, accuracy, topic_context)`**: Formulates explainable diagnosis for weak subtopics.
- **`MLRetentionAdapter.predict_retention(topic_id, elapsed_days, decay_lambda, repetition_count)`**: Computes mathematical memory retention score.
- **`MLRetentionAdapter.calibrate_decay_rate(revision_history, quiz_scores)`**: Calibrates individualized decay parameter $\lambda$.

---

## 8. Setup & Running the Server

### Step-by-Step Local Setup

1. **Activate virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     cd backend
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     cd backend
     source venv/bin/activate
     ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Apply database migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

Once running:
- **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Interactive Swagger Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc:** [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

---

## 9. Running Automated Tests

Run the complete test suite with `pytest`:

```bash
cd backend
pytest
```
