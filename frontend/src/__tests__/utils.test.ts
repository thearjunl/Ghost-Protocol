import { cn } from "@/lib/utils";

describe("cn utility", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "extra")).toBe("base extra");
  });

  it("merges tailwind conflicts correctly", () => {
    // twMerge should resolve p-4 vs p-2 to p-2 (last wins)
    expect(cn("p-4", "p-2")).toBe("p-2");
  });

  it("handles empty inputs", () => {
    expect(cn()).toBe("");
  });
});
