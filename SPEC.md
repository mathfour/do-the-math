# Do the Math

A natural-language math agent. Describe what you want in plain English and Do the Math figures out the rest — starting with 2D graphing, and built from day one to grow into a full ecosystem of math agents (solving, factoring, calculus, proofs, and more).

This document is the build spec. It is written to be handed to Claude Code (or any developer) as the single source of truth for what to build, in what order, and how to verify it's done.

> **v1 scope (today's goal):** a complete, demonstrable vertical slice — Anthropic → Math Intent IR → SymPy → Plotly → React UI — that someone can watch working and immediately understand both the architecture and the future direction. Provider breadth, additional agents, and nice-to-haves are deliberately deferred. See Section 1.1.

---

## 1. What it does

**v1 — Graphing.** Tell it what you want and it derives the equation and renders an interactive 2D plot.

> "I need a parabola with the vertex at (1, 2), opening upward."

Do the Math interprets the request into a structured Math Intent, validates the math with SymPy, derives the equation, and returns the graph.

**Where it's going — an ecosystem of agents.** The backend classifies *what kind* of math request came in (graphing? solving? a proof?) and dispatches it to the appropriate registered agent. Every agent shares the same math-understanding layer rather than re-parsing English on its own. The graphing agent is the first; the architecture lets new agents register themselves and plug in without changing the orchestrator.

### 1.1 v1 scope decisions (what we are and aren't doing today)

The objective is a working, demonstrable first version that can be shown to someone **today**. We prioritize a complete vertical slice over provider breadth.

**In scope for v1:**
- **Anthropic only.** One working provider, end to end.
- The full vertical slice: Anthropic → Math Intent IR → SymPy → Plotly → React chat UI.
- The orchestrator and `Agent` registration architecture exactly as designed — but with a **simple classifier** and exactly **one registered agent (GraphingAgent)**.
- Demo deliverables (Section 9).

**Kept in the architecture, but NOT implemented in v1:**
- The provider adapter interface stays exactly as designed (so adding providers later is just new adapters).
- OpenAI, Azure OpenAI, and Gemini remain on the roadmap. **Do not implement these adapters until the core experience works.**

**Deferred (Phase 5+):** session history, property-based tests, additional agents.

> Note on sharing: because v1 is Anthropic-only, anyone running it themselves needs an **Anthropic** API key. v1 is built to be **demonstrated by the author on the author's key**; letting others run it on their own provider's key is the multi-provider roadmap item.

---

## 2. Core architectural principle: the Math Intent layer

**This is the most important design decision in the project. Build this first and build everything else on top of it.**

Do NOT go straight from English to an equation. Always go through a structured intermediate representation (the **Math Intent / IR**):

```
English  ──►  Math Intent (IR)  ──►  validated math  ──►  output
```

The LLM's job is to produce the IR — a structured description of what the user wants. It is **not** the source of mathematical truth. A deterministic math engine (SymPy) validates and derives from the IR. The LLM does language understanding (what it's good at); SymPy keeps the math correct (what it's good at).

Example:

> "Graph a parabola with vertex (1,2) opening upward."

LLM produces the IR:

```json
{
  "object": "parabola",
  "vertex": [1, 2],
  "direction": "up"
}
```

SymPy derives and validates:

```json
{ "equation": "y = (x - 1)**2 + 2" }
```

Why this matters: the Solver, Factoring, Calculus, and Proof agents will **all** consume the same IR and reuse the same math engine. Without this layer, every future agent reinvents English-parsing and math handling. With it, adding an agent is mostly defining how it acts on an IR it already understands.

### Shared components (build once, reuse everywhere)

```
math_interpreter.py   # English -> Math Intent (IR). LLM-backed, provider-agnostic.
math_engine.py        # IR -> validated equations/results. SymPy-backed. Source of truth.
graph_renderer.py     # validated math -> Plotly figure spec.
```

The v1 Graphing Agent is a thin orchestration over these three. Future agents reuse `math_interpreter` and `math_engine` directly.

---

## 3. Architecture

```
User (browser chat UI)
        │
        ▼
   React front end
        │
        ▼
   Python backend  ──►  Router / classifier (simple in v1)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        Graphing agent   Solver agent     Proof agent
        (v1, built)      (roadmap)        (roadmap)
              │
              ▼
        math_interpreter  →  math_engine (SymPy)  →  graph_renderer
              │
              ▼
        Provider adapter layer
        (Anthropic implemented; OpenAI/Azure/Gemini = roadmap)
              │
              ▼
        Model API (user's own Anthropic key in v1)
```

- **Front end:** React. A simple chat interface that opens in the browser.
- **Backend:** Python (FastAPI recommended). Hosts the router, the agents, the shared math components, and the provider adapter layer.
- **Router/classifier:** Classifies the incoming request and dispatches to a registered agent. In v1 the classifier is simple and there is exactly one registered agent (GraphingAgent) — but the classification + registration mechanism is real, so future agents slot in unchanged.
- **math_interpreter:** English → Math Intent (IR), via the user's chosen LLM provider (Anthropic in v1).
- **math_engine:** IR → validated equations/results, via SymPy. The source of mathematical truth — the LLM is not.
- **graph_renderer:** validated math → Plotly figure spec.
- **Provider adapter layer:** A shared interface with one thin adapter per provider. **Only the Anthropic adapter is implemented in v1.** The interface is designed so the others are pure additions later.

### Agent registration

Future agents are not special-cased in the orchestrator. They implement a common interface and register themselves:

```python
class Agent:
    name: str

    def can_handle(self, intent) -> bool:
        ...

    def execute(self, request) -> Envelope:
        ...
```

```python
GraphingAgent()   # the only registered agent in v1
# SolverAgent(), ProofAgent(), ... register themselves when added
```

The router asks each registered agent `can_handle(intent)` and dispatches to the match. Adding an agent requires no orchestrator changes.

### Output contract

Every agent returns the same envelope so the front end renders results uniformly and future agents follow the same shape:

```json
{
  "type": "graph | solution | proof | clarification | error",
  "payload": { },
  "explanation": "human-readable summary of what was done"
}
```

- `type: "graph"` — `payload` is a Plotly figure spec.
- `type: "clarification"` — the request was underspecified. `payload` carries the question, e.g. `{ "question": "Where is the vertex?" }`. (See Section 4.)
- `type: "error"` — `payload` carries a useful message; nothing crashes.

This contract is defined in Phase 1 even though only graphs and clarifications exist yet, so solution/proof outputs slot in without front-end rework.

---

## 4. Handling underspecified requests (clarification)

Not every request is solvable as written. "Graph a parabola" has no vertex. The system must ask rather than guess.

The mechanism is the **IR itself**, not a guessed confidence number:

- Each object type in the IR has required fields (a parabola requires a vertex and a direction, etc.).
- After `math_interpreter` produces the IR, the backend checks for missing required fields.
- If a required field is missing, the agent returns `type: "clarification"` with a targeted question.
- The front end displays the question; the user's answer is fed back in to complete the IR.

**v1 scope of the clarification loop:** clarification only needs to resolve the **current active request** — i.e. fill in missing fields for the request being made right now. Cross-request follow-ups that reference earlier results ("move that same parabola left") depend on session history and are **Phase 5+**, not part of v1.

This is deterministic and checkable. We deliberately do **not** rely on an LLM-produced confidence float — those are poorly calibrated. Completeness of the required IR fields is the honest signal.

---

## 5. What counts as graphable (v1 scope)

Claude Code must not silently decide scope. v1 supports these function types of the form `y = f(x)`:

**Supported in v1**
- Linear
- Quadratic
- Polynomial (general)
- Trigonometric (sin, cos, tan)
- Exponential
- Logarithmic

**Out of scope for v1** (return a clear "not supported in v1" message, not a wrong graph)
- Implicit equations (e.g. `x² + y² = 25`)
- Parametric curves
- Polar graphs
- Piecewise functions
- Inequalities / shaded regions

Anything outside the supported list returns an `error` (or `clarification`) explaining it's not yet supported — never a guess.

---

## 6. Development phases

Each phase ends in a runnable, tested state. Don't start a phase before the prior phase's tests pass.

### Phase 0 — Repo & tooling
- Initialize the GitHub repository (see Section 8).
- Project skeleton: `/backend` (Python) and `/frontend` (React).
- Linting/formatting (ruff + black for Python, ESLint + Prettier for React).
- Test harnesses: pytest (backend), Vitest + React Testing Library (front-end unit), Playwright (end-to-end).
- CI workflow running lint + all tests on every push/PR.

### Phase 1 — Shared math core & output contract  ← the foundation
- Define the Math Intent (IR) schema for v1 graph objects, including required fields per object.
- Build `math_interpreter` (English → IR) backed by the **Anthropic** adapter.
- Build `math_engine` (IR → validated equation/result) on **SymPy**.
- Build `graph_renderer` (validated math → Plotly spec).
- Define the output envelope, including `clarification` and `error` types.
- Build the router/classifier scaffold and the `Agent` registration interface; register the Graphing Agent (the only agent in v1).
- Expose a single backend endpoint (e.g. `POST /chat`) taking a message + key config and returning the envelope.

### Phase 2 — Front end & chat UI
- React chat interface that opens in the browser.
- **First-run / API key screen.** On first launch, the user is shown a provider/key entry screen:
  - A provider selector listing all planned providers: **Anthropic**, OpenAI, Azure OpenAI, Google Gemini.
  - In v1, **only Anthropic is selectable/active.** The others are shown but not selectable, each with a "Coming soon" label.
  - A short line on the screen states that additional AI providers will be added in a future version.
  - The user enters their **Anthropic API key**; it is persisted locally (env var / local config) and never transmitted anywhere except Anthropic.
  - Keep this UI minimal: a simple selector with three non-selectable "Coming soon" entries and a key field. No per-provider configuration UI, no settings panes — that arrives with the adapters.
- Render the envelope: interactive Plotly graph for `graph`; the question for `clarification`; readable text for `explanation`; graceful display for `error`.

> Why show the "Coming soon" providers now: the key-entry screen is the clearest place to communicate the model-agnostic direction. A demo viewer sees the multi-provider intent immediately, and when the adapters land later the screen only needs those options enabled — no redesign.

### Phase 3 — Vertical slice complete & demo capture
- Confirm the full happy path runs end to end: type a request → IR generated → SymPy derives equation → Plotly graph renders in the React UI.
- Produce the demo deliverables (Section 9).
- If time permits, add the richer reasoning examples (Section 9.1).

### Phase 4 — Local run & sharing
- Single documented command (or short sequence) to install and launch.
- App opens in the browser automatically.
- Verify a fresh clone runs and works with an Anthropic key.

### Phase 5+ — Deferred (do not let these block v1)
- **Remaining provider adapters:** OpenAI, Azure OpenAI, Gemini (pure additions behind the existing interface).
- Harden the classifier as more agents arrive.
- **Session history** — enables "move that same parabola 3 units left."
- **Property-based tests** (Section 7).
- Additional agents (Solver, Factoring, Calculus, Geometry, Statistics, Proof).

---

## 7. Testing

Testing is a first-class requirement. The bar is **quality unit coverage plus end-to-end coverage, including the front end.**

### Backend unit tests (pytest)
- IR extraction: a range of phrasings map to the correct Math Intent.
- Equation derivation via `math_engine`: correct equation for given IR (e.g. vertex (1,2) up → `y = (x-1)**2 + 2`).
- Output envelope: valid envelope from every path; underspecified input returns `clarification`; unsupported input returns `error` with a useful message.
- Anthropic adapter: maps a known input to the normalized internal shape (mock the network — no live API in unit tests).
- Router/classifier and agent registration: a known input routes to GraphingAgent.

### Front-end unit tests (Vitest + React Testing Library)
- First-run flow renders and captures the Anthropic key correctly.
- Key is stored locally and not leaked to unintended destinations.
- Chat component renders user messages and agent responses across turns.
- Graph component renders a valid Plotly spec; `clarification` renders the question; `error` renders the error state.

### End-to-end tests (Playwright)
- Full happy path in a real browser: launch → enter key → type a parabola description → see the rendered graph.
- Clarification loop: an underspecified request prompts a question, and answering it completes the graph.
- Error path: invalid/empty key and unsupported request types surface clear messages without crashing.
- (Use a mocked backend or a test key so E2E runs don't depend on live model billing.)

### Property-based tests (Phase 5+)
- Every derived parabola passes through its stated vertex.
- "Opens upward" ⇒ positive leading coefficient; "opens downward" ⇒ negative.

### Coverage & CI
- Target meaningful coverage (~80%+ on backend logic; cover all critical front-end paths).
- All suites run in CI on every push/PR. A red suite blocks merge.

### Demo-day critical path vs. fast-follow
The full testing bar above stands. For **sequencing** toward a same-day demo, the minimum to put the demo on its feet is: (1) the working vertical slice and (2) **backend unit tests** covering IR extraction and SymPy derivation — the math must be trustworthy on screen. **Playwright E2E and property-based tests are fast-follow** (next-day hardening), not demo blockers. "Fast-follow" means committed and scheduled, not dropped — they remain required for `main` to be considered done.

---

## 8. Version control (GitHub)

- All work lives in a GitHub repository from Phase 0.
- **Branching:** `main` stays releasable. Feature work on branches (`feature/...`, `fix/...`) merged via pull request.
- **Commits:** Small, descriptive. Conventional Commits style recommended (`feat:`, `fix:`, `test:`, `docs:`).
- **Pull requests:** CI (lint + all tests) must pass before merge.
- **Secrets:** API keys are NEVER committed. Add `.env`, local config, and key files to `.gitignore`. Provide a `.env.example` with placeholder names only.
- **Sharing:** v1 is Anthropic-only, so a recipient running it themselves needs an Anthropic key. Clone the repo, run, enter the key.

---

## 9. Demo deliverables (v1 success depends on these)

The primary success criterion is that **someone can see the application working today and immediately understand the architecture and future direction.** In addition to the code, v1 must produce:

- **Screenshot:** the chat interface (empty / ready state).
- **Screenshot:** a successful graphing result (request + rendered graph visible).
- **Demo GIF or short screen recording** showing the full slice in motion:
  1. user enters a graph request,
  2. the Math Intent (IR) is generated,
  3. SymPy derives the equation,
  4. the graph renders in the UI.

> These artifacts are captured **by the developer while the app is running** during the build — manually is fine. Automated screenshot/GIF tooling is **not** required and should not block the demo; only reach for it if it's genuinely quick. Store the captures in a `/demo` directory referenced from this README. Surface the IR and derived equation in the UI (even a small "reasoning" panel) so the recording visibly shows steps 2–3, not just input → graph.

### 9.1 Stretch examples (if time permits)

To show real mathematical reasoning beyond plugging into vertex form, add one or two of:
- a line through two given points,
- a parabola from a vertex **plus** an additional point on the curve,
- a transformed parent function (e.g. shifted/stretched sin or exponential).

These demonstrate that SymPy is doing genuine derivation, which strengthens the demo narrative.

---

## 10. Acceptance criteria (human checklist)

### Vertical slice & correctness
- [ ] Requests pass through a structured Math Intent (IR) — never English straight to equation.
- [ ] SymPy (`math_engine`) is the source of mathematical truth; the LLM only produces the IR.
- [ ] The full slice runs end to end: Anthropic → IR → SymPy → Plotly → React UI.
- [ ] Describing a parabola by vertex + direction produces the correct equation and matching graph.
- [ ] At least three differently-phrased graphing requests all produce correct graphs.
- [ ] The response includes a readable explanation of what was derived.

### Clarification & scope
- [ ] An underspecified request (e.g. "graph a parabola") returns a `clarification` question instead of guessing.
- [ ] Answering the clarification completes the request.
- [ ] An out-of-scope type (e.g. `x² + y² = 25`) returns a clear "not supported in v1" message — not a wrong graph.

### Architecture (built now, even if single-provider / single-agent)
- [ ] The provider adapter interface exists; the Anthropic adapter is implemented.
- [ ] OpenAI / Azure / Gemini are absent from the code but present in the roadmap — adding them would be a new adapter only.
- [ ] Agents implement a common interface and register themselves; GraphingAgent is the one registered agent.
- [ ] The router dispatches via `can_handle` without being modified per agent.
- [ ] All agent outputs use the shared output envelope.

### Demo deliverables
- [ ] Chat-interface screenshot exists.
- [ ] Successful-graph screenshot exists.
- [ ] Demo GIF / recording exists and shows: request → IR → SymPy derivation → rendered graph.
- [ ] (Stretch) at least one richer reasoning example is included.

### Local run & sharing
- [ ] A fresh clone runs locally with the documented commands and opens in the browser.
- [ ] On first run, a provider/key screen appears that lists Anthropic, OpenAI, Azure OpenAI, and Gemini.
- [ ] Anthropic is selectable; the other three are visible but not selectable, each marked "Coming soon".
- [ ] The screen notes that more AI providers are coming in a future version.
- [ ] The Anthropic key is stored locally and never committed or sent anywhere except Anthropic.

### Testing & version control
- [ ] Backend unit tests pass.
- [ ] Front-end unit tests pass.
- [ ] End-to-end (Playwright) tests pass.
- [ ] CI runs all suites on every push/PR and blocks merge on failure.
- [ ] `main` is releasable; work merges via reviewed pull requests.

---

## 11. Agent ecosystem

```
Current Agents
--------------
[x] Graphing Agent

Planned Agents (reuse math_interpreter + math_engine)
-----------------------------------------------------
[ ] Solver Agent
[ ] Simplification Agent
[ ] Factoring Agent
[ ] Calculus Agent
[ ] Geometry Agent
[ ] Statistics Agent
[ ] Proof Agent
```

---

## 12. Roadmap

- [x] Graphing agent (2D) on the shared math core — **Anthropic, v1**
- [ ] Remaining provider adapters (OpenAI, Azure OpenAI, Gemini)
- [ ] Router/classifier hardening as agents are added
- [ ] Equation solver agent
- [ ] Theorem / proof agent
