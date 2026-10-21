import { Link, useSearchParams } from "react-router";

import { pageSearchParams } from "../../shared/filters";

interface PaginationProps {
  limit: number;
  offset: number;
  total: number;
}

export function MatchPagination({ limit, offset, total }: PaginationProps) {
  const [searchParams] = useSearchParams();
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const previousOffset = Math.max(0, offset - limit);
  const nextOffset = offset + limit;

  return (
    <nav className="pagination" aria-label="Match pagination">
      <p>
        <strong>
          {from}–{to}
        </strong>{" "}
        of {total}
      </p>
      <div>
        {offset > 0 ? (
          <Link
            className="page-button"
            to={`?${pageSearchParams(searchParams, previousOffset).toString()}`}
            aria-label="Previous page"
          >
            ←
          </Link>
        ) : (
          <span className="page-button disabled" aria-hidden="true">
            ←
          </span>
        )}
        {nextOffset < total ? (
          <Link
            className="page-button"
            to={`?${pageSearchParams(searchParams, nextOffset).toString()}`}
            aria-label="Next page"
          >
            →
          </Link>
        ) : (
          <span className="page-button disabled" aria-hidden="true">
            →
          </span>
        )}
      </div>
    </nav>
  );
}
