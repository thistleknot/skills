---
name: react-fastapi-sqlite
description: >
  Scaffold and implement a full-stack web application using React (with TanStack
  Query for server-state), FastAPI (with SQLModel/SQLAlchemy for ORM), and SQLite
  as the database. Use this skill whenever the task involves: building a REST API
  backend with Python, wiring a React frontend to a FastAPI service, setting up
  SQLite persistence with an ORM layer, structuring the src/api/hooks/components/pages
  separation in React, or configuring TanStack Query (useQuery, useMutation,
  QueryClient, query invalidation). Trigger on any mention of FastAPI + React,
  full-stack Python web app, SPA with REST backend, TanStack Query with FastAPI,
  or React frontend for a Python API.
---

# React + FastAPI + SQLite + TanStack Query

## Architecture Overview

```
SQLite file
    → SQLModel ORM (table definitions)
    → FastAPI dependency injection (SessionDep)
    → Router handlers (CRUD per domain)
    → JSON over HTTP (CORS enabled)
    → axios (base URL, interceptors)
    → TanStack Query (queryOptions, useMutation, cache invalidation)
    → hooks (useItems, etc.)
    → pages / components (no fetch logic)
```

**Core constraint:** fetch logic never lives in components. The boundary is:

```
api/      — raw fetch functions + queryOptions (framework-agnostic)
hooks/    — useQuery / useMutation wrappers (React-specific)
pages/    — compose hooks; pass data down as props
components/ — pure UI; receive data + callbacks as props
```

---

## Stack

| Concern | Tool |
|---|---|
| Backend framework | FastAPI |
| ORM / schema | SQLModel (merges SQLAlchemy + Pydantic) |
| Database | SQLite (single file, zero config) |
| Schema validation | Pydantic (via SQLModel) |
| Frontend framework | React + TypeScript (Vite) |
| Server-state | TanStack Query v5 |
| HTTP client | axios |
| Dev server | uvicorn (backend) · vite dev (frontend) |

**Banned:** yfinance, Yahoo Finance.
**Not needed here:** Redux, Zustand, Context for server data — TanStack Query owns all of it.

---

## Project Layout

```
project/
├── backend/
│   ├── main.py           # app factory, CORS, router mounts, lifespan
│   ├── database.py       # engine, session factory, create_db_and_tables
│   ├── models.py         # SQLModel table definitions (source of truth)
│   ├── schemas.py        # request/response shapes (Create, Read, Update)
│   ├── crud.py           # DB operations — no HTTP logic here
│   ├── routers/
│   │   └── items.py      # one router file per domain
│   └── requirements.txt
│
└── frontend/
    ├── index.html
    ├── src/
    │   ├── main.tsx          # ReactDOM.createRoot, QueryClientProvider
    │   ├── App.tsx           # top-level routes / layout
    │   ├── lib/
    │   │   ├── queryClient.ts  # single QueryClient with shared defaults
    │   │   └── api.ts          # axios instance, base URL, interceptors
    │   ├── api/
    │   │   └── items.ts        # queryOptions + mutation fns (one file per domain)
    │   ├── hooks/
    │   │   └── useItems.ts     # useQuery/useMutation wrappers
    │   ├── components/         # pure UI components
    │   └── pages/              # page-level components
    ├── package.json
    └── vite.config.ts
```

---

## Decomposition

Implement in this order. Each stage has a validation gate. Do not proceed until current stage passes.

```
1. database         no deps
2. models           depends on 1
3. schemas          depends on 2
4. crud             depends on 2
5. routers          depends on 3, 4
6. main             depends on 5
7. queryClient      no deps (frontend)
8. api layer        depends on 7
9. hooks            depends on 8
10. pages/components depends on 9
```

---

## Stage 1 — Database Setup

