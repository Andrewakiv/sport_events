import {
  Links,
  Meta,
  NavLink,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import "./styles/global.css";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#07130f" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export function HydrateFallback() {
  return (
    <main className="loading-shell" aria-busy="true">
      <div className="brand-mark" aria-hidden="true">
        SE
      </div>
      <p>Loading match centre…</p>
    </main>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/football/champions-league/matches">
          <span className="brand-mark" aria-hidden="true">
            SE
          </span>
          <span>
            <strong>Sport Events</strong>
            <small>Match intelligence</small>
          </span>
        </NavLink>

        <nav className="primary-nav" aria-label="Main navigation">
          <NavLink to="/football/champions-league/matches">
            Champions League
          </NavLink>
          <span aria-disabled="true" title="Coming soon">
            Formula 1 <em>soon</em>
          </span>
        </nav>

        <div className="data-mode">
          <span aria-hidden="true" />
          Read-only API
        </div>
      </header>

      <Outlet />

      <footer className="site-footer">
        <p>Sport Events · Fixtures and results, without the noise.</p>
        <p>Kick-off times are shown in your local time zone.</p>
      </footer>
    </div>
  );
}

export function ErrorBoundary() {
  return (
    <main className="fatal-error">
      <p className="eyebrow">Application error</p>
      <h1>This page could not be loaded.</h1>
      <p>Refresh the page or return to the match centre.</p>
      <a
        className="button button-primary"
        href="/football/champions-league/matches"
      >
        Back to matches
      </a>
    </main>
  );
}
