import { describe, expect, it } from "vitest";

import { stageLabel, statusLabel, teamInitials } from "./format";

describe("presentation helpers", () => {
  it("creates compact team initials without generic club suffixes", () => {
    expect(teamInitials("Liverpool FC")).toBe("L");
    expect(teamInitials("Real Madrid CF")).toBe("RM");
    expect(teamInitials(undefined)).toBe("?");
  });

  it("localizes known stage and status values", () => {
    expect(stageLabel("QUARTER_FINALS")).toBe("Чвертьфінал");
    expect(statusLabel("FINISHED")).toBe("Завершено");
  });
});