```python
# backend/database.py
"""
Workflow:
  Creates SQLite engine and session factory.
  SessionDep is the FastAPI dependency injected into all route handlers.

Preconditions: SQLModel installed
Failure modes: check_same_thread must be False for SQLite; missing it causes
  threading errors under uvicorn with multiple requests.
"""
from sqlmodel import SQLModel, Session, create_engine
from typing import Annotated
from fastapi import Depends

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # set True to log SQL during dev
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
```

**Validation gate:** `python -c "from database import create_db_and_tables; create_db_and_tables()"` creates `app.db` with no errors.

---

## Stage 2 — Models

```python
# backend/models.py
"""
Workflow:
  SQLModel table classes are the single source of truth for DB schema.
  Do not define columns anywhere else.

Preconditions: database.py exists (engine must be importable for metadata)
Failure modes: table=True required for DB persistence; omitting it makes
  SQLModel treat the class as a pure Pydantic model (no table created).
"""
from sqlmodel import SQLModel, Field
from typing import Optional

class Item(SQLModel, table=True):
    """
    Require: name non-empty
    Guarantee: id auto-assigned on insert
    Maintain: description is always Optional — never a required field
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
```

**Validation gate:** after running `create_db_and_tables()`, `sqlite3 app.db ".schema"` shows the `item` table with correct columns.

---

## Stage 3 — Schemas

```python
# backend/schemas.py
"""
Workflow:
  Separate Pydantic models for Create, Read, Update shapes.
  Never expose the ORM model directly as a response type — use Read.

Preconditions: none (pure Pydantic, no DB dependency)
Failure modes: collapsing Create/Read into one model leaks id=None into
  create requests and forces nullable fields where they shouldn't be.
"""
from pydantic import BaseModel
from typing import Optional

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ItemRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}  # enables ORM mode

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
```

**Validation gate:** `ItemCreate(name="test")` succeeds; `ItemCreate()` raises `ValidationError`.

---

## Stage 4 — CRUD

```python
# backend/crud.py
"""
Workflow:
  Pure DB operations. No HTTP concerns, no request/response objects.
  All functions take a Session and return ORM instances or None.

Preconditions: models.py imported, session injected by caller
Failure modes: session.refresh() required after commit to access
  server-generated fields (e.g. id); skipping it returns stale state.
"""
from sqlmodel import Session, select
from models import Item
from schemas import ItemCreate, ItemUpdate
from typing import Optional

def create_item(session: Session, payload: ItemCreate) -> Item:
    item = Item(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

def get_item(session: Session, item_id: int) -> Optional[Item]:
    return session.get(Item, item_id)

def get_items(session: Session, offset: int = 0, limit: int = 100) -> list[Item]:
    return list(session.exec(select(Item).offset(offset).limit(limit)).all())

def update_item(session: Session, item_id: int, payload: ItemUpdate) -> Optional[Item]:
    item = session.get(Item, item_id)
    if not item:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

def delete_item(session: Session, item_id: int) -> bool:
    item = session.get(Item, item_id)
    if not item:
        return False
    session.delete(item)
    session.commit()
    return True
```

**Validation gate:** unit-test each function against a test Session before wiring routes.

---

## Stage 5 — Routers

```python
# backend/routers/items.py
"""
Workflow:
  HTTP layer only. Validates input via schemas, calls crud, returns schemas.
  No SQL here. No business logic beyond HTTP status codes.

Preconditions: crud.py, schemas.py, database.SessionDep
Failure modes: returning ORM model directly without response_model causes
  Pydantic to silently serialize wrong shapes in some versions.
"""
from fastapi import APIRouter, HTTPException
from database import SessionDep
from schemas import ItemCreate, ItemRead, ItemUpdate
import crud

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=ItemRead, status_code=201)
def create_item(payload: ItemCreate, session: SessionDep):
    return crud.create_item(session, payload)

@router.get("/", response_model=list[ItemRead])
def list_items(session: SessionDep, offset: int = 0, limit: int = 100):
    return crud.get_items(session, offset, limit)

@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, session: SessionDep):
    item = crud.get_item(session, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, payload: ItemUpdate, session: SessionDep):
    item = crud.update_item(session, item_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, session: SessionDep):
    if not crud.delete_item(session, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
```

