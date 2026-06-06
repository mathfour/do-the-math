# Clarice — Review Log

Reviewer notes for **Do the Math**. Claude implements; I review at each phase boundary.
I only ever edit this file. Measured against the frozen [SPEC.md](SPEC.md); deviations are
tracked against [NOTES.md](NOTES.md).

Verdict legend: ✅ approved to proceed · 🟡 approved with follow-ups · 🔴 changes required.

---

## Phase 5 — post-v1 hardening (property tests, robustness, feedback)

**Verdict: ✅ approved.** Strong hardening pass — the property tests earn their keep (two real bugs
caught), the robustness contract is the right one, and the feedback feature is self-contained.
(reviewed 2026-06-06, range `1b7072a..5e54747`)

### What I verified (re-run at HEAD)
- **Backend 113 tests / 93% coverage**, ruff + black clean. **Frontend 21 unit + 4 E2E**,
  tsc/eslint/prettier clean. `hypothesis>=6.100` declared as a dev dep; in `uv.lock`.
- **Both bug fixes are correct:**
  - `_guard` bare-symbol fix — re-probed the boundary: accepts `x`, `2x+1`, `sin(x)`, constants;
    still rejects `x>0`, `Eq`, `And/Or/Not`, `True`. Pinned by guard + engine + full-slice
    (`y = x` through `/chat`) tests — incl. the end-to-end regression I asked for last round.
  - Unhashable-kind crash — `check_required` now does `isinstance(kind, str)` *before* the `in`
    lookup, so `{"kind": ["x"]}` degrades to the "what kind?" clarification instead of a 500.
    API-level parametrized tests confirm malformed IR → 200.

### The property suite (the heart of this phase)
Well-targeted invariants, each guarding the trust boundary for *any* input, not just examples:
displayed-equation round-trips to the exact expression · exact arithmetic (no stray `Float`) ·
degree-n polynomial has 0…n−1 turning points · rendered figures always JSON-safe (finite-or-None,
exercising tan asymptote masking + log domain clamping) · degenerate inputs always raise · and the
robustness property — **any** raw IR yields a valid envelope, never an exception. This is exactly
the right use of property testing for a "the math is always correct" system.

### On Claude's three "worth a look" items
1. **`_guard` narrowing** — correct and now pinned by properties; no scope hole. ✓
2. **Robustness contract ("valid envelope for any IR")** — yes, this is the right invariant for v1:
   the agent must never throw on malformed model output, only degrade to clarification/error/help.
   Both layers are covered (agent-level property + `/chat` API tests). Endorsed.
3. **Feedback as a `showFeedback` branch in `App.tsx`, not a router** — fine for three top-level
   views (key / chat / feedback). Introduce a router only when a 4th view or deep-linking (shareable
   URLs) appears. Not worth the dependency now. Feedback itself is clean: no backend, no third party
   beyond GitHub + the author's own email, clipboard with a graceful fallback, no data collected.

### On the deferred item (#4 accessibility) — my input, since asked
Worth doing, and a good next hardening target for a tool aimed at students/teachers. Concrete scope
I'd suggest, in rough priority:
- **An `aria-live="polite"` region around the messages list** so a new graph/clarification/error is
  announced to screen readers (right now results render silently).
- **Make the graph's `aria-label` the equation**, not the generic "graph" — e.g. "Graph of
  y = (x − 1)² + 2" — so the one piece of non-text content carries its meaning.
- **Focus management** for the feedback/info overlays: move focus into the view on open and return
  it to the trigger on close. (The info popover already handles Escape + outside-click — good start.)
- Keyboard-only pass over the composer, toggle, and folds (the `<details>` panels are natively fine).

None of these block anything; they're the right content for an a11y phase.

