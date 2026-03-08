# Ghost-Protocol

**An Autonomous Non-Human Identity (NHI) Auditor and Governance tool.** Uses Agentic AI (Ollama/Llama 3) to analyze AWS IAM & CloudTrail logs for real-time "Least Privilege" enforcement.

GhostProtocol discovers, analyses, and enforces least-privilege policies on machine identities (IAM Roles used by EC2, Lambda, and other AWS services). It combines real-time AWS scanning with AI-powered policy recommendations to close the gap between *what a role can do* and *what it actually does*.

---

## Problem Solved

Enterprises run thousands of IAM Roles that are consumed by services rather than humans. These **Non-Human Identities** are frequently over-provisioned — they carry broad wildcard permissions despite using only a handful of API actions. GhostProtocol:

1. **Discovers** every NHI role in your AWS account.
2. **Correlates** allowed permissions against actual CloudTrail usage (last 30 days via Athena).
3. **Generates** a least-privilege replacement policy using a local LLM (Ollama / Llama 3).
4. **Quarantines** high-risk identities instantly with a non-destructive Deny-All permissions boundary.

---

## Technical Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | Python · FastAPI · Uvicorn |
| **AWS Integration** | Boto3 · IAM · CloudTrail · Athena |
| **AI / LLM** | LangChain · Ollama (Llama 3, local) |
| **Database** | Supabase (Postgres) |
| **Frontend** | Next.js 15 · React 19 · TypeScript |
| **UI Kit** | Tailwind CSS · Radix UI · Framer Motion |
| **Infra** | Docker Compose · PostgreSQL 16 |

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Next.js Dashboard                         │
│   Identity Risk Table · Policy Diff Modal · Quarantine UI      │
└────────────────────┬───────────────────────────────────────────┘
                     │  REST  (fetch)
┌────────────────────▼───────────────────────────────────────────┐
│                      FastAPI Backend                            │
│   /scan  ·  /identities  ·  /analyze  ·  /quarantine           │
├────────────┬───────────────┬───────────────┬───────────────────┤
│  scanner   │   analyzer    │   database    │  config            │
│  (Boto3)   │  (LangChain)  │  (Supabase)   │  (.env)            │
└─────┬──────┴───────┬───────┴───────┬───────┴───────────────────┘
      │              │               │
 AWS IAM/Athena   Ollama (local)   Supabase / Postgres
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- AWS credentials configured (`aws configure` or env vars)
- [Ollama](https://ollama.ai) running locally with the `llama3` model pulled
- A Supabase project (or use the local Postgres container for dev)

### 1. Clone & configure

```bash
git clone https://github.com/your-username/ghostprotocol.git
cd ghostprotocol
cp backend/.env.example backend/.env
# Edit backend/.env with your Supabase & AWS credentials
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### 3. Run locally (dev)

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Supabase Schema

Create the `identities` table in your Supabase project:

```sql
CREATE TABLE identities (
  arn           TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  type          TEXT,
  trust_principals JSONB DEFAULT '[]',
  allowed_actions  JSONB DEFAULT '[]',
  used_actions     JSONB DEFAULT '[]',
  risk_score    INTEGER DEFAULT 0,
  is_quarantined BOOLEAN DEFAULT FALSE,
  last_activity  TIMESTAMPTZ,
  quarantined_at TIMESTAMPTZ,
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/scan` | Trigger AWS NHI scan |
| `GET` | `/identities` | List all identities (by risk) |
| `GET` | `/identities/{arn}` | Get single identity |
| `POST` | `/analyze` | AI policy analysis for an ARN |
| `POST` | `/quarantine` | Apply Deny-All boundary to an ARN |

---

## How Quarantine Works

The quarantine mechanism is **non-destructive and reversible**:

1. A managed IAM policy with `"Effect": "Deny", "Action": "*", "Resource": "*"` is created once.
2. It is attached as a **Permissions Boundary** to the target role.
3. The role still exists — no policies are deleted — but every API call is denied.
4. To restore, simply remove the permissions boundary from the role in the AWS console or via CLI.

---

## License

Apache-2.0