---

## Stage 6 — Main App

```python
# backend/main.py
"""
Workflow:
  App factory. CORS, lifespan (DB init), router mounts.
  Nothing else lives here.

Preconditions: all routers importable
Failure modes: CORS misconfiguration is the #1 cause of frontend 
  fetch failures — allow_origins must include the Vite dev URL.
  allow_methods=["*"] and allow_headers=["*"] are safe for dev.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables
from routers import items

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Validation gate:** `uvicorn main:app --reload` starts; `curl localhost:8000/health` returns `{"status":"ok"}`; `localhost:8000/docs` shows all item routes.

---

## Stage 7 — QueryClient (Frontend)

```typescript
// frontend/src/lib/queryClient.ts
/**
 * Single QueryClient instance with project-wide defaults.
 *
 * Preconditions: @tanstack/react-query installed
 * Failure modes: creating QueryClient inside a component re-creates it
 *   on every render — always create at module level.
 *
 * staleTime: how long cached data is considered fresh (no background refetch)
 * gcTime: how long unused cache entries are kept in memory
 * refetchOnWindowFocus: off — prevents unexpected refetches during dev
 */
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,          // 1 min
      gcTime: 5 * 60_000,         // 5 min
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

```typescript
// frontend/src/lib/api.ts
/**
 * Axios instance with base URL and shared interceptors.
 *
 * Preconditions: axios installed, backend running on port 8000
 * Failure modes: hardcoded base URL must match CORS allow_origins in main.py.
 *   Use Vite env vars (import.meta.env.VITE_API_URL) for environment parity.
 */
import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Global error interceptor — extend as needed
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API error:", err.response?.data ?? err.message);
    return Promise.reject(err);
  }
);
```

```typescript
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./lib/queryClient";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

---

## Stage 8 — API Layer (Frontend)

```typescript
// frontend/src/api/items.ts
/**
 * Raw fetch functions and queryOptions for the /items domain.
 *
 * Preconditions: apiClient configured in lib/api.ts
 * Guarantee: queryOptions bundles queryKey + queryFn so both are colocated
 *   and cache entries are consistent across all consumers.
 * Failure modes: mismatched queryKey between useQuery and invalidateQueries
 *   causes mutations to not trigger refetches — always derive keys from
 *   the constants defined here.
 */
import { queryOptions } from "@tanstack/react-query";
import { apiClient } from "../lib/api";

export interface Item {
  id: number;
  name: string;
  description: string | null;
}

export interface ItemCreate {
  name: string;
  description?: string;
}

export interface ItemUpdate {
  name?: string;
  description?: string;
}

// Key constants — single source of truth for cache invalidation
export const itemKeys = {
  all: ["items"] as const,
  detail: (id: number) => ["items", id] as const,
};

// Query options objects — reusable across useQuery and prefetchQuery
export const itemsQueryOptions = queryOptions({
  queryKey: itemKeys.all,
  queryFn: async (): Promise<Item[]> => {
    const { data } = await apiClient.get("/items/");
    return data;
  },
});

export const itemQueryOptions = (id: number) =>
  queryOptions({
    queryKey: itemKeys.detail(id),
    queryFn: async (): Promise<Item> => {
      const { data } = await apiClient.get(`/items/${id}`);
      return data;
    },
  });

// Mutation functions — plain async, not hooks
export const createItem = async (payload: ItemCreate): Promise<Item> => {
  const { data } = await apiClient.post("/items/", payload);
  return data;
};

export const updateItem = async (id: number, payload: ItemUpdate): Promise<Item> => {
  const { data } = await apiClient.patch(`/items/${id}`, payload);
  return data;
};

