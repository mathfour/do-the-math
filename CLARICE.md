# Clarice — Review Log

Reviewer notes for **Do the Math**. Claude implements; I review at each phase boundary.
I only ever edit this file. Measured against the frozen [SPEC.md](SPEC.md); deviations are
tracked against [notes.md](notes.md).

Verdict legend: ✅ approved to proceed · 🟡 approved with follow-ups · 🔴 changes required.

---

## Phase 1 — Shared math core & output contract

**Verdict: ✅ approved to proceed to Phase 2.** (reviewed 2026-06-05, commit `1b430ed`)

This is the foundation phase and it's been built with real care. The central design law
(English → IR → SymPy → output, LLM never the source of math truth) is honored everywhere, the
exact-arithmetic invariant is enforced at the one choke point (`_num`), and scope rejection is
deterministic with defense-in-depth guards. Genuinely above the bar.

### What I verified (re-run locally, not taken on faith)
- `ruff` clean · `black --check` clean · **60 tests pass · 92.9% coverage**, gate enforced
  (`--cov-fail-under=80` in `addopts`). My Phase 0 follow-up #2 (wire the coverage gate) — **done**.
- Exact-arithmetic spot checks all hold: `1/3` slope → `y = x/3`; `0.5` → `Rational(1,2)`;
  parabola vertex (1,2) up → exactly `y = (x - 1)**2 + 2`.
- Honest declines work: vertical line / collinear three-points → `not_a_function`; implicit →
  `unsupported`; zero-leading-coeff quadratic → `DerivationError`. No path returns a wrong graph.
- `/chat` end-to-end with the adapter mocked: graph / clarification / missing-key / 422-empty all
  return the right envelope. Anthropic adapter tested with the network mocked (no live billing).

### Against the SPEC Phase 1 checklist — all present
- [x] IR schema for v1 objects + required-fields-per-object (`ir.py` discriminated union;
      `clarification.REQUIRED`).
- [x] `math_interpreter` (English→IR) behind the Anthropic adapter via forced tool-use.
- [x] `math_engine` (IR→validated) on SymPy, exact, source of truth.
- [x] `graph_renderer` (validated→JSON-safe Plotly dict; asymptote gaps; domain clipping).
- [x] Output envelope incl. `clarification` and `error`.
- [x] Router/classifier scaffold + `Agent` registration; `GraphingAgent` is the one registered agent.
- [x] `POST /chat` (+ `/health`) returning the envelope; never crashes on bad input.

### Things I went looking for and was glad to find
- The classic falsy-zero clarification bug is **avoided** — `_is_missing` doesn't treat numeric `0`
  as absent, so `slope: 0` / `intercept: 0` aren't mistaken for missing fields.
- Clarification runs on the **raw dict before** strict Pydantic construction — correct ordering, so
  a missing field asks a question instead of throwing.
- Float→Rational normalization keeps equations readable; the steep-polynomial test proves the
  asymptote heuristic doesn't eat genuinely-large smooth curves.
- Both documented SPEC deviations (nested `graph` payload `{figure, equation, ir}`;
  `can_handle → True` for the single v1 agent) are sensible and logged in `notes.md`.

### Follow-ups (none block Phase 2)

1. **🟡 Coverage gate in `addopts` blocks partial local runs.** `--cov-fail-under=80` lives in
   pytest `addopts`, so it's enforced on *every* invocation — including `pytest tests/test_ir.py`,
   which then "fails under 80%" simply because one file doesn't exercise the whole app. That's a
   TDD/ergonomics papercut. Suggest keeping `--cov` in `addopts` but moving **`--cov-fail-under`** to
   the CI command (or a CI-only addopts), so a focused local run isn't reported as a failure. Pure
   DX — coverage enforcement itself is correct.

2. **Sanitize the interpreter-error message.** `router.handle` puts the raw `{exc}` into the
   user-facing envelope (`"Couldn't reach the language model… {exc}"`). Fine for a mocked demo, but
   once a live key is in play a transport/SDK exception string can be noisy or leak internal detail.
   Recommend a friendly fixed message to the client and the detail to server logs.

