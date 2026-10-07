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
    <html lang="uk">
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
      <p>Готуємо матч-центр…</p>
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

        <nav className="primary-nav" aria-label="Основна навігація">
          <NavLink to="/football/champions-league/matches">
            Ліга чемпіонів
          </NavLink>
          <span aria-disabled="true" title="Незабаром">
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
        <p>Sport Events · Розклад і результати без зайвого шуму.</p>
        <p>Час матчу показано у вашому часовому поясі.</p>
      </footer>
    </div>
  );
}

export function ErrorBoundary() {
  return (
    <main className="fatal-error">
      <p className="eyebrow">Помилка застосунку</p>
      <h1>Цю сторінку не вдалося відкрити.</h1>
      <p>Оновіть сторінку або поверніться до матч-центру.</p>
      <a
        className="button button-primary"
        href="/football/champions-league/matches"
      >
        До матчів
      </a>
    </main>
  );
}
