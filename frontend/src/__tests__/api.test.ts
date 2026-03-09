import {
  fetchIdentities,
  triggerScan,
  analyzeIdentity,
  quarantineIdentity,
} from "@/lib/api";

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchIdentities", () => {
  it("returns identities on success", async () => {
    const data = [{ arn: "arn:aws:iam::123:role/TestRole", name: "TestRole", risk_score: 50 }];
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => data,
    });

    const result = await fetchIdentities();
    expect(result).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/identities"),
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("throws on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    await expect(fetchIdentities()).rejects.toThrow("Failed to fetch identities");
  });
});

describe("triggerScan", () => {
  it("posts to /scan", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ scanned: 3 }),
    });

    const result = await triggerScan();
    expect(result.scanned).toBe(3);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/scan"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on scan failure", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    await expect(triggerScan()).rejects.toThrow("Scan failed");
  });
});

describe("analyzeIdentity", () => {
  it("posts ARN to /analyze", async () => {
    const analysis = { risk_score: 75, unused_actions: ["s3:*"], recommended_policy: {}, summary: "risky" };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => analysis,
    });

    const result = await analyzeIdentity("arn:aws:iam::123:role/R");
    expect(result.risk_score).toBe(75);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/analyze"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arn: "arn:aws:iam::123:role/R" }),
      }),
    );
  });

  it("throws on analysis failure", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    await expect(analyzeIdentity("arn:aws:iam::123:role/R")).rejects.toThrow("Analysis failed");
  });
});

describe("quarantineIdentity", () => {
  it("posts ARN to /quarantine", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ arn: "arn:aws:iam::123:role/R", quarantined: true }),
    });

    const result = await quarantineIdentity("arn:aws:iam::123:role/R");
    expect(result.quarantined).toBe(true);
  });

  it("throws on quarantine failure", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    await expect(quarantineIdentity("arn:aws:iam::123:role/R")).rejects.toThrow("Quarantine failed");
  });
});
