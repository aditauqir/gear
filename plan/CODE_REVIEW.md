# Code review: swarm/ (planA-review, 2026-11-07)

**Scope.** I read every module under `swarm/`: game, agents, llm, context, adversary, monitors, runner, runlog, viz, analysis, config and schema. I checked them against `plan/CONTRACTS.md` and `plan/ARCHITECTURE_v2.md`. Line numbers refer to the tree after the `Review:` commits.

**Hard constraint.** Determinism had to be preserved. Every applied change was checked with FakeLLM dry runs of `configs/demo_or_10x50_sim.yaml`:
- three runs: 3 rounds; 6 rounds (covers the cot_control at round 5); and 4 rounds with `game.turn_mode=sequential`;
- each run on a copy of the tree without my change and on the live tree, with output in `/tmp/claude-1000/review/`;
- comparison: `cmp` of every `events.jsonl`, `llm_calls.jsonl` (full prompts) and `snapshots.jsonl`, for both fork branches.

All of them are byte-identical. The scripts are `/tmp/claude-1000/review/{dryrun,mkbase,cmp}.sh`.

**Severity.** `bug-high` = wrong results or aborted runs in realistic use. `bug-low` = latent, rare or cosmetic-in-data. `cleanup` = no behaviour change.

## Summary

| # | Severity | Where | Finding | Status |
|---|---|---|---|---|
| 1 | bug-high | runner/wiring.py:133, context/policies.py:92 | Own-action ledger items collide on item_id; the prompt shows one action twice and drops the other | **open** (changes prompt text; lead decision) |
| 2 | bug-high | context/leak_oracle.py:169 | `original_text` canary matched the bare note text; a repeated note or a DM aborted the game with TruthLeak | **fixed** d5b7eb5 |
| 3 | bug-high | game/engine.py:120 (was `asyncio.gather`) | Simultaneous mode: when one act() raised (BudgetExceeded), the other LLM calls kept running and spending after game_end, and logged into a closed GameWriter | **fixed** 43bf2f2 |
| 4 | bug-low | runner/wiring.py:261 | ScriptedGod `after_turns>0` in simultaneous mode (and `after_turns>=n_agents`) never fired, silently | **fixed** c2f4a3d (fail fast) |
| 5 | bug-low | game/engine.py:324 + runner/wiring.py:225 | Real runs log `turn.prompt_hash/prompt_set_hash = null` and emit no `context_built` events | open (changes events.jsonl) |
| 6 | bug-low (design) | config.py:313 `config_hash` | Hash covers operational knobs (cache path, out_dir, global_cap_usd, concurrency, retry, n_games, name). The uncommitted cap default 2→6 changes demo.yaml's hash, so its game ids, seeds and cache keys change too | open (recommendation) |
| 7 | bug-low | game/engine.py:174 vs 288 | Two God stamping conventions: GodLike stamps the wake slot, HookGod (the real path) stamps slot-1. In simultaneous mode a forged DM therefore shows the same round in real runs and the next round with `god=` | open (doc/contract) |
| 8 | bug-low | llm/openai_compat.py:207-226, 277 | One budget reservation covers all retries; a timed-out POST may still be billed but records 0 | open (llm/ is off-limits now) |
| 9 | bug-low | runner/wiring.py:62-67 | `RunBudget` and `GlobalLedger` are built per client: an agent model and a god model give two per-run caps; reservations are per process | open (latent: LLMGod is a stub) |
| 10 | bug-low | llm/openrouter.py:71-123 | GlobalLedger reservations are in-memory only, so concurrent processes (e.g. sim60 plus another run) can overshoot the global cap by their in-flight estimates | open |
| 11 | bug-low | game/engine.py:491, runner/run.py:59,117 | BudgetExceeded is caught inside the engine, so the game and the run report `status=done`. The `budget_exceeded` run status is dead code, and a partial round gets no round_end or snapshot | open |
| 12 | bug-low | game/rules.py:170 | `apply` turns KeyError/ValueError/IndexError into a failed action. An engine bug becomes silent, and the state may be partially mutated, which contradicts "state unchanged" | open |
| 13 | bug-low | adversary/powers.py:142 | cot_control uses `action.mode` without checking `god.powers.cot_control.mode` (an LLM God could append when the config says replace) | open (latent) |
| 14 | bug-low | llm/openai_compat.py:250 | Single-flight: which fork branch "leads" is a race, so `cache_hit` and latency in llm_calls.jsonl are not reproducible. events.jsonl is unaffected | informational |
| 15 | cleanup | runner/wiring.py | `run_round` monkeypatch for snapshots replaced by `GameEngine(on_snapshot=sink.snapshot)` | **done** c2f4a3d |
| 16 | cleanup | runlog/llmlog.py | Duplicate `cache_key` recipe; now re-exported from llm/cache.py | **done** 93ea9b3 |
| 17 | cleanup | adversary/scripted_god.py:50 | `open_needs` shadowed `rules.open_needs` with different semantics (it excludes held keys); renamed `missing_needs` | **done** 93ea9b3 |
| 18 | cleanup | game/rules.py:117 | `deliver_message` doc claimed God's fraud uses it; it does not (and adds no ActionRecord) | **done** 93ea9b3 |
| 19 | cleanup | game/engine.py | `run_round` split into `_play_sequential` / `_play_simultaneous`; `ledgers or {}` replaced by fill-in-place (a caller's empty dict was dropped) | **done** 43bf2f2 |
| 20 | cleanup | engine ledgers vs wiring.LedgerSink | Two ledger builders. The engine's is unused in the real path (DecideAgent ignores it). The memory views are duplicated too (`make_decide` uses `obs.round-1` for cot, the engine `st.round`) | open |
| 21 | cleanup | runner/synth.py | A second, independent implementation of the game rules, so it can drift from game/rules.py | open |
| 22 | cleanup | small | `engine.py:482` `max_rounds or` (0 becomes the default); `BOARD_WHOLE_TURN` defined after use; `ProgressSink._lines` class-level state shared across runs; `rules._key_value` returns 0 when no copy exists (unreachable); `LLMAgent` seeds use game_id, not game_idx as CONTRACTS §4 says (intentional for forks; doc drift) | open |

## Bugs in detail

### 1. Own-action items collide on item_id (bug-high, OPEN)
**Where.** `LedgerSink.emit` calls `own_action_items(d.agent, round, [d.action], ...)` once per `action_result`, so `n` is always 0. Every own action of a turn gets the item_id `"<agent>:<round>:own_action:0"`. `fit()` then builds `items = {i.item_id: i ...}` (policies.py:92): the dict keeps only the last one, while `sections[*].item_ids` lists the id twice. `to_view` renders the surviving item twice.

**Failure, observed.** In the FakeLLM dry run (6 rounds), the round-4 prompt of sandy_dune contains:
```
- (r3) You posted on the board: Looking for info 6; I have spares.
- (r3) You posted on the board: Looking for info 6; I have spares.
```
Its round-3 `give_key` to fern_beacon is gone, although the log line shows the give happened. Every real run (sim60 included) has this whenever an agent takes 2 actions. Agents lose memory of their own gives and defects.

**Fix.** Number own actions per (agent, round) in LedgerSink, e.g. `n = sum(1 for it in ledger if it.round == r and it.kind == "own_action")`, then build the item with that `n`. A simpler alternative: emit the turn's own actions as one batch at the end of `_resolve`.

**Why not applied.** The fix changes the prompt text from round 2 on. The task's hard constraint says prompts must stay byte-identical. Needs the lead's call.

### 2. Leak-oracle false positive aborts games (bug-high, FIXED d5b7eb5)
**Before.** A `replace` memory_overwrite added the bare old note text as a canary for every later prompt. LLM agents often repeat a note ("Plan: trade with X for info 4"). If God replaced round r-1 (the ScriptedGod default `round: prev`) and the same text was still shown as round r-2's note, or the agent had sent it in a DM, `assert_clean` raised `TruthLeak`. The game then ended as `error`, and the fork pair was broken.

**Fix.** The needle is now `"(round r): <old text>"`, matching how `memory_items` renders that round's entry. Re-showing the replaced entry is still caught: the existing tests pass unchanged.

**Test.** `tests/context/test_leak_oracle.py::test_original_text_canary_is_scoped_to_its_round`. It fails on the old code.

### 3. Orphaned agent turns after an exception in simultaneous mode (bug-high, FIXED 43bf2f2)
**Before.** `asyncio.gather` does not cancel siblings. The budget reservation happens before the concurrency semaphore, so all N agents' calls are reserved and queued. When one raised `BudgetExceeded`, the engine ended the game while the other calls kept running and spending. They then logged to a closed `GameWriter` (ValueError, "Task exception was never retrieved"). AuthError and TruthLeak had the same problem.

**Fix.** `_gather_or_cancel` creates the tasks in the same order as gather, and on any exception cancels them and awaits them. The happy path is unchanged: the dry runs are identical.

**Test.** `tests/game/test_engine_review.py::test_simultaneous_failure_cancels_sibling_turns`.

### 4. Silent no-op God schedule (bug-low, FIXED c2f4a3d)
The real engine consults God before slot 0 only in simultaneous mode, and before slots 0..n-1 in sequential mode. So `after_turns>0` (simultaneous) or `after_turns>=n_agents` never fired, and the run silently had no intervention.

**Fix.** `wiring.check_schedule` raises ValueError at game start. No existing config is affected. `round < start_round` stays allowed because it is documented.

**Test.** `tests/runner/test_wiring_review.py`.

### 5. Missing prompt hashes and context_built events in real runs (bug-low, OPEN)
`_play_real` passes a `decide` function, so the engine wraps it in one shared `DecideAgent`, which has no `.last`. `_emit_turn` therefore logs `prompt_hash=None` and `prompt_set_hash=None` and never emits `context_built`. This was confirmed in the dry-run events. As a result, prompt provenance per turn and context token accounting are absent from every real run.

**Fix.** Pass the `LLMAgent`s to `GameEngine` as a mapping, so `TurnAgent` and the engine's own ledger, grep and memory are used. The other option is to forward `agents[a].last` through DecideAgent. Either one adds fields and events to events.jsonl, so it is not applied.

### 6. config_hash covers operational knobs (bug-low/design, OPEN)
`config_hash()` dumps the whole config. That includes `llm.cache.path`, `run.out_dir`, `run.name`, `run.n_games`, `run.max_concurrency_games`, `llm.retry.*`, `llm.openrouter.global_cap_usd`, `max_concurrency` and the prices.

**Concrete case.** The uncommitted default change `global_cap_usd: 2.0 -> 6.0` in config.py and base.yaml changes the hash of configs/demo.yaml (`e657c252cf92` -> `ed06e5589ee7`). That gives new game ids, new agent seeds and a cold LLM cache for any config that does not pin the cap. The demo_or_* configs pin 2.0 or 6.0, so they are unaffected.

**Fix (later, deliberately).** Hash only semantic sections (`game`, `reasoning`, `roles`, `god`, `context`, `run.seed/branch/replica`), using the same trick as `game.board`, so existing hashes are kept where possible. Until then, treat any edit to an llm/run default as a hash change.

### 7. Two God-stamp conventions (bug-low, OPEN)
- GodLike (`god=`): `_god` sets `turn_index=slot`, so forged DMs are visible at observations after the slot.
- HookGod (the real path, via `_SlotGod`): stamps `slot-1`, so a forged DM is visible to the agent playing that slot. In simultaneous mode it is visible the same round, versus the next round with `god=`.

Both conventions are indistinguishable to agents. However, CONTRACTS §2 ("stamped with the turn index of the God wake slot") matches only one of them, and the two paths differ by one round in simultaneous mode. Pick one and document it.

### 8-10. Budget enforcement holes (bug-low, OPEN; swarm/llm budget code left to planA-sim60)
- **(8)** The retry loop reuses one reservation. Timeouts or 5xx after the provider has generated may be billed but are recorded at 0. **Fix:** record the estimate (or the provider cost) for failed attempts.
- **(9)** `_build_client` builds a fresh `RunBudget` and `GlobalLedger` per (backend, model). If roles use two models, the per-run cap doubles. **Fix:** build them once per run in `build_clients` and pass them to every client.
- **(10)** The in-process `reserved` field is invisible to other processes. **Fix:** write the reservations to the ledger file (a reserve line, then a settle line), or accept the documented overshoot bound of concurrency × estimate per process.

### 11. Budget stop hidden in status (bug-low, OPEN)
`GameEngine.run` swallows BudgetExceeded, so `_run_one` marks the game `done`. The manifest's `budget_exceeded` run status can never occur, and only `end_reason` tells the truth. The partially played round has no `round_end` or snapshot.

**Fix.** In `_run_one`, map `outcome.end_reason == "budget_exceeded"` to `status="budget_exceeded"`, and emit a round_end for the partial round.

### 12. rules.apply swallows internal errors (bug-low, OPEN)
`except (KeyError, ValueError, IndexError)` hides engine bugs as `error:KeyError` action failures. `_defect` mutates several fields in sequence, so a mid-way exception leaves a partial state.

**Fix.** Re-raise under tests (an env flag), or validate before mutating. At minimum, log the exception.

### 13. cot_control mode not checked against config (bug-low, OPEN)
`apply_cot_control` honours `action.mode`. ScriptedGod defaults it from config, but an LLM God could pass `append` while `god.powers.cot_control.mode=replace`.

**Fix.** Fail with `mode_disabled` when `action.mode != pcfg.mode`, or document that mode is a per-action choice.

## Checked and found OK
- **Hidden information.** observe/view_log/grep_log build AgentViews field by field. Holdings are own-only. Key values reach only the receiver of a gift or mint. Defect lines respect release, victim and identity rules, and wrong defects follow the same path. A forged DM is indistinguishable from a real one (same msg_id scheme, no round in AgentMessageView, inbox order by append), and the anonymous board covers view, log and grep. The system prompt has no agent name, round or God words (tested). Truth fields never reach templates (`_check_ctx`).
- **Timing.** Each record is shown exactly once (`prev <= stamp < t`, `release_visible`). Simultaneous-mode windows and delays match CONTRACTS §2.
- **Simultaneous resolution.** Priority order is `st.order` (reshuffled by seed). Conflicts fail with a notice, and winners become untargetable mid-resolution.
- **Determinism.** Every RNG is derived (`make_rng` or `derive_seed`); there is no hash(), wall clock or launch order in logged content. Repeated dry runs are byte-identical.
- **Fork runner.** CURRENT_GAME is per task. The single-flight leader's failure falls back to the follower's own call. Fork A and B share game_id, so they share seeds and cache keys by design.
