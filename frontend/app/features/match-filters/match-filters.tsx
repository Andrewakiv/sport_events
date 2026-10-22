import type { FormEvent } from "react";
import { Form, Link, useNavigation, useSubmit } from "react-router";

import type { MatchFilters } from "../../shared/api/types";

const STATUSES = [
  ["", "All statuses"],
  ["SCHEDULED", "Scheduled"],
  ["TIMED", "Kick-off confirmed"],
  ["IN_PLAY", "In play"],
  ["FINISHED", "Finished"],
  ["POSTPONED", "Postponed"],
] as const;

export function MatchFiltersPanel({ filters }: { filters: MatchFilters }) {
  const submit = useSubmit();
  const pending = useNavigation().state !== "idle";

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    for (const [key, value] of Array.from(data.entries())) {
      if (value === "") data.delete(key);
    }
    data.delete("offset");
    void submit(data, { method: "get" });
  }

  return (
    <aside className="filter-panel" aria-labelledby="filters-heading">
      <div className="filter-heading">
        <div>
          <p className="eyebrow">Refine your search</p>
          <h2 id="filters-heading">Filters</h2>
        </div>
        <Link className="reset-link" to="/football/champions-league/matches">
          Reset
        </Link>
      </div>

      <Form
        key={JSON.stringify(filters)}
        method="get"
        className="filter-form"
        onSubmit={applyFilters}
      >
        <input type="hidden" name="limit" value={filters.limit} />

        <label>
          <span>Season</span>
          <select name="season" defaultValue={filters.season ?? ""}>
            <option value="">All seasons</option>
            <option value="2026">2026 / 27</option>
            <option value="2025">2025 / 26</option>
            <option value="2024">2024 / 25</option>
            <option value="2023">2023 / 24</option>
          </select>
        </label>

        <label>
          <span>Match date · UTC</span>
          <input name="date" type="date" defaultValue={filters.date ?? ""} />
        </label>

        <label>
          <span>Status</span>
          <select name="status" defaultValue={filters.status ?? ""}>
            {STATUSES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <button
          className="button button-primary"
          type="submit"
          disabled={pending}
        >
          Apply
        </button>
      </Form>

      <div className="filter-note">
        <span aria-hidden="true">i</span>
        <p>
          Filters work together. Match dates use UTC; kick-off times are local.
        </p>
      </div>
    </aside>
  );
}