3. **Add one backend test for the clarification *round-trip*.** The pieces are each tested (history
   is prepended in the adapter; a missing field asks; a complete IR graphs) but nothing asserts the
   SPEC §4 loop end-to-end: underspecified → question → answer-with-history → completed graph. Cheap
   to add at the `/chat` level and it locks the behavior the demo depends on. (Could alternatively be
   the Playwright clarification spec in Phase 3 — fine either way, just don't let it fall through.)

4. **Nit — repeated/degenerate three-points message.** `parabola_three_points` with two identical
   points falls through to the generic "unexpected variables" `DerivationError` rather than a clean
   "give three distinct points" message. Safe (no wrong graph), just technical-sounding. Low priority.

### Carried-forward items still open (not Phase 1's job — tracking so they don't slip)
- SPEC §8/§10 PR-merge boxes remain **WAIVED** by human decision (direct-to-`main`); mark them
  waived, not checked, at final acceptance.
- `App.tsx` + both smoke tests are still stock Vite scaffold — slated for replacement in Phase 2/3.

---

## Phase 0 — Repo & tooling

**Verdict: ✅ approved to proceed to Phase 1.** (reviewed 2026-06-05, commit `99f044e`)

### What I verified (not just claimed — re-run locally)
- **Backend:** `uv run ruff check .` → clean · `black --check .` → clean · `pytest` → 2 passed.
- **Frontend:** `eslint .` → clean · `prettier --check .` → clean · `tsc -b --noEmit` → clean ·
  `vitest run` → 1 passed · `playwright test` → 1 passed (real chromium against dev server).
- **Repo hygiene:** caches (`.pytest_cache`, `.ruff_cache`, `test-results/`) are on disk but
  correctly **untracked**; `.gitignore` covers secrets/`.env`/keys; `.vscode/` is ignored and not
  committed; `.env.example` carries placeholders only, no real key. Clean.

### Against the SPEC Phase 0 checklist
- [x] Repo initialized (remote `mathfour/do-the-math`, pushed to `main`).
- [x] `/backend` (Python 3.12 via uv) + `/frontend` (Vite + React + TS) skeletons.
- [x] ruff + black (backend), ESLint + Prettier (frontend).
- [x] pytest, Vitest + RTL, Playwright harnesses — all wired and green.
- [x] CI runs lint + all suites on push **and** pull_request.

Phase 0 is genuinely complete. Solid foundation. The decisions in `notes.md` (Math Intent law,
exact-arithmetic gotcha, deterministic clarification table, `unsupported` as a first-class IR kind,
tool-use for structured IR) are the right calls and bode well for Phase 1.

### Follow-ups (none block Phase 1)

1. **🟡 PR/merge-gate deviation — needs an explicit human decision.** SPEC §8 and §10 require
   feature branches merged via **reviewed pull requests** and "CI … blocks merge on failure."
   `notes.md` deliberately chose commit-straight-to-`main`, no PRs, with my phase-boundary review
   standing in for the PR gate. That's a reasonable workflow, but two acceptance-checklist items
   ("work merges via reviewed pull requests"; "CI … blocks merge on failure") then can't be met as
   written — with direct-to-`main` there is no merge to block; CI is post-hoc. **Not a Phase 0
   defect** — just flagging so it isn't a surprise at final acceptance. Decision needed: accept the
   deviation as the project's rule (and I'll note the two boxes as intentionally waived), or add
   branch protection + PRs later.

2. **Coverage gate not wired into CI.** `pytest-cov` and `[tool.coverage.run]` exist, but CI runs
   plain `pytest` with no `--cov` and no threshold. Correct for Phase 0 (no logic yet) — but SPEC §7
   targets ~80% backend coverage, so wire the gate when Phase 1 lands real logic, or it'll quietly
   slip.

3. **Dev/CI Node divergence.** `notes.md` records the dev box on Node 25; CI pins Node 22. 22-LTS in
   CI is fine, but a two-major gap can mask issues either direction. Intentional is fine — worth one
   line in `notes.md` on why 22, so it reads as a choice, not drift.

4. **Nit — scaffold leftovers.** `App.tsx` is still the stock Vite "Get started" template (react/vite
   logos, `hero.png`), and both smoke tests assert on that scaffold text. Expected at Phase 0 and the
   tests are explicitly labeled as throwaways for Phase 2/3 — just confirming they're on the list to
   be replaced, not carried forward.

### Spot-check on a thing I expected to bite — and didn't
- Model id `claude-sonnet-4-6` in `.env.example` / `notes.md` is the correct current Sonnet 4.6 id.
  `notes.md` flagged it "to confirm at implementation time" — confirmed correct. Keep it in config
  (it already is) so it stays swappable.
