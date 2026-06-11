# Skill-behavior tests (opt-in, LLM-backed)

These scenarios verify that the **model follows SKILL.md** — they assert on the
**tool-call trace**, not the model's free-form prose. They are atelier's analog
of impeccable's skill-behavior suite, adapted to atelier's stdlib-only,
no-SDK-on-this-box constraints.

## Two layers, by design

| Layer | What | Where | Needs SDK/key? |
|---|---|---|---|
| **Engine unit tests** | The assertion engine, fed pre-recorded traces via `ReplayAgent`. Asserts correct-trace→pass, incorrect-trace→fail. | `tests/test_skill_behavior_assertions.py` (run by `tests/run.py`) | **No** — pure stdlib, no network |
| **Live runner** | Real `LiveAnthropicAgent` against the Messages API, evaluated by the same engine. | `tests/skill_behavior/run_skill_behavior.py` (manual) | Yes — skips cleanly if absent |

The default suite (`python3 tests/run.py`) runs only the engine unit tests. The
`tests/skill_behavior/` **subdir is never discovered** by the runner — `run.py`
lists `tests/test_*.py` at the top level only (`os.listdir`, no recursion), so
nothing here executes by accident, with or without an API key.

## Pluggable-agent architecture

`agent.py` defines an `Agent` protocol:

```
run(system_prompt, user_prompt, tools, workspace_dir, max_steps) -> Trace
```

A `Trace` is a stdlib dataclass: an ordered list of `ToolCall(name, args,
result_summary)` plus the final assistant text. Two implementations:

- **`ReplayAgent(trace)`** — returns a pre-recorded `Trace`. Pure stdlib, no
  network. This is what makes the assertion engine testable offline: the engine
  only ever sees a `Trace`, so a fixture is indistinguishable from a live run.
- **`LiveAnthropicAgent(model="claude-sonnet-4-6")`** — runs a real Anthropic
  Messages-API tool-use loop. It **lazily imports `anthropic` inside `run()`**,
  so importing `agent.py` never fails when the SDK is absent. If the SDK or
  `ANTHROPIC_API_KEY` is missing it raises `AgentUnavailable` (a skip signal),
  never an `ImportError` at module load and never a hard failure for a missing
  key.

`tools.py` provides the workspace-scoped tools (`bash`, `read`, `write`,
`list`) bounded to a temp workspace with output byte caps. The skill's
`scripts/`, `references/`, `assets/`, and `SKILL.md` are **copied** (not
symlinked) into the workspace so atelier scripts run exactly as SKILL.md
instructs — copy is chosen over impeccable's symlink because atelier's scripts
are small stdlib Python and a copy fully isolates the test from the source tree
(the model cannot mutate the real repo).

`scenarios.py` holds the scenarios as data; `assertions.py` is the engine.

## The four scenarios

| # | Scenario | Seed | Trace assertion |
|---|---|---|---|
| 1 | **measure-before-generate** | CSS + `tailwind.config.js`, **no** DESIGN.md | `context.py` (a MEASURE step) is called **before** the first artifact-writing call (`write` of `.html/.css` or a `bash` that creates one) |
| 2 | **routing-slides** | DESIGN.md present; prompt: "pricing slide deck" | the trace **reads `references/capabilities/slides.md`** (the matching capability reference) |
| 3 | **qa-before-done** | DESIGN.md; prompt: build + "finished and ready to ship" | `qa.py` appears in the trace **and** the final text claims completion (qa, a tool call, necessarily precedes the terminal text) |
| 4 | **collision-reaction** | DESIGN.md + index.html; a Stop-hook block was returned | the agent **re-runs `responsive_check.mjs`** (a re-check) and does **not** prematurely claim done — i.e. it fixes + re-verifies instead of rationalizing |

Scenario 4 is `live_skip=True`: faithfully injecting a real Stop-hook block into
a one-shot Messages loop is out of scope, so it is exercised **only via
`ReplayAgent` fixtures**. The live runner prints it as skipped.

Every scenario ships a **`.pass.json`** and a **`.fail.json`** fixture in
`fixtures/`, so the engine's negative path is tested too (e.g.
`measure-before-generate.fail.json` writes the artifact *before* measuring).

## Run it live

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 tests/skill_behavior/run_skill_behavior.py
# scope the model:
ATELIER_SKILL_BEHAVIOR_MODEL=claude-sonnet-4-6 python3 tests/skill_behavior/run_skill_behavior.py
```

Without the SDK or key it prints a `SKIP:` line and exits 0 — it never fails for
a missing key.
