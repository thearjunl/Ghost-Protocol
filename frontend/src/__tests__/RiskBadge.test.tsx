import { render, screen } from "@testing-library/react";
import RiskBadge from "@/components/RiskBadge";

describe("RiskBadge", () => {
  it("renders the score", () => {
    render(<RiskBadge score={75} />);
    expect(screen.getByText("75")).toBeInTheDocument();
  });

  it("applies red styling for critical scores (>80)", () => {
    const { container } = render(<RiskBadge score={90} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-red-400");
  });

  it("applies yellow styling for warning scores (51-80)", () => {
    const { container } = render(<RiskBadge score={65} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-yellow-400");
  });

  it("applies green styling for safe scores (<=50)", () => {
    const { container } = render(<RiskBadge score={30} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-green-400");
  });

  it("applies green at boundary score 50", () => {
    const { container } = render(<RiskBadge score={50} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-green-400");
  });

  it("applies yellow at boundary score 80", () => {
    const { container } = render(<RiskBadge score={80} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-yellow-400");
  });

  it("applies red at boundary score 81", () => {
    const { container } = render(<RiskBadge score={81} />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain("text-red-400");
  });
});
