import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { PageOutOfRange } from "./page-out-of-range";

describe("PageOutOfRange", () => {
  it("links to the first and last page while keeping active filters", () => {
    render(
      <MemoryRouter initialEntries={["/?status=FINISHED&limit=25&offset=100"]}>
        <PageOutOfRange limit={25} total={51} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/51 matches fit your filters/)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Go to last page" }),
    ).toHaveAttribute("href", "/?status=FINISHED&limit=25&offset=50");
    expect(
      screen.getByRole("link", { name: "Go to first page" }),
    ).toHaveAttribute("href", "/?status=FINISHED&limit=25");
  });
});