export const deleteItem = async (id: number): Promise<void> => {
  await apiClient.delete(`/items/${id}`);
};
```

---

## Stage 9 — Hooks (Frontend)

```typescript
// frontend/src/hooks/useItems.ts
/**
 * React hooks that wrap TanStack Query for the /items domain.
 *
 * Preconditions: QueryClientProvider in tree, api/items.ts importable
 * Guarantee: mutations invalidate the relevant query keys on success,
 *   keeping cache consistent without manual refetch calls.
 * Failure modes: forgetting invalidateQueries after a mutation leaves the
 *   list stale until the next staleTime expiry.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  itemsQueryOptions,
  itemQueryOptions,
  itemKeys,
  createItem,
  updateItem,
  deleteItem,
  type ItemCreate,
  type ItemUpdate,
} from "../api/items";

export const useItems = () => useQuery(itemsQueryOptions);

export const useItem = (id: number) => useQuery(itemQueryOptions(id));

export const useCreateItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ItemCreate) => createItem(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemKeys.all });
    },
  });
};

export const useUpdateItem = (id: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ItemUpdate) => updateItem(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemKeys.all });
      queryClient.invalidateQueries({ queryKey: itemKeys.detail(id) });
    },
  });
};

export const useDeleteItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemKeys.all });
    },
  });
};
```

---

## Stage 10 — Pages and Components (Frontend)

Pages own data fetching via hooks. Components receive data as props.

```typescript
// frontend/src/pages/ItemsPage.tsx
/**
 * Page-level component. Composes hooks and passes data to pure components.
 * No fetch logic. No axios calls. No useEffect for data.
 */
import { useItems, useCreateItem, useDeleteItem } from "../hooks/useItems";
import { ItemList } from "../components/ItemList";
import { ItemForm } from "../components/ItemForm";

export const ItemsPage = () => {
  const { data: items, isPending, error } = useItems();
  const createItem = useCreateItem();
  const deleteItem = useDeleteItem();

  if (isPending) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <ItemForm
        onSubmit={(payload) => createItem.mutate(payload)}
        isSubmitting={createItem.isPending}
      />
      <ItemList
        items={items ?? []}
        onDelete={(id) => deleteItem.mutate(id)}
      />
    </div>
  );
};
```

```typescript
// frontend/src/components/ItemList.tsx
/**
 * Pure UI. No hooks, no fetch, no side effects.
 * Receives items and callbacks as props.
 */
import { type Item } from "../api/items";

interface Props {
  items: Item[];
  onDelete: (id: number) => void;
}

export const ItemList = ({ items, onDelete }: Props) => (
  <ul>
    {items.map((item) => (
      <li key={item.id}>
        <span>{item.name}</span>
        {item.description && <span> — {item.description}</span>}
        <button onClick={() => onDelete(item.id)}>Delete</button>
      </li>
    ))}
  </ul>
);
```

**Validation gate:** items load from backend, create adds to list without page refresh, delete removes from list without page refresh. Open Network tab — no duplicate requests.

---

## CORS Checklist

CORS is the most common failure point when wiring frontend to backend.

| Check | Expected |
|---|---|
| `allow_origins` in `main.py` | matches Vite dev URL (`http://localhost:5173`) |
| Vite proxy or `VITE_API_URL` | matches backend port (`8000`) |
| Preflight OPTIONS requests | return 200 (FastAPI CORSMiddleware handles this) |
| `Content-Type: application/json` | set in `api.ts` axios defaults |

If you get `Access-Control-Allow-Origin` errors: verify `allow_origins` is not `["*"]` when `allow_credentials=True` — that combination is rejected by browsers.

---

## Environment Config

```bash
# backend/.env (loaded by python-dotenv or pydantic-settings)
DATABASE_URL=sqlite:///./app.db
```

```
# frontend/.env.development
VITE_API_URL=http://localhost:8000
```

```
# frontend/.env.production
VITE_API_URL=https://api.yourdomain.com
```

---

