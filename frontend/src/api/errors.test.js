import { describe, expect, it } from "vitest";
import { parseApiError } from "./errors";

describe("API error envelope", () => {
  it("reads production error objects", () => {
    const err = parseApiError({ error: { code: "FORBIDDEN", message: "Not allowed", request_id: "abc" } }, 403);
    expect(err.message).toBe("Not allowed");
    expect(err.code).toBe("FORBIDDEN");
    expect(err.requestId).toBe("abc");
    expect(err.status).toBe(403);
  });
});
