# Do the Math

A natural-language math agent. Describe what you want in plain English and Do the Math figures out the rest — starting with 2D graphing, and built from day one to grow into a full ecosystem of math agents (solving, factoring, calculus, proofs, and more).

> 🚧 **Status: in active development — v1 (Phase 0).** This README is a living document and grows as the build progresses. The full, frozen build spec lives in [SPEC.md](SPEC.md); build decisions and progress are tracked in [notes.md](notes.md).

---

## What it does

**v1 — Graphing.** Tell it what you want and it derives the equation and renders an interactive 2D plot.

> "I need a parabola with the vertex at (1, 2), opening upward."

Do the Math interprets the request into a structured **Math Intent**, validates the math with SymPy, derives the equation, and returns the graph.

**Where it's going — an ecosystem of agents.** The backend classifies *what kind* of math request came in (graphing? solving? a proof?) and dispatches it to the appropriate registered agent. Every agent shares the same math-understanding layer rather than re-parsing English on its own. The graphing agent is the first; the architecture lets new agents register and plug in without changing the orchestrator.

---

## The core idea: the Math Intent layer

Do the Math never goes straight from English to an equation. It always passes through a structured intermediate representation — the **Math Intent (IR)**:

```
English  ──►  Math Intent (IR)  ──►  validated math  ──►  output
```

The LLM's job is to produce the IR — a structured description of what the user wants. It is **not** the source of mathematical truth. A deterministic math engine (SymPy) validates and derives from the IR. The LLM does language understanding (what it's good at); SymPy keeps the math correct (what it's good at).

> "Graph a parabola with vertex (1,2) opening upward."

The LLM produces the IR:

```json
{ "kind": "parabola_vertex_direction", "vertex": [1, 2], "direction": "up" }
```

SymPy derives and validates:

```json
{ "equation": "y = (x - 1)**2 + 2" }
```

Why it matters: every future agent (Solver, Factoring, Calculus, Proof) consumes the **same** IR and reuses the **same** math engine. Adding an agent is mostly defining how it acts on an IR it already understands — not reinventing English-parsing and math handling.

### Shared components (built once, reused everywhere)

- `math_interpreter` — English → Math Intent (IR). LLM-backed, provider-agnostic.
- `math_engine` — IR → validated equations/results. SymPy-backed. The source of mathematical truth.
- `graph_renderer` — validated math → Plotly figure spec.

---

## Architecture

```
User (browser chat UI)
        │  React + TypeScript front end
        ▼
   Python backend (FastAPI)  ──►  Router / classifier
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                  Graphing agent   Solver agent     Proof agent
                  (v1, built)      (roadmap)        (roadmap)
                        │
                        ▼
              math_interpreter → math_engine (SymPy) → graph_renderer
                        │
                        ▼
              Provider adapter layer
              (Anthropic implemented; OpenAI/Azure/Gemini = roadmap)
                        │
                        ▼
              Model API (your own Anthropic key in v1)
```

- **Agents register themselves** behind a common interface (`can_handle(intent)` / `execute(request)`); the router dispatches to the match without per-agent special-casing.
- **Every agent returns the same output envelope**, so the front end renders results uniformly and future agents follow the same shape:

```json
{
  "type": "graph | solution | proof | clarification | error",
  "payload": { },
  "explanation": "human-readable summary of what was done"
}
```

- **Underspecified requests ask rather than guess.** Each IR object type has required fields; if one is missing, the agent returns a `clarification` question (e.g. "Where is the vertex?") instead of inventing an answer. This is deterministic — completeness of the required IR fields, not an LLM confidence score.

---

## What's graphable in v1

Functions of the form `y = f(x)`:

**Supported** — linear, quadratic, polynomial, trigonometric (sin/cos/tan), exponential, logarithmic.

**Out of scope for v1** (returns a clear "not supported in v1" message, never a wrong graph) — implicit equations (e.g. `x² + y² = 25`), parametric curves, polar graphs, piecewise functions, inequalities / shaded regions.

---

## AI providers

v1 is **Anthropic-only**, end to end. The provider adapter interface is built so additional providers are pure additions later. On first run you'll see a provider/key screen listing Anthropic (active) plus OpenAI, Azure OpenAI, and Google Gemini (shown as "Coming soon"). You supply your own **Anthropic API key**; it's stored locally and never sent anywhere except Anthropic.

---

## Running locally

> ⏳ Coming in Phase 4 — a single documented command to install and launch, opening in the browser. Until then, see [notes.md](notes.md) for current build status.

---

## Roadmap

- [x] Graphing agent (2D) on the shared math core — **Anthropic, v1**
- [ ] Remaining provider adapters (OpenAI, Azure OpenAI, Gemini)
- [ ] Router/classifier hardening as agents are added
- [ ] Equation solver agent
- [ ] Theorem / proof agent

### Planned agents (all reuse `math_interpreter` + `math_engine`)

Solver · Simplification · Factoring · Calculus · Geometry · Statistics · Proof

---

## Project docs

- **[SPEC.md](SPEC.md)** — the frozen v1 build spec and acceptance checklist (the original planning document; the source of truth for what we agreed to build).
- **[notes.md](notes.md)** — the living dev log: decisions and their rationale, deviations from the spec, phase status, and review notes.
