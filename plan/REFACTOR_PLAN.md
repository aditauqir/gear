# Refactor plan (planA-review, 2026-11-07): behaviour-preserving modularity

**Goal.** Iraj asked for "more modular" code. Every step below is behaviour-preserving.

**Hard rules for every step:**
- No public import path changes. Every old name stays importable from its old module, via re-exports.
- No change to CONTRACTS.md interfaces.
- Determinism check before and after each step: byte-identical `events.jsonl`, `llm_calls.jsonl` (prompts) and `snapshots.jsonl` for both fork branches. It runs on three FakeLLM dry runs of `configs/demo_or_10x50_sim.yaml`:
  - simultaneous, 6 rounds (covers fraud and cot_control);
  - sequential, 4 rounds;
  - board options on (`post_costs_turn`, `anonymous`, `post_skip_rounds=2`), 5 rounds.
- Full suite green after each step.

**Process.**
- Work happens in a separate git worktree (`/tmp/claude-1000/review/wt`). Sweep cells launch fresh `swarm.run` processes, so a half-edited file must never sit in the live tree.
- Finished commits are cherry-picked into the main tree, and the check is re-run there against the pre-pick tree.
- Commits are titled `Refactor: ...`.
- Not touched: planA-sweep's files (`infra/sweep*`, `configs/sweep*`, `swarm/analysis/sweep_stats.py`, and its uncommitted edits in `swarm/config.py`, `swarm/llm/openrouter.py`, `swarm/runner/spec.py`, `infra/grid_driver.py`) and planA-viz's `swarm/viz/`.

## Status (applied 2026-11-07, after GRID DONE 03:19)
| Step | Commit | Check |
|---|---|---|
| R1 schema package | 95d3fc7 | 18/18 dry-run files byte-identical (sim, seq, board) |
| R2 game/resolve.py + game/board.py | e4606ba | 18/18 byte-identical; new tests/game/test_resolve.py |
| R3 runner/sinks.py + runner/god_adapter.py | 6073a0e | 18/18 byte-identical |

All three commits were made in the worktree and cherry-picked onto the live tree. The check was then re-run on the live tree, which includes other agents' uncommitted edits: before vs after the pick, 18/18 files are byte-identical. The invariant checker reports 0 violations on the board-options dry run. Full suite: 553 passed. The 1 failure is `tests/viz/test_story.py`, caused by planA-viz's uncommitted `paper_figs.py` edit, not by the refactor. `CONTRACTS.md` still says `swarm/schema.py`; it now means the `swarm/schema/` package (same names).

## Steps to apply

### R1. `swarm/schema.py` becomes a package `swarm/schema/`
Today it is 895 lines in one file. The new modules, one concern each:

| Module | Contents |
|---|---|
| `base.py` | Record, MutableState, the id aliases, GOD/SYSTEM, MemoryKind, Phase |
| `timing.py` | turn_index, log_visible, defect_release_turn, release_visible (the CONTRACTS §2 timing contract) |
| `state.py` | the truth side: KeyCopy, AgentState, Message, Taint, MemoryEntry, ActionRecord, Notice, GameState |
| `views.py` | the agent-visible side: AgentView and subclasses, TRUTH_FIELDS |
| `actions.py` | agent actions and adapters, AgentOutput, God actions |
| `context.py` | HistoryItem, ContextSection, ContextBundle, CompactionRecord |
| `llm_io.py` | ChatMessage, CallMeta, ChatRequest, Usage, ChatResponse, LLMCall |
| `events.py` | payloads, EventData, EventBody, Event, make_event, EventSink, MemorySink, Snapshot |
| `labels.py` | Label, MonitorScore |
| `jsonl.py` | the JSONL helpers |

`swarm/schema/__init__.py` re-exports every public name of the old module. `import swarm.schema as S` and every `from swarm.schema import X` keep working. The truth side and the agent-visible side now live in separate files, so the leak boundary is visible in the file tree.

### R2. Engine: turn resolution separated from the loop and from event emission
- New `swarm/game/resolve.py` holds `resolve_turn(state, agent, actions, grep, cfg) -> TurnResolution(events, results)`. It covers the whole action loop: the free grep, `post_costs_turn` blocking, the action limit, simultaneous conflict notices and the `post_skip_rounds` skip. It mutates state like `rules.apply` and returns the event bodies in the same order the engine emits them today.
- New `swarm/game/board.py` holds the board-option helpers and their notice texts.
- The engine keeps the loop, observation, the act() calls, memory writes, ledgers and emission.
- `rules._notice` becomes the public `rules.notice` (the old name is kept as an alias). Old engine names (`BOARD_WHOLE_TURN`, `_whole_turn_text`, `_conflict_text`) are re-exported.

### R3. `swarm/runner/wiring.py` is split by role
| Module | Contents |
|---|---|
| `runner/sinks.py` | LedgerSink, ProgressSink, OracleClient (event and request wrappers) |
| `runner/god_adapter.py` | _SlotGod, make_god_hook, check_schedule (the HookGod timing adapter) |
| `wiring.py` | client building, make_decide, _play_real, plus re-exports of everything above |

## Proposed but NOT applied (behaviour change, or files owned by others)
- **R4. LLM budget layer.** Move RunBudget, GlobalLedger and estimate_cost into `swarm/llm/budget.py` (re-exported from openrouter.py). Build ONE RunBudget and GlobalLedger per run in `build_clients` (fixes CODE_REVIEW #9), and record failed-attempt estimates (#8). Blocked: `openrouter.py` has uncommitted edits by planA-sweep, and #8/#9 change spend accounting.
- **R5. One ledger builder.** The engine's `ledgers` and `wiring.LedgerSink` duplicate each other (#20). Pass LLMAgents to the engine as a TurnAgent mapping and delete `make_decide`/DecideAgent from the real path. This also emits `prompt_hash` and `context_built` (#5). It changes events.jsonl, so it needs a lead decision.
- **R6. Config hashing.** Move `config_hash` and the HASH_OPERATIONAL table out of `config.py` into `swarm/config_hash.py`. Blocked: `config.py` has uncommitted edits by others.
- **R7. Synth engine** (#21). Re-implement synth on top of `game.rules`, or delete it. It changes synth outputs.
