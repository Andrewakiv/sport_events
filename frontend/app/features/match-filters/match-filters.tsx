import type { FormEvent } from "react";
import { Form, Link, useSubmit } from "react-router";

import type { MatchFilters } from "../../shared/api/types";

const STATUSES = [
  ["", "Усі статуси"],
  ["SCHEDULED", "Заплановано"],
  ["TIMED", "Час визначено"],
  ["IN_PLAY", "У грі"],
  ["FINISHED", "Завершено"],
  ["POSTPONED", "Перенесено"],
] as const;

export function MatchFiltersPanel({ filters }: { filters: MatchFilters }) {
  const submit = useSubmit();

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
          <p className="eyebrow">Точний пошук</p>
          <h2 id="filters-heading">Фільтри</h2>
        </div>
        <Link
          className="reset-link"
          to={filters.demo ? "?demo=1" : "/football/champions-league/matches"}
        >
          Скинути
        </Link>
      </div>

      <Form method="get" className="filter-form" onSubmit={applyFilters}>
        {filters.demo && <input type="hidden" name="demo" value="1" />}

        <label>
          <span>Сезон</span>
          <select name="season" defaultValue={filters.season ?? ""}>
            <option value="">Усі сезони</option>
            <option value="2026">2026 / 27</option>
            <option value="2025">2025 / 26</option>
            <option value="2024">2024 / 25</option>
            <option value="2023">2023 / 24</option>
          </select>
        </label>

        <label>
          <span>Дата матчу · UTC</span>
          <input name="date" type="date" defaultValue={filters.date ?? ""} />
        </label>

        <label>
          <span>ID команди</span>
          <input
            name="team_id"
            type="number"
            min="1"
            placeholder="Наприклад, 64"
            defaultValue={filters.teamId ?? ""}
          />
        </label>

        <label>
          <span>Статус</span>
          <select name="status" defaultValue={filters.status ?? ""}>
            {STATUSES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <button className="button button-primary" type="submit">
          Застосувати
        </button>
      </Form>

      <div className="filter-note">
        <span aria-hidden="true">i</span>
        <p>
          Фільтри комбінуються. Дата запиту — UTC, а час у картках — локальний.
        </p>
      </div>
    </aside>
  );
}
