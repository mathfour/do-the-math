# Clarice — Review Log

Reviewer notes for **Do the Math**. Claude implements; I review at each phase boundary.
I only ever edit this file. Measured against the frozen [SPEC.md](SPEC.md); deviations are
tracked against [notes.md](notes.md).

Verdict legend: ✅ approved to proceed · 🟡 approved with follow-ups · 🔴 changes required.

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