## Dev Startup

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev   # starts on localhost:5173
```

---

## Frontend Decisions

These are independent of the backend wiring. Ask the user before scaffolding if
not specified. Each decision has a default — use the default when there's no
stated preference.

---

### Language: `.jsx` vs `.tsx`

| Extension | Language | Use for |
|---|---|---|
| `.tsx` | TypeScript + JSX | All React components (default) |
| `.ts` | TypeScript, no JSX | Utilities, config, pure logic |
| `.jsx` | JavaScript + JSX | Avoid — no type safety |
| `.js` | JavaScript | Avoid — no type safety |

**Default: TypeScript throughout.** Use `.tsx` for any file returning JSX,
`.ts` for everything else. Never mix `.jsx` into a `.tsx` project.

---

## Key Relationships & Integration Points

| Skill | Aspect | Why |
|---|---|---|
| `code` | Implementation standards, naming, refactor sequence | Ensures consistent patterns across backend (CRUD ops, router structure) and frontend (hooks, component composition) |
| `validation` | Integration tests, E2E verification, schema validation | Full-stack integration testing: FastAPI test client + React testing library with TanStack Query mocking |
| `tdd-agent` | Red→Green→Refactor for both backend and frontend | Routes use TDD (model → route → test); React components use TDD (component stub → integration test → implementation) |
| `headless-browser-verification` | Visual regression detection for React UI changes | Capture screenshots before/after React component changes to detect unintended visual diffs (especially mutations and cache invalidations) |
| `git-workflow` | Branch strategy, push gates, frontend screenshot proof | Frontend changes require headless-browser screenshots in commit; backend changes use standard code verification against last known working commit |
| `diagnostic-scanner` | Backend: mypy type checking; Frontend: TypeScript strict mode linting | Catch API contract violations (Pydantic mismatch) and React prop-drilling errors before runtime |
| `security-review` | CORS validation, ORM SQL injection prevention, API key injection points | Verify FastAPI CORS allow_origins is correct, SQLModel queries use parameterized statements (automatic via ORM), no secrets in frontend env |

**Workflow Integration Pattern:**
1. Start with `code` (naming/pattern) + `architecture` (if redesigning data flow)
2. Implement with `tdd-agent` (test-driven on both backend and frontend)
3. Validate with `validation` (unit + E2E) + `diagnostic-scanner` (type-check)
4. Verify with `headless-browser-verification` (frontend changes only)
5. Push via `git-workflow` (test branch → dev after user confirms visual + code checks)

---

### Bundler / Scaffold

| Tool | When |
|---|---|
| **Vite** (default) | SPA fronting a FastAPI backend — use this |
| Next.js | SSR, file-based routing, or React Server Components needed |
| Create React App | Deprecated — do not use |

Vite scaffold: `npm create vite@latest -- --template react-ts`

Next.js competes with FastAPI for the server role. Don't combine them without
a clear reason — you'll have two backend surfaces to maintain.

---

### Styling

Four approaches. Pick one before writing a single component; mixing them creates
maintenance debt.

**Option A — Plain CSS / CSS Modules** (zero config, no framework)
```
src/components/ItemList.module.css   ← scoped per component
```
```tsx
import styles from "./ItemList.module.css";
<ul className={styles.list}>
```
Use when: you want no tooling overhead, small project, team knows CSS.

---

**Option B — Tailwind CSS** (utility-first, most common in 2025 greenfield)

Install:
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

`tailwind.config.js`:
```js
content: ["./index.html", "./src/**/*.{ts,tsx}"]
```

`src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Usage: classes inline on elements — `className="flex gap-2 p-4 rounded"`.
No separate CSS files for most components.

---

**Option C — shadcn/ui + Tailwind** (default for production UIs in 2025)

shadcn/ui is not a package — it's a CLI that copies component source into your
repo. You own the code. Built on Radix UI (accessible primitives) + Tailwind.

Requires Tailwind installed first, then:
```bash
npx shadcn@latest init
npx shadcn@latest add button input card table
```

