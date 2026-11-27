import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ErrorState } from "../components/ui";
import { visibleNav } from "../layout/navConfig";

describe("error and empty states", () => {
  it("renders an API error state", () => {
    render(<ErrorState message="The wealth service is unavailable." onRetry={() => {}} />);
    expect(screen.getByText(/could not reach the wealth service/i)).toBeTruthy();
    expect(screen.getByText(/unavailable/i)).toBeTruthy();
  });

  it("error boundary shows recovery", () => {
    function Boom() {
      throw new Error("dashboard crash");
    }
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeTruthy();
  });
});

describe("role navigation contract", () => {
  it("hides advisor workstation from clients", () => {
    const labels = visibleNav("CLIENT").map((i) => i.to);
    expect(labels).not.toContain("/advisor");
    expect(labels).not.toContain("/integrations");
    expect(visibleNav("ADVISOR").map((i) => i.to)).toContain("/advisor");
    expect(visibleNav("ADVISOR").map((i) => i.to)).toContain("/integrations");
  });
});
