const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export interface Identity {
  arn: string;
  name: string;
  type: string;
  trust_principals: string[];
  allowed_actions: string[];
  used_actions: string[];
  risk_score: number;
  is_quarantined: boolean;
  last_activity: string | null;
  quarantined_at?: string | null;
}

export interface AnalysisResult {
  risk_score: number;
  unused_actions: string[];
  recommended_policy: Record<string, unknown>;
  summary: string;
}

function getHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  return headers;
}

export async function fetchIdentities(): Promise<Identity[]> {
  const res = await fetch(`${API_BASE}/identities`, {
    cache: "no-store",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch identities");
  return res.json();
}

export async function triggerScan(): Promise<{ scanned: number }> {
  const res = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Scan failed");
  return res.json();
}

export async function analyzeIdentity(arn: string): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ arn }),
  });
  if (!res.ok) throw new Error("Analysis failed");
  return res.json();
}

export async function quarantineIdentity(
  arn: string
): Promise<{ arn: string; quarantined: boolean }> {
  const res = await fetch(`${API_BASE}/quarantine`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ arn }),
  });
  if (!res.ok) throw new Error("Quarantine failed");
  return res.json();
}

