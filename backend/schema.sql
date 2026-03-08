-- GhostProtocol — Supabase / PostgreSQL Schema
-- Run this in your Supabase SQL Editor or against a local Postgres instance.

CREATE TABLE IF NOT EXISTS identities (
  arn              TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  type             TEXT,
  trust_principals JSONB DEFAULT '[]'::jsonb,
  allowed_actions  JSONB DEFAULT '[]'::jsonb,
  used_actions     JSONB DEFAULT '[]'::jsonb,
  risk_score       INTEGER DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
  is_quarantined   BOOLEAN DEFAULT FALSE,
  last_activity    TIMESTAMPTZ,
  quarantined_at   TIMESTAMPTZ,
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Index for dashboard ordering (risk_score DESC is the primary sort)
CREATE INDEX IF NOT EXISTS idx_identities_risk
  ON identities (risk_score DESC);

-- Index for filtering quarantined identities
CREATE INDEX IF NOT EXISTS idx_identities_quarantined
  ON identities (is_quarantined)
  WHERE is_quarantined = TRUE;
