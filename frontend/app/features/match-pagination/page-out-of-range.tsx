import { Link, useSearchParams } from "react-router";

import { lastPageOffset, pageSearchParams } from "../../shared/filters";

interface PageOutOfRangeProps {
  limit: number;
  total: number;
}

export function PageOutOfRange({ limit, total }: PageOutOfRangeProps) {
  const [searchParams] = useSearchParams();
  const firstPage = pageSearchParams(searchParams, 0).toString();
  const lastPage = pageSearchParams(
    searchParams,
    lastPageOffset(total, limit),
  ).toString();

  return (
    <div className="state-card">
      <span className="state-icon" aria-hidden="true">
        0
      </span>
      <p className="eyebrow">Page unavailable</p>
      <h3>This page has no matches</h3>
      <p>
        {total} {total === 1 ? "match fits" : "matches fit"} your filters, but
        not on this page. The data may have changed since the link was created.
      </p>
      <Link className="button button-primary" to={`?${lastPage}`}>
        Go to last page
      </Link>
      <Link className="button button-secondary" to={`?${firstPage}`}>
        Go to first page
      </Link>
    </div>
  );
}
