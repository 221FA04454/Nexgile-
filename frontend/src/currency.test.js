import { describe, expect, it } from "vitest";
import { formatINR, formatINRCompact } from "./currency";

describe("formatINR", () => {
  it("uses Indian grouping and the rupee symbol", () => {
    expect(formatINR(1000)).toBe("₹1,000");
    expect(formatINR(10000)).toBe("₹10,000");
    expect(formatINR(100000)).toBe("₹1,00,000");
    expect(formatINR(1000000)).toBe("₹10,00,000");
    expect(formatINR(10000000)).toBe("₹1,00,00,000");
  });

  it("formats zero, negatives, decimals, and large values", () => {
    expect(formatINR(0)).toBe("₹0");
    expect(formatINR(-1000)).toMatch(/-.*₹1,000|₹-1,000|-₹1,000/);
    expect(formatINR(1234.56, 2)).toMatch(/₹1,234\.56/);
    expect(formatINR(2810334)).toBe("₹28,10,334");
    expect(formatINR(2140000)).toBe("₹21,40,000");
    expect(formatINR(3000000)).toBe("₹30,00,000");
  });

  it("formats portfolio, tax, retirement, and goal magnitudes", () => {
    expect(formatINR(2810334.3)).toBe("₹28,10,334");
    expect(formatINR(42600)).toBe("₹42,600");
    expect(formatINR(210000)).toBe("₹2,10,000");
    expect(formatINR(2500000)).toBe("₹25,00,000");
    expect(formatINR(1850000)).toBe("₹18,50,000");
    expect(formatINR(650000)).toBe("₹6,50,000");
  });

  it("returns an em dash for missing values", () => {
    expect(formatINR(null)).toBe("—");
    expect(formatINR(undefined)).toBe("—");
  });
});

describe("formatINRCompact", () => {
  it("uses lakh/crore compact labels for chart axes", () => {
    expect(formatINRCompact(100000)).toBe("₹1.0 L");
    expect(formatINRCompact(10000000)).toBe("₹1.0 Cr");
  });
});
