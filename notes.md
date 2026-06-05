# Dev Log / Decision Record

Living working notes for building **Do the Math**. Polished, visitor-facing material lives in [README.md](README.md); the frozen v1 build spec is [SPEC.md](SPEC.md). This file is the *why* behind the build — decisions, deviations, per-phase status, and review feedback.

## Roles & workflow

- **Claude** implements; **Clarice** reviews.
- Git: single `main` branch, **commit and push straight to `main`** (no dev branch, no PRs).
- Because there's no PR gate, work **pauses at each phase boundary for Clarice's review**. Her feedback and how it was resolved is logged here.
- Effort model: **proper phase-by-phase** — each phase reaches its full tested state before the next begins.

## Documentation model

Three docs (decided 2026-06-05):
- **README.md** — living public front door; updated incrementally each phase.
- **SPEC.md** — the original README, frozen verbatim as the immutable v1 build spec + acceptance checklist. We measure against it; we don't edit it.
- **notes.md** (this file) — living dev log: decisions + rationale, deviations from SPEC, phase status, Clarice's review notes, open questions.

## Environment

- System Python is **3.9.6** (too old) → backend pins **Python 3.12 via `uv`**.
- Node **25** / npm **11** — fine for Vite.
- No `gh` CLI — not needed; we push to `main` directly. Remote: `mathfour/do-the-math`.

## Key technical decisions

- **Stack:** FastAPI (Python 3.12, uv) backend; Vite + React + **TypeScript** frontend; Plotly.js for graphs. Lint/format: ruff + black (backend), ESLint + Prettier (frontend). Tests: pytest, Vitest + RTL, Playwright.
- **Central design law:** English → **Math Intent (IR)** → SymPy-validated math → output. The LLM only produces the IR; **SymPy is the source of mathematical truth.** Never English → equation directly.
- **Anthropic model:** default `claude-sonnet-4-6` for IR extraction (strong structured extraction, cost-effective for repeated demo runs); model id lives in config so it's swappable. _To confirm exact model id + tool-use SDK usage via the `claude-api` reference at implementation time._
- **Structured IR output:** Anthropic adapter uses **tool-use** — one tool whose `input_schema` is the IR union's JSON schema — forcing a valid-shaped IR. No free-text JSON parsing.
- **Exact arithmetic everywhere:** IR numeric fields are `Union[int, float, str]`, normalized to exact SymPy numbers (`Integer`/`Rational`/`sympify`). This keeps equations readable (`y = (x - 1)**2 + 2`, not float-littered) and correct. _The single most important math-core gotcha._
- **`unsupported` is a first-class IR kind** — scope rejection is deterministic, not a force-fit. Backed by engine-level guards (reject leftover symbols, relationals, Piecewise) as defense in depth.
- **Clarification is deterministic** — driven by a required-field table per IR kind, checked *before* strict Pydantic construction. Returns the first missing field as one targeted question. No LLM confidence floats.
- **API key flow:** UI → browser `localStorage` → `X-Anthropic-Key` header → backend → Anthropic. Backend `.env` (`ANTHROPIC_API_KEY`) is a dev/live fallback. Key is never committed and never sent anywhere except Anthropic.

## Phase status

- **Phase 0 — Repo & tooling:** _complete (pending Clarice review)._
  - Docs split: `SPEC.md` frozen, `notes.md` started, `README.md` trimmed to public form.
  - Repo hygiene: `.gitignore`, `.env.example`.
  - Backend: `uv` project (Python 3.12), `pyproject.toml` (fastapi/uvicorn/pydantic/sympy/numpy/anthropic + dev: pytest/ruff/black), package skeleton, smoke tests. `uv run pytest` / `ruff` / `black --check` all green.
  - Frontend: Vite + React + TS scaffold; Vitest 4 + RTL, Prettier, Playwright wired. `lint` / `typecheck` / `format:check` / `vitest` / `playwright` all green. (Bumped Vitest 2→4 to align with Vite 8 and clear audit criticals.)
  - CI: `.github/workflows/ci.yml` runs backend (ruff/black/pytest) + frontend (eslint/prettier/typecheck/vitest/playwright) on push + PR.
  - This is the repo's **initial commit** (no prior commits existed).

## Open questions

- _(none yet)_

## Clarice review log

- _(awaiting first phase-boundary review)_
