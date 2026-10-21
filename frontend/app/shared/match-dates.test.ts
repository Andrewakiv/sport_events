// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("local match calendar dates", () => {
  it("uses the next day in Tokyo consistently with card and detail times", async () => {
    vi.stubEnv("TZ", "Asia/Tokyo");
    vi.resetModules();
    const {
      localDateKey,
      formatMatchDate,
      formatMatchTime,
      formatLongKickoff,
    } = await import("./format");
    const kickoff = "2026-10-07T19:00:00Z";

    expect(localDateKey(kickoff)).toBe("2026-10-08");
    expect(formatMatchDate(kickoff)).toMatch(/^Thursday,? 8 October$/);
    expect(formatMatchTime(kickoff)).toBe("04:00");
    expect(formatLongKickoff(kickoff)).toMatch(/^Thursday,? 8 October 2026/);
    // Different UTC dates can belong to the same local date group.
    expect(localDateKey("2026-10-08T02:00:00Z")).toBe(localDateKey(kickoff));
    expect(localDateKey("2026-10-07T14:59:00Z")).not.toBe(
      localDateKey(kickoff),
    );
  });

  it("uses the previous day west of UTC and keeps distinct years separate", async () => {
    vi.stubEnv("TZ", "America/Los_Angeles");
    vi.resetModules();
    const { localDateKey, formatMatchDate, formatMatchTime } =
      await import("./format");
    const kickoff = "2026-10-08T02:00:00Z";

    expect(localDateKey(kickoff)).toBe("2026-10-07");
    expect(formatMatchDate(kickoff)).toMatch(/^Wednesday,? 7 October$/);
    expect(formatMatchTime(kickoff)).toBe("19:00");
    expect(localDateKey("2027-01-01T02:00:00Z")).toBe("2026-12-31");
  });

  it("groups both occurrences of a repeated DST hour on the same local day", async () => {
    vi.stubEnv("TZ", "America/New_York");
    vi.resetModules();
    const { localDateKey, formatMatchDate, formatMatchTime } =
      await import("./format");
    const first = "2026-11-01T05:30:00Z";
    const second = "2026-11-01T06:30:00Z";

    expect(localDateKey(first)).toBe("2026-11-01");
    expect(localDateKey(second)).toBe(localDateKey(first));
    expect(formatMatchDate(second)).toMatch(/^Sunday,? 1 November$/);
    expect(formatMatchTime(first)).toBe("01:30");
    expect(formatMatchTime(second)).toBe("01:30");
  });
});
