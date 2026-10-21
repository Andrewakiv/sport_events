import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider, useLocation } from "react-router";
import { describe, expect, it } from "vitest";

import { parseFilters } from "../../shared/filters";
import { MatchFiltersPanel } from "./match-filters";

function FiltersRoute() {
  const location = useLocation();
  const filters = parseFilters(new URL(location.search, "http://localhost"));
  return <MatchFiltersPanel filters={filters} />;
}

describe("MatchFiltersPanel", () => {
  it("removes empty filters, resets offset and preserves the page size", async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter(
      [{ path: "/", Component: FiltersRoute }],
      { initialEntries: ["/?demo=1&limit=2&offset=4"] },
    );
    render(<RouterProvider router={router} />);

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Статус" }),
      "FINISHED",
    );
    await user.click(screen.getByRole("button", { name: "Застосувати" }));

    await waitFor(() => {
      const params = new URLSearchParams(router.state.location.search);
      expect(Object.fromEntries(params)).toEqual({
        demo: "1",
        limit: "2",
        status: "FINISHED",
      });
    });
  });

  it("updates form values after reset and back navigation", async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter(
      [{ path: "/", Component: FiltersRoute }],
      { initialEntries: ["/?demo=1&season=2026&status=FINISHED"] },
    );
    render(<RouterProvider router={router} />);

    await user.click(screen.getByRole("link", { name: "Скинути" }));
    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: "Сезон" })).toHaveValue("");
      expect(screen.getByRole("combobox", { name: "Статус" })).toHaveValue("");
    });

    await act(async () => {
      await router.navigate(-1);
    });
    expect(screen.getByRole("combobox", { name: "Сезон" })).toHaveValue("2026");
    expect(screen.getByRole("combobox", { name: "Статус" })).toHaveValue(
      "FINISHED",
    );
  });
});