### Follow-ups
- 🟢 Nothing blocking. The only carry-over from v1 still worth confirming is the **README install
  folds rendering on GitHub** (v1 #1) — separate from this bundle, still worth eyeballing on the
  rendered page if not already done.

---

## Interim — `_guard` bare-symbol fix (math-truth boundary)

**Spot-checked 2026-06-06 — confirmed sound.** Not a phase boundary; Claude flagged it as an FYI
during v1 hardening and will fold it into the Phase 5 review. Logging because it touches the
most important invariant.

Hypothesis property tests (equation round-trip) caught a real one: `_guard` rejected `y = x`
because a bare SymPy `Symbol` is itself a `Boolean` instance, so `isinstance(expr, Boolean)`
false-positived. Narrowed to `is_Relational | BooleanFunction | BooleanAtom`. I re-ran the boundary
both ways: **accepts** `x`, `2x+1`, `sin(x)`, constants; **still rejects** `x>0`, `Eq(x,1)`,
`And/Or/Not`, `True`. Regression test added; suite green (~93%). Good catch — exactly the subclass
gotcha property tests are for, and the narrowing is precise (no scope hole opened).

---

## Phase 4 / v1 sign-off — local run, help intent, user-controlled summaries

**Verdict: ✅ v1 signed off / shippable.** One thing to eyeball on GitHub (README folds, #1
below); everything else is green and the architecture invariants hold. (reviewed 2026-06-05, range
`614f543..3d5a7c9`)

### What I verified (re-run at HEAD)
- **Backend 85 tests / 92% coverage** (gate 80%); ruff + black clean. **Frontend 17 unit + 4 E2E
  pass**; tsc/eslint/prettier clean. Working tree clean.
- **The Phase 3 #1 fix is correct.** `_num_turning_points` now counts sign changes of f′. Probed
  directly: `x³→0`, `x⁵→0` (inflections), `x⁴→1`, `x³−3x→2`. Regression tests added.
- **The math-truth invariant still holds end to end.** LLM phrasing is opt-in (per-request
  `llm_summaries`, server default off), only rephrases SymPy-verified facts, passes the equation
  through verbatim, and falls back to the deterministic line on any failure. Graph title + reasoning
  panel equation are always deterministic. The plumbing (main → router → `Request.use_llm_summary` →
  `_summarize`) is clean, and the UI reads the pref from storage at send time so the toggle takes
  effect mid-session.
- **Help intent** is wired correctly: `help` is in the required-field table (so it isn't mistaken for
  an underspecified graph), `HelpRequest` parses, and `Envelope.help` renders a static capabilities
  card — no extra model call.

### v1 acceptance (SPEC §10) — met
- [x] Always English → IR → SymPy → output; SymPy is the source of truth (incl. summary facts).
- [x] Full slice runs live; parabola vertex+direction and ≥3 phrasings produce correct graphs.
- [x] Underspecified → clarification; answering completes; out-of-scope → clear, now-friendlier
      "I can only graph y = f(x)" note instead of jargon.
- [x] Provider adapter interface w/ Anthropic only; OpenAI/Azure/Gemini absent from code, present as
      "Coming soon" + roadmap. Agents register; router dispatches via `can_handle`; all output uses
      the envelope.
- [x] Demo deliverables refreshed to the current UI (ready-state, graph-result, slice.gif).
- [x] Fresh clone runs via `run.sh` (one command) + documented steps; first-run key screen lists all
      four providers; key stored locally, never committed or sent anywhere but Anthropic.
- [x] Backend + frontend unit + Playwright E2E all pass in CI on push/PR.
- [~] SPEC §8/§10 "merged via reviewed PR" / "CI blocks merge" remain **WAIVED** (direct-to-`main`,
      human decision 2026-06-05). My phase-boundary reviews stood in for the PR gate. Mark these
      waived — not checked — at acceptance, as agreed.

### Follow-ups

1. **🟡 Verify the README install folds render on GitHub (Claude's flagged #4 — real risk).** The
   ```bash fences are indented **8 spaces, inside nested `<details>` that live within numbered list
   items**. That specific combination (raw-HTML block inside a list item + a 4+-space-indented fence)
   is exactly where GitHub's Markdown renderer often shows literal back-ticks or drops the code box,
   even though there's a blank line after each `<summary>`. I can't confirm from the source alone —
   **open the pushed README on github.com and look at every fold.** If any fence shows raw ``` or
   loses its box, the reliable fix is to **de-indent the fences to column 0** (GitHub renders fenced
   code inside `<details>` fine when the fence isn't indented), or flatten one level of nesting. Pure
   docs — does not affect the app.

2. **🟢 `help` extends SPEC §3's envelope vocabulary (graph|solution|proof|clarification|error +
   `help`).** Sensible, documented in NOTES, and backward-compatible (the UI falls through to
   `explanation` for unknown types). Fine as a deliberate extension — just keep it in the §3 list when
   NOTES/README are reconciled so the contract stays the single source of truth.

3. **🟢 Nit — `invalid_intent` is treated as a scope reason in the UI.** A malformed-IR error renders
   under the friendly "I can only graph y = f(x)" header. Reasonable as a catch-all, but semantically
   it's a "couldn't parse, rephrase" case, not an out-of-scope shape. Leave it or split it — cosmetic.

### Closing note
This is a clean v1. The thesis the project set out to prove — language in, structured IR, SymPy as
the sole source of mathematical truth, honest refusals over wrong answers — holds at every layer I
checked, including the new opt-in LLM phrasing. Nice work across all five phases.

---

## Phase 3 — Vertical slice complete & demo capture

**Verdict: ✅ approved to proceed to Phase 4 — with one correctness fix I'd like done first
(non-blocking for sign-off, but fix before anyone demos free-form cubics).** (reviewed 2026-06-05,
commit `614f543`)

The full slice is real and demonstrable: live in the browser, plus mocked Playwright E2E covering
all three paths. The demo deliverables are genuinely good — the `graph-result.png` shows request →
conversational line → interactive graph → expanded IR + SymPy equation in one frame, which is
exactly the §9 narrative. Phase 3 also went beyond "capture screenshots" and added a friendly
result-line layer; that's mostly excellent, with one math bug I caught (below).

### What I verified (re-run at HEAD)
- **Backend: 81 tests pass, 92% coverage** (gate 80%). **Frontend: 12 unit + 4 E2E pass**;
  `tsc`/`eslint`/`prettier` clean.
- Demo artifacts exist and are wired from the README: `demo/{ready-state,graph-result}.png`,
  `demo/slice.gif` (1.45 MB), plus a `demo/README.md` capture guide with exact prompts. `.claude/`
  has nothing committed.
- **The math-truth boundary holds.** The new `describe.py` line is built from SymPy facts; the
  optional LLM-phrased summary (`write_summary`) is **OFF by default** (`DTM_LLM_SUMMARIES`, defaults
  to 0), passes the equation through verbatim, is told never to change a number, and falls back to the
  deterministic line on any failure. The graph title and reasoning-panel equation are always rendered
  deterministically. Demo captures used the deterministic line — consistent.

### Against the SPEC Phase 3 checklist
- [x] Full happy path end to end (request → IR → SymPy → Plotly in React), confirmed by the
      `slice.spec.ts` happy-path E2E and the live capture.
- [x] Demo deliverables: ready-state screenshot, successful-graph screenshot (with IR + equation
      visible), and a motion GIF of the full slice.
- [x] Stretch §9.1 examples — **exceeded**: line-through-two-points and richer polynomials are in the
      demo prompt set, plus feature-aware graph windowing and shape-aware summaries.

### Earlier follow-ups — resolved
- [x] Phase 2 #1 (delete dead scaffold assets) — `src/assets/` Vite SVGs removed.
- [x] Phase 2 #2 (`finally` around `setLoading`) — `Chat.send` now uses `try/finally`.
- [x] Phase 1 deferred **live-API check** — satisfied; the slice runs live in the browser.
- Phase 2 #3 (tighten payload typing) was optional and not taken — fine, not pressing.

### Follow-ups

1. **🔴→fix soon — turning-point count is wrong for monotonic polynomials.**
   `describe._num_turning_points` counts *distinct real roots* of f′, but a turning point requires f′
   to **change sign** (a root of *odd* multiplicity). So `y = x³` reports *"degree-3 curve with 1
   turning point"* and `y = x⁵` reports 1 — both have **zero** (x=0 is a horizontal inflection). I
   reproduced both at HEAD. The code's own comment ("a repeated root is a horizontal inflection, not a
   turn") describes the right rule, but dedup-by-distinct-*value* doesn't detect multiplicity, so it
   isn't actually implemented. The tests only cover genuine-turn cases (cubic→2, quartic→3), so it's
   uncaught. **Scope:** only the friendly prose is wrong — the graph and the equation are correct, and
   the canonical demo prompts (parabola, line, degree-5 with 4 distinct roots) all report correctly —
   so this does **not** block Phase 3 sign-off. But "x cubed has one turning point" is exactly the kind
   of false math claim this project exists to never make, and it's reachable by a one-word prompt.
   Fix: count odd-multiplicity real roots of f′ (e.g. `sp.real_roots` with multiplicities, or detect
   sign changes of f′ between consecutive critical points) and add a monotonic-cubic / `x⁵` regression
   test. The renderer's windowing can keep using all distinct critical points as anchors — only the
   *note* needs the multiplicity rule.

2. **🟡 Scope expansion + the LLM's role — be deliberate at §10 acceptance.** Phase 3 grew a real
   feature surface (deterministic summaries, optional LLM phrasing, feature-windowing, polynomial-
   wiggle prompt guidance) beyond the literal "demo capture" ask. It's well-built and in service of
   the demo, so I'm not docking it — but note the SPEC §10 bullet *"the LLM only produces the IR"* is
   now technically broader: with summaries enabled the LLM also phrases (SymPy-verified) facts. The
   mitigations are sound, so at final acceptance phrase that criterion as **"the LLM is never the
   source of mathematical truth"** (which holds) and keep summaries **off** for any trust-critical
   demo (already the practice). Worth a one-line note in `NOTES.md` so the broadened LLM role is a
   recorded decision, not drift.

3. **🟡 The agent↔provider seam widened.** `GraphingAgent` now reaches back into the provider for
   `write_summary`, and `Request` carries the provider. Reasonable and gated, but it means the agent
   now depends on the provider exposing a phrasing method (documented in the `ProviderAdapter`
   Protocol — good). Keep an eye on this when the second agent/provider lands so the summary capability
   stays optional, not assumed.

### Carried-forward (tracking)
- SPEC §8/§10 PR-merge boxes remain **WAIVED** (direct-to-`main`) — mark waived, not checked.
- `NOTES.md` still lists Phase 3 as *"in progress"* — flip to complete once #1 is addressed.

---

## Phase 2 — Front end & chat UI

**Verdict: ✅ approved to proceed to Phase 3.** (reviewed 2026-06-05, commit `fd87243`)

Reviewed against an isolated worktree pinned to `fd87243` (Claude was concurrently editing CSS
colors on `main`, so I deliberately did **not** review the live working tree — these notes reflect
the committed Phase 2 state only). Clean, well-factored React: a key gate, a chat loop, and uniform
envelope rendering with a reasoning panel that surfaces exactly the IR→equation narrative the demo
needs. Strong phase.

### What I verified (re-run in the pinned worktree)
- `tsc -b --noEmit` clean · `eslint` clean · `prettier --check` clean · **Vitest 12/12 pass** ·
  **Playwright e2e passes** (real chromium, first-run key screen).
- **`npm ci` is consistent** — `plotly.js-dist-min` is in `package-lock.json`; `npm ci --dry-run`
  reports "up to date", so CI's `npm ci` won't break on a stale lock.
- Scaffold properly retired: `App.tsx` rewritten; `index.html` title = "Do the Math"; the old
  "Get started" smoke assertions are gone (both unit `App.test.tsx` and `e2e/smoke.spec.ts` rewritten
  to the new UI).

### Against the SPEC Phase 2 checklist — all present
- [x] React chat interface; renders user turns and agent responses across turns (`Chat.tsx`).
- [x] First-run key screen lists **all four** providers; **Anthropic selectable**, OpenAI / Azure /
      Gemini disabled with "Coming soon" badges; the "more providers coming" note is present.
- [x] Key persisted to `localStorage` only, sent via `X-Anthropic-Key` to the local backend, never
      elsewhere (`storage.ts`; asserted in `ApiKeyScreen.test` / `storage.test`).
- [x] Envelope rendering: interactive Plotly `graph`; `clarification` question; readable
      `explanation`; graceful `error` (with `role="alert"`).
- [x] **Reasoning panel** surfaces the Math Intent (IR) + SymPy-derived equation (SPEC §9) — the
      demo's "show the steps" requirement is built in, not bolted on later.

### Phase 1 follow-ups — all four resolved (commit `77a17fe`)
- [x] #1 Coverage gate relocated: `--cov` stays in `addopts`, `--cov-fail-under=80` moved to the CI
      command — focused local runs no longer report as failing.
- [x] #2 Interpreter error sanitized: router now logs the exception server-side and returns a fixed,
      generic client message (no SDK/transport leak on a live key).
- [x] #3 Clarification round-trip now tested end-to-end at `/chat` (underspecified → question →
      answer-with-history → graph) — and the UI wires the same loop (`Chat.test` covers history
      threading). Backend is up to 63 tests / 93%.
- [x] #4 `parabola_three_points` degenerate cases give a clean "three distinct points" message.

### Things I went looking for and was glad to find
- **History stays role-alternating.** `send()` is disabled while `loading`, so you can't queue two
  user turns; `toHistory` therefore yields strict user/assistant alternation, which the Anthropic
  messages API requires. The clarification loop won't desync.
- **`postChat` never throws** — network and non-200 are both converted to `error` envelopes, so the
  UI has a single render path and no unhandled rejections.
- Plotly is cleaned up on unmount (`Plotly.purge` in the effect's cleanup); jsdom-heavy Plotly is
  stubbed in tests so unit runs stay fast and deterministic.

### Follow-ups (none block Phase 3)

1. **Delete the dead scaffold assets.** `src/assets/{hero.png,react.svg,vite.svg}` are no longer
   referenced anywhere in `src/` (grep is clean) — leftover Vite boilerplate. Harmless but untidy;
   remove them (and any now-unused `App.css` scaffold rules) so the tree reads as intentional. Note:
   Claude's in-flight CSS pass may already be touching this — worth confirming after it lands.

2. **Add a `finally` around `setLoading(false)` in `Chat.send`.** Today it's safe because `postChat`
   is contractually non-throwing — but if that contract ever changes, a thrown error would strand the
   UI in "Working it out…" forever. One-line defensive guard.

3. **Tighten envelope payload typing (optional).** `AssistantMessage` does
   `payload as unknown as GraphPayload`. Works, but a discriminated union on `Envelope` (payload typed
   per `type`) would drop the double-cast and catch shape drift at compile time. Nice-to-have.

### Carried-forward (tracking; not Phase 2's job)
- SPEC §8/§10 PR-merge boxes remain **WAIVED** (direct-to-`main`) — mark waived, not checked, at
  final acceptance.
- I reviewed the **committed** state; the live CSS color work was intentionally out of scope. I'll
  pick up whatever lands there at the Phase 3 review.

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
  `can_handle → True` for the single v1 agent) are sensible and logged in `NOTES.md`.

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

Phase 0 is genuinely complete. Solid foundation. The decisions in `NOTES.md` (Math Intent law,
exact-arithmetic gotcha, deterministic clarification table, `unsupported` as a first-class IR kind,
tool-use for structured IR) are the right calls and bode well for Phase 1.

### Follow-ups (none block Phase 1)

1. **🟡 PR/merge-gate deviation — needs an explicit human decision.** SPEC §8 and §10 require
   feature branches merged via **reviewed pull requests** and "CI … blocks merge on failure."
   `NOTES.md` deliberately chose commit-straight-to-`main`, no PRs, with my phase-boundary review
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

3. **Dev/CI Node divergence.** `NOTES.md` records the dev box on Node 25; CI pins Node 22. 22-LTS in
   CI is fine, but a two-major gap can mask issues either direction. Intentional is fine — worth one
   line in `NOTES.md` on why 22, so it reads as a choice, not drift.

4. **Nit — scaffold leftovers.** `App.tsx` is still the stock Vite "Get started" template (react/vite
   logos, `hero.png`), and both smoke tests assert on that scaffold text. Expected at Phase 0 and the
   tests are explicitly labeled as throwaways for Phase 2/3 — just confirming they're on the list to
   be replaced, not carried forward.

### Spot-check on a thing I expected to bite — and didn't
- Model id `claude-sonnet-4-6` in `.env.example` / `NOTES.md` is the correct current Sonnet 4.6 id.
  `NOTES.md` flagged it "to confirm at implementation time" — confirmed correct. Keep it in config
  (it already is) so it stays swappable.