Components land in `src/components/ui/`. Import and use:
```tsx
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
```

`tsconfig.json` path alias required (`@/*` → `./src/*`); shadcn init handles
this automatically.

Use when: you want accessible, production-grade components without a heavyweight
design system. Current dominant choice for new React projects.

---

**Option D — Component library (MUI / Chakra)**

Pre-styled components with their own design language. Lower control, faster
initial setup for standard CRUD UIs.

```bash
npm install @mui/material @emotion/react @emotion/styled  # MUI
# or
npm install @chakra-ui/react                              # Chakra v3
```

Use when: you need enterprise-grade component density fast and don't need to
control the visual design.

---

### Routing

Only needed if the app has more than one page/view.

| Tool | When |
|---|---|
| **React Router v6** (default) | Most cases — stable, well-documented |
| TanStack Router | Type-safe routes, pairs naturally with TanStack Query |
| None | Single-page CRUD with no URL routing |

React Router install: `npm install react-router-dom`

---

### State Beyond Server Data

TanStack Query owns all server state. For client/UI state:

| Scope | Tool |
|---|---|
| Component-local (modal open, form value) | `useState` / `useReducer` |
| Cross-component UI state | Zustand (`npm install zustand`) |
| Form state with validation | React Hook Form (`npm install react-hook-form`) |

Do not reach for Zustand or Context to cache API data — that's TanStack Query's job.

---

### Decision Checklist (ask before scaffolding)

```
[ ] TypeScript? (default: yes)
[ ] Styling approach? Plain CSS / Tailwind / shadcn+Tailwind / MUI / Chakra
[ ] Routing needed? If yes: React Router or TanStack Router
[ ] Form handling? useState / React Hook Form
[ ] Dark mode / theming? (shadcn supports this out of the box)
```

---

## Known Failure Modes

| Failure | Signal | Fix |
|---|---|---|
| `check_same_thread` error | SQLite threading error on concurrent requests | Add `connect_args={"check_same_thread": False}` to engine |
| Stale list after mutation | UI doesn't update after create/delete | Call `queryClient.invalidateQueries({ queryKey: itemKeys.all })` in `onSuccess` |
| CORS preflight rejected | Network tab shows OPTIONS returning 403/404 | Verify `allow_origins` matches frontend URL exactly, including port |
| ORM model returned without refresh | `id` is `None` after insert | Call `session.refresh(item)` after `session.commit()` |
| `queryKey` mismatch | Mutations don't trigger refetch | Derive all keys from `itemKeys` constants, never inline strings |
| `id` in `ItemCreate` | Pydantic accepts `id=None` on creates | Keep `ItemCreate` separate from `ItemRead`; never share one model for both |
| React Strict Mode double-mount | Queries fire twice in dev | Normal behavior, does not occur in production; TanStack Query deduplicates |
| axios base URL wrong in production | Requests go to localhost in prod build | Use `VITE_API_URL` env var, never hardcode |

---

## Files to Produce

```
backend/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── crud.py
├── routers/
│   └── items.py      # one per domain
└── requirements.txt  # fastapi, sqlmodel, uvicorn, python-dotenv

frontend/src/
├── main.tsx
├── App.tsx
├── lib/
│   ├── queryClient.ts
│   └── api.ts
├── api/
│   └── items.ts      # one per domain
├── hooks/
│   └── useItems.ts   # one per domain
├── components/
│   ├── ItemList.tsx
│   └── ItemForm.tsx
└── pages/
    └── ItemsPage.tsx
```

Add one `api/`, `hooks/` file per additional domain. Never merge domains into one file.
Implement stages in topological order. Each file is complete — no partial implementations.
Run the validation gate for each stage before moving to the next.
<!-- consolidation:see-also:start -->
## See Also
[[git-workflow]]  [[request-intent-resolution]]  [[agentic-harness]]  [[openspec-workflow]]  [[validation-artifacts]]
<!-- consolidation:see-also:end -->
