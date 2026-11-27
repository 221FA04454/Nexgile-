import { describe, expect, it } from "vitest";
import { SUGGESTED_PROMPTS } from "./AIWealthAgent";

describe("AI WealthAgent prompts", () => {
  it("offers the Phase 2 suggested questions", () => {
    expect(SUGGESTED_PROMPTS).toEqual([
      "How is my portfolio performing?",
      "What tax opportunities do I have?",
      "Am I on track for retirement?",
      "What documents need my attention?",
      "Summarize my household finances.",
    ]);
  });
});
