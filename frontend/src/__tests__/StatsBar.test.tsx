import { render, screen } from "@testing-library/react";
import StatsBar from "@/components/StatsBar";
import type { Identity } from "@/lib/api";

// Mock lucide-react icons to avoid SVG rendering issues in tests
jest.mock("lucide-react", () => ({
  Shield: (props: any) => <span data-testid="icon-shield" {...props} />,
  AlertTriangle: (props: any) => <span data-testid="icon-alert" {...props} />,
  Activity: (props: any) => <span data-testid="icon-activity" {...props} />,
  ShieldOff: (props: any) => <span data-testid="icon-shieldoff" {...props} />,
}));

function makeIdentity(overrides: Partial<Identity> = {}): Identity {
  return {
    arn: "arn:aws:iam::123456789012:role/TestRole",
    name: "TestRole",
    type: "EC2",
    trust_principals: ["ec2.amazonaws.com"],
    allowed_actions: ["s3:GetObject"],
    used_actions: ["s3:GetObject"],
    risk_score: 50,
    is_quarantined: false,
    last_activity: null,
    ...overrides,
  };
}

describe("StatsBar", () => {
  it("renders total NHI count", () => {
    const identities = [makeIdentity(), makeIdentity({ arn: "arn:aws:iam::123456789012:role/B" })];
    render(<StatsBar identities={identities} />);
    expect(screen.getByText("Total NHIs")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("counts critical risk identities (>80)", () => {
    const identities = [
      makeIdentity({ risk_score: 90 }),
      makeIdentity({ arn: "arn:aws:iam::123456789012:role/B", risk_score: 40 }),
      makeIdentity({ arn: "arn:aws:iam::123456789012:role/C", risk_score: 85 }),
    ];
    render(<StatsBar identities={identities} />);
    expect(screen.getByText("Critical Risk")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("counts quarantined identities", () => {
    const identities = [
      makeIdentity({ is_quarantined: true }),
      makeIdentity({ arn: "arn:aws:iam::123456789012:role/B", is_quarantined: false }),
    ];
    render(<StatsBar identities={identities} />);
    expect(screen.getByText("Quarantined")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("computes average risk score", () => {
    const identities = [
      makeIdentity({ risk_score: 60 }),
      makeIdentity({ arn: "arn:aws:iam::123456789012:role/B", risk_score: 80 }),
    ];
    render(<StatsBar identities={identities} />);
    expect(screen.getByText("Avg Risk Score")).toBeInTheDocument();
    expect(screen.getByText("70")).toBeInTheDocument();
  });

  it("shows zero avg when no identities", () => {
    render(<StatsBar identities={[]} />);
    // All stats should be 0
    const zeroes = screen.getAllByText("0");
    expect(zeroes.length).toBeGreaterThanOrEqual(4);
  });
});
