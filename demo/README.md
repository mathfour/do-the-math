# Demo artifacts

Captured by the author while the app is running (manual is fine — see SPEC §9).
The LLM-written result line is intentionally **off** for these captures, so the
result line is the deterministic friendly one (still shows the IR + equation).

## Files to produce

| File | What it shows |
| --- | --- |
| `ready-state.png` | The chat, empty/ready state (right after entering the key). |
| `graph-result.png` | A successful graph **with the "How this was derived" panel expanded** so the Math Intent (IR) + derived equation are visible. |
| `slice.gif` (or `.mov` / `.mp4`) | The full slice in motion: request → IR → SymPy equation → rendered graph. |

These filenames are what the main `README.md` references — keep them, or update both.

## How to capture

1. Start the backend and frontend (see the main `README.md` "Running locally" / `NOTES.md`).
2. Open <http://localhost:5173> and enter your Anthropic key.
3. **`ready-state.png`** — screenshot the empty chat.
4. Type **`a parabola with vertex (1, 2), opening upward`** and send. When the graph
   appears, click **"How this was derived"** to expand the IR + equation, then
   screenshot → **`graph-result.png`**.
5. **`slice.gif`** — record the same flow start to finish: type the request, watch the
   result line + graph appear, then expand the reasoning panel.

## Good demo prompts

- `a parabola with vertex (1, 2), opening upward` — the canonical example
- `the line through (0, 0) and (2, 4)` — genuine SymPy derivation
- `graph a parabola` — shows the clarification loop (it asks for the vertex)
- `graph x^2 + y^2 = 25` — shows a clean "not supported in v1" refusal
- `a fourth-order polynomial with lots of hills and valleys` — shows the wiggle + reasoning
