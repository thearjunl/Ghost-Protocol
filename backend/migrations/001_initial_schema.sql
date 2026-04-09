-- GhostProtocol Initial Database Schema
-- Creates the identities table for storing NHI audit data

CREATE TABLE IF NOT EXISTS identities (
  arn           TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  type          TEXT,
  trust_principals JSONB DEFAULT '[]'::jsonb,
  allowed_actions  JSONB DEFAULT '[]'::jsonb,
  used_actions     JSONB DEFAULT '[]'::jsonb,
  risk_score    INTEGER DEFAULT 0,
  is_quarantined BOOLEAN DEFAULT FALSE,
  last_activity  TIMESTAMPTZ,
  quarantined_at TIMESTAMPTZ,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_identities_risk_score ON identities(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_identities_is_quarantined ON identities(is_quarantined);
CREATE INDEX IF NOT EXISTS idx_identities_type ON identities(type);
CREATE INDEX IF NOT EXISTS idx_identities_updated_at ON identities(updated_at DESC);

-- Create a function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_identities_updated_at ON identities;
CREATE TRIGGER update_identities_updated_at
    BEFORE UPDATE ON identities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE identities IS 'Stores Non-Human Identity (NHI) audit data from AWS IAM';
COMMENT ON COLUMN identities.arn IS 'AWS IAM Role ARN (Primary Key)';
COMMENT ON COLUMN identities.name IS 'IAM Role name';
COMMENT ON COLUMN identities.type IS 'Service type (EC2, LAMBDA, ECS, etc.)';
COMMENT ON COLUMN identities.trust_principals IS 'List of AWS service principals that can assume this role';
COMMENT ON COLUMN identities.allowed_actions IS 'IAM actions allowed by attached policies';
COMMENT ON COLUMN identities.used_actions IS 'IAM actions actually used (from CloudTrail)';
COMMENT ON COLUMN identities.risk_score IS 'Risk score from 0-100 (higher = more over-privileged)';
COMMENT ON COLUMN identities.is_quarantined IS 'Whether the role has been quarantined';
COMMENT ON COLUMN identities.last_activity IS 'Last time the role was used';
COMMENT ON COLUMN identities.quarantined_at IS 'Timestamp when role was quarantined';
