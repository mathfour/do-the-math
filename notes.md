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
- **CI pins Node 22** (dev is on Node 25) — 22 is the current LTS line and the stable target for CI reproducibility; Vite 8 supports it (needs ≥20.19 / ≥22.12). Dev-vs-CI gap is intentional, not drift.

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

- **Phase 1 — Shared math core & output contract:** _complete (pending live check + Clarice review)._
  - `ir.py` (discriminated-union IR + Envelope), `math_engine.py` (SymPy derive), `graph_renderer.py` (Plotly dict), `clarification.py`, provider seam (`base`/`fake`/`anthropic_adapter` via tool-use), `math_interpreter`, agent registry + `GraphingAgent`, `router`, `config`, FastAPI `POST /chat` + `/health`.
  - **60 backend tests, 93% coverage** (gate set to fail under 80%). Anthropic adapter tested with the network mocked.
  - Live check script at `backend/scripts/live_check.py` — runs the real Anthropic slice. **Deferred (human decision 2026-06-05): we'll do the first real-API test once the UI exists (Phase 2/3), so it can be watched end to end rather than read from a terminal.** Backend is fully exercised by mocked unit tests (93%) until then.
  - Reconciliations / deviations from SPEC (intentional):
    - **Graph payload shape:** SPEC §3 says `graph` payload "is a Plotly figure spec." We nest it as `{"figure": <plotly>, "equation": str, "ir": dict}` so the reasoning panel (SPEC §9 — surface IR + derived equation) has its data. Frontend reads `payload.figure`.
    - **`GraphingAgent.can_handle` returns `True`** in v1 (one agent claims every request, turning unknown/missing kinds into clarifications). Real kind-based classification arrives with the second agent — SPEC §3/§6 call the v1 classifier "simple" and defer hardening to Phase 5. A `handles_kind()` helper already encodes the kind set for that future split.
    - **Coverage gate** lives in `pyproject` `addopts` (`--cov-fail-under=80`), so it's enforced identically by local `uv run pytest` and CI — rather than a separate CI step (addresses Clarice follow-up #2).
- **Phase 0 — Repo & tooling:** _complete (Clarice-approved)._
  - Docs split: `SPEC.md` frozen, `notes.md` started, `README.md` trimmed to public form.
  - Repo hygiene: `.gitignore`, `.env.example`.
  - Backend: `uv` project (Python 3.12), `pyproject.toml` (fastapi/uvicorn/pydantic/sympy/numpy/anthropic + dev: pytest/ruff/black), package skeleton, smoke tests. `uv run pytest` / `ruff` / `black --check` all green.
  - Frontend: Vite + React + TS scaffold; Vitest 4 + RTL, Prettier, Playwright wired. `lint` / `typecheck` / `format:check` / `vitest` / `playwright` all green. (Bumped Vitest 2→4 to align with Vite 8 and clear audit criticals.)
  - CI: `.github/workflows/ci.yml` runs backend (ruff/black/pytest) + frontend (eslint/prettier/typecheck/vitest/playwright) on push + PR.
  - This is the repo's **initial commit** (no prior commits existed).

## Open questions

- ~~SPEC §8/§10 vs. direct-to-main~~ — **RESOLVED 2026-06-05: WAIVED by human decision.** We keep commit-straight-to-`main`. At final acceptance, the SPEC §8 "merged via pull request" and §10 "blocks merge on failure" boxes are explicitly marked **WAIVED** (rationale: chosen direct-to-main workflow; no PR/merge gate exists), **not** checked. CI still runs on every push to `main` as a post-hoc guard. Flagged by Clarice (Phase 0 review).

## To carry into later phases

- **Live API check (Phase 2/3):** run `backend/scripts/live_check.py` (or the equivalent through the UI) with a real Anthropic key once the chat UI exists — the first real end-to-end test, watched in the browser. Deferred from Phase 1 by human decision.
- **Coverage gate:** _done in Phase 1_ — `--cov-fail-under=80` lives in `pyproject` `addopts`, enforced by local `pytest` and CI alike (currently 93%).
- **Scaffold placeholders:** `frontend/src/App.tsx` and both smoke tests (`App.test.tsx`, `e2e/smoke.spec.ts`) are stock Vite boilerplate, intentionally. They get **replaced in Phase 2 (UI) / Phase 3 (real E2E)** — not carried forward.

## Clarice review log

- **Phase 1 — APPROVED** (proceed to Phase 2). Four non-blocking follow-ups, all addressed before Phase 2:
  1. **Coverage-gate ergonomics** → moved `--cov-fail-under=80` out of `pyproject` `addopts` (which made focused runs like `pytest tests/test_ir.py` "fail" for under-covering the app) into the CI pytest command. `--cov` stays in addopts; enforcement stays in CI.
  2. **Sanitized interpreter-error envelope** → `router.handle` now logs the exception server-side (`logger.exception`) and returns a fixed, friendly message instead of interpolating the raw exception (no SDK/transport leakage on a live key).
  3. **Clarification round-trip test** → added `test_clarification_round_trip_completes_the_graph` at the `/chat` level (underspecified → question → answer-with-history → graph), asserting history reaches the interpreter. Locks the SPEC §4 loop the demo leans on.
  4. **Duplicate three-points message** → `_parabola_three_points` now returns a clean "give three distinct points" (duplicates) / "two points share an x-value" (same-x) message instead of the generic "unexpected variables" guard. Tests added.
  - Carried forward (acknowledged): SPEC §8/§10 PR boxes stay **waived** (not checked) at acceptance; stock Vite `App.tsx` + smoke tests get replaced in Phase 2/3.
- **Phase 0 — APPROVED** (proceed to Phase 1). Everything green, repo clean. Four non-blocking follow-ups:
  1. SPEC §8/§10 PR-merge boxes can't be literally met under direct-to-main → recorded as an open question above; needs a human waiver call (don't silently check those boxes at acceptance).
  2. Wire the coverage gate when Phase 1 lands logic → recorded in "To carry into later phases."
  3. Document why CI pins Node 22 → done (see Environment).
  4. Confirm stock scaffold is slated for replacement → confirmed (see "To carry into later phases").
  - Also resolved: `claude-sonnet-4-6` confirmed as the correct current Sonnet 4.6 id; stays in config.
