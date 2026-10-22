const MATCHES_PATH = "/football/champions-league/matches";
const PARSE_ORIGIN = "http://localhost";

export function safeReturnTo(value: string | null): string {
  if (value === null) return MATCHES_PATH;
  try {
    const url = new URL(value, PARSE_ORIGIN);
    if (url.origin !== PARSE_ORIGIN || url.pathname !== MATCHES_PATH) {
      return MATCHES_PATH;
    }
    return `${url.pathname}${url.search}`;
  } catch {
    return MATCHES_PATH;
  }
}
