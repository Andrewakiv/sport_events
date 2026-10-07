import type { Match } from "./api/types";

const dateFormatter = new Intl.DateTimeFormat("uk-UA", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

const timeFormatter = new Intl.DateTimeFormat("uk-UA", {
  hour: "2-digit",
  minute: "2-digit",
});

const longDateFormatter = new Intl.DateTimeFormat("uk-UA", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
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

export function utcDateKey(match: Match): string {
  return match.kickoff_at.slice(0, 10);
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
    LEAGUE_STAGE: "Етап ліги",
    GROUP_STAGE: "Груповий етап",
    LAST_16: "1/8 фіналу",
    QUARTER_FINALS: "Чвертьфінал",
    SEMI_FINALS: "Півфінал",
    FINAL: "Фінал",
  };
  return labels[stage] ?? stage.replaceAll("_", " ").toLocaleLowerCase("uk-UA");
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    FINISHED: "Завершено",
    IN_PLAY: "У грі",
    PAUSED: "Перерва",
    TIMED: "Заплановано",
    SCHEDULED: "Заплановано",
    POSTPONED: "Перенесено",
    CANCELLED: "Скасовано",
  };
  return (
    labels[status] ?? status.replaceAll("_", " ").toLocaleLowerCase("uk-UA")
  );
}

function sentenceCase(value: string): string {
  return value.charAt(0).toLocaleUpperCase("uk-UA") + value.slice(1);
}
