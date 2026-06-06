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
- **NOTES.md** (this file) — living dev log: decisions + rationale, deviations from SPEC, phase status, Clarice's review notes, open questions.

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
- **LLM role boundary (decision, re: SPEC §10):** the LLM can also *phrase* SymPy-verified facts (equation passed verbatim; it never invents/changes numbers), so the literal "the LLM only produces the IR" is broader than at launch. The invariant we actually hold and will assert at acceptance is **"the LLM is never the source of mathematical truth"** — SymPy is. This is now a **per-user choice** — a checkbox on the key screen (default **off**), persisted to `localStorage` and sent per request (`llm_summaries` in the `/chat` body); `DTM_LLM_SUMMARIES` is just the server default when a request doesn't specify. Stays off for the trust-critical demo.

## Phase status

- **Phase 5 — Hardening (post-v1):** _in progress._
  - **Property-based tests (Hypothesis)** on the math core (`tests/test_properties.py`): the displayed `equation` always re-parses to the exact derived expr (round-trip, parsed against the engine's real `x`); exact-arithmetic preserved (no stray `Float` for int/rational/exact-float inputs); a degree-n polynomial has 0…n-1 turning points; rendered figures are always JSON-safe (every y finite-or-`None`, never NaN/Inf). Backend now **97 tests / 92%**.
  - **Bug found & fixed by the round-trip property:** `_guard` rejected `y = x` (and anything reducing to the bare symbol) as "a relation, not a function" — because a bare SymPy `Symbol` *is* a `Boolean` instance, so `isinstance(expr, Boolean)` was a false positive. Fixed to check `is_Relational` / `BooleanFunction` / `BooleanAtom` instead; regression tests added at both the guard level and the full slice (`y = x` derives **and renders**, per Clarice).
  - **Feedback:** a "Send feedback" button (chat header + key screen) opens a branded in-app feedback screen (`FeedbackScreen.tsx`, styled like the splash) offering two routes — a pre-filled **GitHub issue** or a **copyable email** (`mathfour.com@gmail.com`). Constants in `lib/feedback.ts`. No backend or third party.
  - **Classifier/agent robustness (#2):** a property test asserts the agent returns a valid envelope (graph/clarification/error/help) for *any* raw IR — arbitrary kinds + junk fields — never an exception; API-level parametrized tests confirm malformed IR yields 200, never 500. **Bug found & fixed:** `check_required` did `kind not in REQUIRED`, which raised `TypeError` on an unhashable kind (e.g. `{"kind": ["x"]}`) → would 500; guarded with `isinstance(str)` so it degrades to the "what kind?" clarification.
  - **Edge cases (#3):** mostly already covered (tan asymptote gaps, log domain clamping, exact rationals, steep/constant/wiggly, all rejections, + the property suite). Filled the one gap — exact **symbolic-constant** string inputs (`sqrt(2)`, `pi`) stay exact; bare letters like `"e"` are rejected as variables. No bug; core held. Backend **113 tests / 92%**.
- **Phase 4 — Local run & sharing:** _complete — Clarice signed off; **v1 ships**._
  - `./run.sh` (repo root) installs both halves (`uv sync` + `npm install`), starts the backend (port 8000) + frontend, and opens the app in the browser (`vite --open`); Ctrl+C stops both. README "Running locally" documents it + the manual two-terminal alternative. Prereqs: `uv`, Node 20.19+/22.12+.
  - Key entered in the UI (no `.env` needed for a fresh clone). Fresh-clone install + build + tests verified.
- **Phase 3 — Vertical slice complete & demo capture:** _complete (Clarice-approved → Phase 4)._
  - **Playwright E2E** built against a mocked `/chat` (route interception + CORS preflight handling, no live billing): happy path (key → request → graph, then expand reasoning panel → IR + equation), clarification loop (question → answer → graph), out-of-scope error path. 4 E2E specs total (incl. the key-screen smoke).
  - **Demo:** `/demo/README.md` capture guide (exact prompts + filenames); main README has a Demo section referencing `demo/{ready-state,graph-result}.png` + `demo/slice.gif`. **Author captures these manually** (decision 2026-06-05); **LLM result line kept OFF** for captures.
  - The Phase-1-deferred **live API test is satisfied** — the full slice runs live in the browser.
  - **Friendlier out-of-scope UX:** scope responses (out-of-scope shapes, or a request we can't graph) render as a gentle info note ("Aw, man… I can only graph right now." + what we *can* graph), reason-aware in the frontend (real failures — bad key, server down — stay red alerts). Pure client-side branch on `payload.reason` → **no extra tokens**. The `unknown` message is now "Future versions of "Do the Math" will be able to do more robust math things. Stay tuned!".
  - **Help intent:** a question *about the tool* ("what can I graph?", "what can you do?", "help") is classified by the interpreter as a new IR kind `help` and answered with a friendly capabilities response — a new `help` **envelope type** (small extension to SPEC §3's listed types: graph/solution/proof/clarification/error). **No extra cost** — same single interpret call; the answer text is static (frontend-rendered). Distinct from the out-of-scope "Aw, man…" path.
  - **Turning-point count fix (Clarice #1):** `describe._num_turning_points` now counts **sign changes of f′** (odd-multiplicity roots), not distinct roots — so `y=x**3`/`y=x**5` correctly report **0** turns (inflection), `y=x**4` reports 1. Regression tests added. (The renderer still anchors its window on all distinct critical points — only the note needed fixing.)
  - **MathFour branding (with the author):** `mathfour.com` logo + favicon (`public/`), "Brought to You By" credit centered on the key screen, full-width top bar on the graphing page (logo flush-left, baseline-aligned with "Do the Math" + "brought to you by"; small CSS nudge to sit the lockup on the text baseline), darker `--muted` for contrast, larger header title, multi-line composer, and a fuller empty-state hint. Removed leftover Vite scaffold SVGs.
- **Phase 2 — Front end & chat UI:** _complete (Clarice-approved at `fd87243`; the live-testing polish that landed after — `aa82647` etc. — folds into the Phase 3 review per Clarice's note)._
  - First-run key screen (provider selector: Anthropic active; OpenAI/Azure/Gemini disabled "Coming soon"; future-providers note; key → `localStorage`), chat with message-list + composer, envelope rendering (graph via Plotly + reasoning panel showing IR + derived equation; clarification; graceful error), `App` key-gate + "Change key".
  - `lib/`: `types.ts` (Envelope mirror), `storage.ts` (localStorage key), `api.ts` (`POST /chat` with `X-Anthropic-Key` + history; non-200/network → error envelope so the UI never special-cases fetch failures).
  - **12 frontend unit tests** (key screen renders/captures/stores key + only Anthropic selectable; chat renders turns; graph/clarification/error from sample envelopes; history sent on next turn). Playwright smoke updated to the new key screen. Stock Vite `App.tsx` + smoke replaced (Clarice carry-forward cleared).
  - Phase 2 decisions:
    - **Plotly via `plotly.js-dist-min` + a thin `useEffect`/`Plotly.react` wrapper**, not `react-plotly.js` — the latter isn't updated for React 19. Loose `plotly.d.ts` covers the small slice we use; tests mock the module.
    - **In-memory `localStorage` shim in `src/test/setup.ts`** — this jsdom build ships a non-functional `Storage`.
    - **Bundle size:** plotly makes the JS bundle ~4.8 MB (1.4 MB gzipped). Fine for a local demo; a dynamic-import code-split is a possible Phase 5 optimization (noted, not done).
    - Backend dev port assumed **8000** (`api.ts` default; overridable via `VITE_API_BASE`); CORS already allows the Vite origin. Run commands documented in Phase 4.
  - **Phase 2 live-testing tweaks (with the author, 2026-06-05)** — done while running the real slice in the browser:
    - **MathFour branding:** page background `#E5F7FD`, white cards, near-black text, accent `#1A6FA3` (light theme).
    - **Adapter robustness:** the model sometimes returns the tool input's `intent` as a JSON *string*; `_extract_intent` now parses it (and reports/loggs anything truly malformed instead of crashing). Caught only because we live-tested — mocked units couldn't see it.
    - **Feature-aware graph window + y-range:** frame the x-window on turning points (roots fallback), and for wiggly polynomials (≥2 turning points) frame the y-axis on the local extrema so steep tails clip instead of flattening the shape. Fixes "cubic looks flat", far-from-origin vertices, etc.
    - **Robust real roots (`math_engine.real_solutions`):** polynomial root isolation, correct in the *casus irreducibilis* (cubic/quartic derivatives whose real roots come back in complex form that `.is_real` can't classify). Fixes turning-point counts (was "0"/"1") and windows for quartics+.
    - **Conversational result line (`describe.py`):** playful, shape-aware opener + a short SymPy-computed note (vertex/slope/period/turning points). Pretty equations via `formatting.pretty_equation` (`·`, superscripts, real `−`, `ln`) — used in the line **and** the graph title; the reasoning panel keeps the canonical SymPy form. Reasoning panel collapsed by default.
    - **LLM-written result line:** provider gains `write_summary(facts)`; the agent asks the model to rephrase **SymPy-verified facts** (never inventing numbers) for fresh wording each graph, falling back to the deterministic line. **Toggled OFF by default** (`graphing.LLM_SUMMARIES_ENABLED` / env `DTM_LLM_SUMMARIES`) to save the author's API tokens during testing — flip on to re-enable. Decision: keep the code, gate it behind a flag rather than delete.
    - **Interpreter prompt:** honor stated polynomial degree/order ("fourth-order" → degree 4) and build "lots of hills and valleys" from polynomials with several distinct real roots. (Prompt nudge, not a hard guarantee — a "polynomial by roots" IR was offered as a bulletproof follow-up; not yet taken.)
- **Phase 1 — Shared math core & output contract:** _complete (Clarice-approved; live check deferred to Phase 2/3)._
  - `ir.py` (discriminated-union IR + Envelope), `math_engine.py` (SymPy derive), `graph_renderer.py` (Plotly dict), `clarification.py`, provider seam (`base`/`fake`/`anthropic_adapter` via tool-use), `math_interpreter`, agent registry + `GraphingAgent`, `router`, `config`, FastAPI `POST /chat` + `/health`.
  - **60 backend tests, 93% coverage** (gate set to fail under 80%). Anthropic adapter tested with the network mocked.
  - Live check script at `backend/scripts/live_check.py` — runs the real Anthropic slice. **Deferred (human decision 2026-06-05): we'll do the first real-API test once the UI exists (Phase 2/3), so it can be watched end to end rather than read from a terminal.** Backend is fully exercised by mocked unit tests (93%) until then.
  - Reconciliations / deviations from SPEC (intentional):
    - **Graph payload shape:** SPEC §3 says `graph` payload "is a Plotly figure spec." We nest it as `{"figure": <plotly>, "equation": str, "ir": dict}` so the reasoning panel (SPEC §9 — surface IR + derived equation) has its data. Frontend reads `payload.figure`.
    - **`GraphingAgent.can_handle` returns `True`** in v1 (one agent claims every request, turning unknown/missing kinds into clarifications). Real kind-based classification arrives with the second agent — SPEC §3/§6 call the v1 classifier "simple" and defer hardening to Phase 5. A `handles_kind()` helper already encodes the kind set for that future split.
    - **Coverage gate** lives in `pyproject` `addopts` (`--cov-fail-under=80`), so it's enforced identically by local `uv run pytest` and CI — rather than a separate CI step (addresses Clarice follow-up #2).
- **Phase 0 — Repo & tooling:** _complete (Clarice-approved)._
  - Docs split: `SPEC.md` frozen, `NOTES.md` started, `README.md` trimmed to public form.
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
- **Keep `write_summary` optional (Clarice Phase 3 #3):** `GraphingAgent` uses `request.provider.write_summary` (gated by `LLM_SUMMARIES_ENABLED`). When a second agent/provider lands, treat that capability as optional on the `ProviderAdapter` so a provider without it still works.

## Clarice review log

- **Phase 4 / v1 — SIGNED OFF (ships).** All five phases hold together; thesis intact end to end (language → IR → SymPy as sole math truth; honest refusals), and it survived the opt-in LLM phrasing (facts from SymPy, equation verbatim, deterministic fallback, off by default). Turning-point fix re-verified (x³/x⁵→0, x⁴→1, x³−3x→2). Three follow-ups:
  1. **README install folds render on GitHub** → **verified GOOD** by fetching the rendered HTML from the GitHub API: every install command (incl. the deepest nested Homebrew one) renders as a real code box, zero literal backticks. No change needed.
  2. **`help` envelope type** → added to the README contract example (`71777a0`) so the living vocabulary stays authoritative; SPEC.md stays frozen, deviation recorded here.
  3. **Cosmetic:** `invalid_intent` ("please rephrase") renders under the scope header — fine as a catch-all; left as-is per her guidance (split only if we want the wording to match).
- **Phase 3 — APPROVED** (→ Phase 4). Demo-ready: live happy path + mocked E2E on all three paths, good demo artifacts, math-truth boundary intact. Both Phase 2 follow-ups landed.
  1. **Turning-point count** → fixed: count sign changes of f′ (odd-multiplicity roots), not distinct roots; `x**3`/`x**5` → 0, `x**4` → 1; regression tests added.
  2. **Broadened LLM role** → recorded as a decision above; at acceptance phrase §10 as "the LLM is never the source of mathematical truth"; summaries stay off for the demo.
  3. **`write_summary` dependency** → noted in "To carry into later phases"; keep optional for the future second agent/provider.

- **Phase 2 — APPROVED** (proceed to Phase 3), reviewed at committed state `fd87243` in an isolated worktree (live CSS work was deliberately out of her scope; she'll pick it up at Phase 3 review). Three non-blocking follow-ups:
  1. **Delete dead scaffold assets** (`src/assets/{hero.png,react.svg,vite.svg}`) → done (`git rm`).
  2. **`finally` around `setLoading(false)` in `Chat.send`** → done (guard so a future throwing `postChat` can't strand the UI in loading).
  3. **Tighter envelope payload typing** (discriminated union to drop the `as unknown as GraphPayload` cast) → _optional / deferred_; noted as a nice-to-have.
  - Carried forward: SPEC §8/§10 PR boxes stay **waived**.
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
