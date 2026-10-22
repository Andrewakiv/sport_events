const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const longDateFormatter = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZoneName: "short",
});

export function formatMatchDate(isoDate: string): string {
  return sentenceCase(dateFormatter.format(new Date(isoDate)));
}

export function formatMatchTime(isoDate: string): string {
  return timeFormatter.format(new Date(isoDate));
}

export function formatLongKickoff(isoDate: string): string {
  return sentenceCase(longDateFormatter.format(new Date(isoDate)));
}

export function localDateKey(isoDate: string): string {
  const date = new Date(isoDate);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function teamInitials(name: string | undefined): string {
  if (!name) return "?";
  const ignored = new Set(["fc", "cf", "ac", "club"]);
  const words = name
    .split(/\s+/)
    .filter((word) => !ignored.has(word.toLowerCase()));
  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

export function stageLabel(stage: string): string {
  const labels: Record<string, string> = {
    LEAGUE_STAGE: "League stage",
    GROUP_STAGE: "Group stage",
    LAST_16: "Round of 16",
    QUARTER_FINALS: "Quarter-finals",
    SEMI_FINALS: "Semi-finals",
    FINAL: "Final",
  };
  return labels[stage] ?? stage.replaceAll("_", " ").toLocaleLowerCase("en-GB");
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    FINISHED: "Finished",
    IN_PLAY: "In play",
    PAUSED: "Paused",
    TIMED: "Kick-off confirmed",
    SCHEDULED: "Scheduled",
    POSTPONED: "Postponed",
    CANCELLED: "Cancelled",
  };
  return (
    labels[status] ?? status.replaceAll("_", " ").toLocaleLowerCase("en-GB")
  );
}

function sentenceCase(value: string): string {
  return value.charAt(0).toLocaleUpperCase("en-GB") + value.slice(1);
}
