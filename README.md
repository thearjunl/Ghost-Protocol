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

#### Ollama Setup

1. Install Ollama from [https://ollama.ai](https://ollama.ai).
2. Pull the Llama 3 model:
   ```bash
   ollama pull llama3
   ```
3. Ensure Ollama is running (default: `http://localhost:11434`). Verify with:
   ```bash
   curl http://localhost:11434/api/tags
   ```

#### AWS CloudTrail / Athena Setup

GhostProtocol queries CloudTrail logs via Athena for used-action correlation.

1. Enable CloudTrail logging to an S3 bucket in your account.
2. Create an Athena database pointing at the CloudTrail S3 bucket:
   ```sql
   CREATE EXTERNAL TABLE cloudtrail_logs (
     eventTime STRING, eventSource STRING, eventName STRING,
     userIdentity STRUCT<arn:STRING, type:STRING>
   )
   ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
   LOCATION 's3://YOUR-CLOUDTRAIL-BUCKET/AWSLogs/ACCOUNT_ID/CloudTrail/';
   ```
3. Create an S3 bucket for Athena query results (e.g. `s3://my-athena-results/`).
4. The IAM credentials used by GhostProtocol need these permissions:
   - `iam:ListRoles`, `iam:ListAttachedRolePolicies`, `iam:GetPolicy`, `iam:GetPolicyVersion`, `iam:ListRolePolicies`, `iam:GetRolePolicy`
   - `iam:CreatePolicy`, `iam:PutRolePermissionsBoundary` (for quarantine)
   - `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:GetQueryResults`
   - `s3:GetObject`, `s3:PutObject` on the Athena results bucket
   - `sts:GetCallerIdentity`

### 1. Clone & configure

```bash
git clone https://github.com/your-username/ghostprotocol.git
cd ghostprotocol
cp backend/.env.example backend/.env
# Edit backend/.env with your Supabase & AWS credentials
```

#### Environment Variables

Create `backend/.env` with the following values:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# AWS
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# CloudTrail Athena
ATHENA_DATABASE=cloudtrail_logs
ATHENA_OUTPUT_BUCKET=s3://your-athena-results-bucket/

# Ollama LLM
OLLAMA_BASE_URL=http://localhost:11434

# Logging
LOG_LEVEL=INFO

# CORS — comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:3000

# Authentication — set a strong secret to enable API key auth (leave empty to disable)
GHOSTPROTOCOL_API_KEY=
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
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

## Security

### API Key Authentication

Set `GHOSTPROTOCOL_API_KEY` in `backend/.env` to enable authentication. All endpoints (except `/health`) will require the header:

```
X-API-Key: your-secret-key
```

When the variable is empty or unset, authentication is disabled (suitable for local development).

### Rate Limiting

All endpoints are rate-limited by default:

| Endpoint | Limit |
|----------|-------|
| `GET /health` | 120/min |
| `GET /identities` | 60/min |
| `GET /identities/{arn}` | 60/min |
| `POST /scan` | 10/min |
| `POST /analyze` | 10/min |
| `POST /quarantine` | 5/min |

### CORS

CORS origins are configured via the `CORS_ORIGINS` environment variable (comma-separated). Defaults to `http://localhost:3000`.

### Request Tracing

Every response includes an `X-Request-ID` header for tracing. Pass your own `X-Request-ID` in the request to correlate with upstream systems.

---

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Connection refused" on port 8000** | Ensure the backend is running: `uvicorn main:app --reload` |
| **"Failed to load identities"** | Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env` |
| **"AI analysis failed"** | Verify Ollama is running: `curl http://localhost:11434/api/tags`. Ensure `llama3` is pulled. |
| **"Scan failed"** | Verify AWS credentials and IAM permissions (see Prerequisites above) |
| **"Athena query failed"** | Check `ATHENA_DATABASE` and `ATHENA_OUTPUT_BUCKET` values; ensure CloudTrail table exists |
| **401 Unauthorized** | If `GHOSTPROTOCOL_API_KEY` is set, include `X-API-Key` header in requests |
| **429 Too Many Requests** | You've hit the rate limit. Wait and retry. |

---

## License

Apache-2.0
