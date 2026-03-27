# Lingo Frontend

React + TypeScript + Vite SPA. Compiled output goes to `../src/lingo/static/` and is served by the FastAPI backend.

## Development

```bash
npm install
npm run dev       # dev server at http://localhost:5173 (proxies API to :8000)
npm run build     # build to ../src/lingo/static/
npm test          # Vitest + React Testing Library
```

The dev server proxies `/api` and `/mcp` to `http://localhost:8000`. Start the backend first (see the root [README](../README.md)).

## Components

- `SearchBar` — live search with `/` and `Cmd+K` keyboard shortcuts
- `StatusFilter` — filter pills (All / Official / Community / Pending / Suggested) with live counts
- `TermRow` — table rows, sorted Official first
- `TermDetail` — slide-in panel with vote / dispute actions
- `AddTermModal` — add term form with client-side validation
- `DevModeBanner` — reads `<meta name="lingo-dev-mode">` injected by FastAPI

State management: TanStack Query (`useTerms`, `useTermDetail`, `useAddTerm`, `useVoteTerm`, `useDisputeTerm` in `src/hooks/useTerms.ts`).

API client: Axios in `src/api/terms.ts`.
