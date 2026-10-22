import { describe, expect, it } from "vitest";

import {
  formatLongKickoff,
  formatMatchDate,
  stageLabel,
  statusLabel,
  teamInitials,
} from "./format";

describe("presentation helpers", () => {
  it("creates compact team initials without generic club suffixes", () => {
    expect(teamInitials("Liverpool FC")).toBe("L");
    expect(teamInitials("Real Madrid CF")).toBe("RM");
    expect(teamInitials(undefined)).toBe("?");
  });

  it("localizes known stage and status values", () => {
    expect(stageLabel("QUARTER_FINALS")).toBe("Quarter-finals");
    expect(statusLabel("FINISHED")).toBe("Finished");
  });

  it("formats dates in English", () => {
    expect(formatMatchDate("2026-10-21T12:00:00Z")).toContain("October");
    expect(formatLongKickoff("2026-10-21T12:00:00Z")).toContain("October 2026");
  });
});
