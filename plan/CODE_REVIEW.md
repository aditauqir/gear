# Code review: swarm/ (planA-review, 2026-11-07)

**Scope.** I read every module under `swarm/`: game, agents, llm, context, adversary, monitors, runner, runlog, viz, analysis, config and schema. I checked them against `plan/CONTRACTS.md` and `plan/ARCHITECTURE_v2.md`. Line numbers refer to the tree after the `Review:` commits.

**Hard constraint.** Determinism had to be preserved. Every applied change was checked with FakeLLM dry runs of `configs/demo_or_10x50_sim.yaml`:
- three runs: 3 rounds; 6 rounds (covers the cot_control at round 5); and 4 rounds with `game.turn_mode=sequential`;
- each run on a copy of the tree without my change and on the live tree, with output in `/tmp/claude-1000/review/`;
- comparison: `cmp` of every `events.jsonl`, `llm_calls.jsonl` (full prompts) and `snapshots.jsonl`, for both fork branches.

All of them are byte-identical, with one exception: fix #1 (8ebbee7) was approved by the lead to change the prompts, and therefore events, from round 2 on. The scripts are `/tmp/claude-1000/review/{dryrun,mkbase,cmp}.sh`.

**Severity.** `bug-high` = wrong results or aborted runs in realistic use. `bug-low` = latent, rare or cosmetic-in-data. `cleanup` = no behaviour change.

## Summary

| # | Severity | Where | Finding | Status |
|---|---|---|---|---|
| 1 | bug-high | runner/wiring.py:131-142, context/policies.py:92 | Own-action ledger items collided on item_id; the prompt showed one action twice and dropped the other | **fixed** 8ebbee7 (lead-approved; changes prompts, see below) |
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

### 1. Own-action items collide on item_id (bug-high, FIXED 8ebbee7)
**Where.** `LedgerSink.emit` calls `own_action_items(d.agent, round, [d.action], ...)` once per `action_result`, so `n` is always 0. Every own action of a turn gets the item_id `"<agent>:<round>:own_action:0"`. `fit()` then builds `items = {i.item_id: i ...}` (policies.py:92): the dict keeps only the last one, while `sections[*].item_ids` lists the id twice. `to_view` renders the surviving item twice.

**Failure, observed.** In the FakeLLM dry run (6 rounds), the round-4 prompt of sandy_dune contains:
```
- (r3) You posted on the board: Looking for info 6; I have spares.
- (r3) You posted on the board: Looking for info 6; I have spares.
```
Its round-3 `give_key` to fern_beacon is gone, although the log line shows the give happened. Every real run (sim60 included) has this whenever an agent takes 2 actions. Agents lose memory of their own gives and defects.

**Fix (8ebbee7, approved by the lead).** LedgerSink now numbers own actions per (agent, round). Each action of a turn gets its own `...:own_action:<n>`. The same dry-run prompt now shows `You gave fern_beacon your key for info 1` alongside the board post.

**Test.** `tests/runner/test_wiring_review.py::test_ledger_sink_numbers_own_actions_per_turn`. It fails on the old code.

**Runs before 8ebbee7 have this bug.** That covers `or_10x30_sim`, `or_10x30_seq`, the smoke runs, and every other real-engine run made from this codebase before that commit. In those runs, agents' context from round 2 on misrepresents their own 2-action turns. Results from them are not comparable with runs after the fix: the prompts differ, so the LLM cache does not carry over either.

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

# Second pass (overnight, 2026-11-07): new code and data-level invariants

**Scope.** This pass covers code added after 28c79f8:
- board options: post_costs_turn, anonymous, post_skip_rounds;
- reasoning.salvage_truncated;
- OpenRouter reasoning_effort and provider_sort;
- the config_hash change (98cb469);
- infra/grid_driver.py;
- swarm/analysis/grid_stats.py.

It also adds a new checker, `swarm/analysis/invariants.py`, which I ran on every finished grid cell and on the older runs.

## Invariant checker (`python -m swarm.analysis.invariants runs/<run>`)
It replays each game from the events alone and asserts the following.
- **order:** seq is contiguous; slots follow the reshuffled order; each agent has one turn per round; every active agent plays.
- **keys:** keys are conserved. Copies move only by give or steal, and appear only by a mint paired with a correct burn. Every give moves a copy the giver held. Snapshots match the replay.
- **defects:** burn correctness, the lose_need target and the release turn are right, and no agent who has won is burned.
- **scores:** round_end scores, win events and the outcome match the replay.
- **delays:** no agent plays while delayed or skipped.
- **obs:** pinned facts, inbox and board each equal an independent re-derivation. So do the view_log lines: the window, released defects and the victim exclusion.
- **god:** God events appear only in the God branch. Powers match the schedule, K and the budget bookkeeping. Forged messages and overwrites match the ok powers.
- **prompts:** no truth field or intervention id appears, and no banned word in the system prompt. "Your keys" equals the pinned holdings. No system-rendered line shows a key value the agent never held. Every "Your note (round r)" is the agent's own current entry. A replaced original is never re-shown. Each own-action line appears at most as often as the action was done.
- **fork:** the God and no-God branches have identical events, prompts and **responses** before God's first event, so the common random numbers hold. The noise branch has no God events.

Mutation tests are in `tests/analysis/test_invariants.py`: each tampered copy of a FakeLLM run is caught by its check.

**Results**

| Run | Violations |
|---|---|
| grid_oss_sim_k2 (48 games) | **0** |
| grid_oss_sim_k6 (finished, 32 games) | **0** |
| r2_grid_oss_seq_k2 (16 games) | **0** |
| or_oss_10x10_sim, or_concurrent_fork, smoke_sweep_*, fake_sweep_* | 0 |
| or_10x30_sim, or_10x30_seq, or_60x20_sim | 102 each, all `prompts`: an own action shown twice. This is the known pre-8ebbee7 ledger bug (#1); the checker would have caught it |

**Interpretation.** The grid cells are internally consistent. There are no rule violations and no hidden-information leaks. The pre-fork prefixes are byte-identical, including the provider responses, so every god-nogod difference starts at God's first act.

## Findings

| # | Severity | Where | Finding | Status |
|---|---|---|---|---|
| 23 | bug-low (analysis) | analysis/grid_stats.py `boot_ci` | At n=8-16 the percentile bootstrap is too narrow. r2_grid_oss_seq_k2 `lost` gives [-0.125, -0.000] but p=0.25 and t95 [-0.151, +0.026]. `rounds` gives [+0.000, +0.750] from a single non-zero seed of 8. The paper plans to report percentile bootstrap CIs | **mitigated** c544fb0: `t95` is printed next to the bootstrap. Recommendation: report sign-flip p and t95 (or BCa), and never claim significance from the percentile CI alone |
| 24 | bug-low | infra/grid_driver.py `Cell.w_total` | The projection subtracts the shared pre-fork rounds once per extra branch. The noise replica B′ has its own seeds and pays for them, so the projection is about 1% low for 3-branch cells. The uncommitted `free=1` mode by another agent counts only the God branch, so it would under-project by about half if a cell also has a noise replica | open. Another agent has uncommitted edits in this file, so I did not touch it. Fix: subtract `min(branches-1, 1) * shared` |
| 25 | bug-low (latent) | infra/grid_driver.py `attach` | `killpg(getpgid(pid))` without checking that the cell leads its own group. If a cell were started from a shell or wrapper without setsid, the abort would kill the whole group: possibly another cell or the watchdog itself. Today every cell is a group leader (`start_new_session`), confirmed with `ps`, so nothing is wrong now | open. Fix: if `pgid != pid`, `os.kill(pid)` only. Also `kill_group` should `proc.wait()` after SIGKILL |
| 26 | info | config_hash (98cb469) | `run.name` and `n_games` are no longer hashed. Two cells with the same game semantics now share game ids, seeds and cache keys: r2_grid_oss_seq_k2 shares all game ids with the aborted grid_oss_seq_k2. That is intended for resume and control reuse, but a "replicate" must change `run.seed` or `run.replica`; renaming the run does not make it independent | documented |
| 27 | ok | board options | post_costs_turn, anonymous and post_skip_rounds are correct in both turn modes. Skip and wrong-defect delay share `delayed_until_round` via `max`; the resume notice is delivered once. The invariant checker covers skips (delays) and anonymous rendering (obs) | no action |
| 28 | ok | salvage_truncated | Salvage runs only when no complete JSON object decodes. It keeps only complete action objects after `"actions"` (string-aware), and a cut-off last action is dropped. In grid_oss_sim_k2 it fired 8 times in 8,920 turns | no action |
| 29 | ok | grid_stats deltas / health | Δ = god − nogod per seed. The exact sign-flip p includes the identity. Seeds pair across cells by world (`world_seed` depends only on run.seed and game_idx). The unhealthy drop is per seed across all branches. Caveat: health is a post-treatment variable, so report the dropped seeds per branch (k2, k6 and r2 seq: none dropped) | no action |
| 30 | ok | reasoning_effort / provider_sort | They are hashed only when set, which re-keys gpt-oss cells as intended. The cache key itself does not include them; it is safe because they enter game_id via config_hash | no action |

# Sweep validity check (final, after fbba90e)

All results below come from the run logs. The checks cover every run in the final analysis: b2_sweep_base, sweep_start1, sweep_start8 + r3b2_sweep_start8, r3_sweep_start14 + r3b2_sweep_start14, sweep_k1, r3_sweep_k4, sweep_board_off + b2_sweep_board_off, r3_sweep_n5 and sweep_n20.

**1. Invariant checker.** The checker reports 0 violations on every run, using `--base runs/grid_oss_sim_k2` for the cells that reuse G1's control games. The one exception is sweep_n20, whose only flags are in the excluded worlds g04 and g05: crashed games with no events, and the missing pair of g04-god. In every cell that reuses G1's control, the control equals G1's no-God game exactly, except g00, which diverges at r6. That is precisely G1's empty-response break.

**2. End reasons.** No game in the analysed data ended `budget_exceeded` or `error`; there are 147 done games. The re-runs were compared with the originals for every round the original completed, excluding rounds after the original's own uncacheable break: sweep_start14→r3_*, b2_sweep_start8→r3b2_*, b2_sweep_start14→r3b2_*, partial_k4/n5/board_off_0447→r3_*/sweep_board_off/b2_sweep_board_off. In 80 of 80 games the events, prompts and responses are identical.

**3. N=20.** Worlds 4 and 5 are excluded. g04-nogod, g05-god and g05-nogod crashed (`UndefinedError: board_enabled`) with 0 calls; g04-god is unpaired. All 9 done N=20 games share one system prompt and one prompt_set_hash (the pre-change template). The A−B result, n=4, +0.088 [−0.170, +0.345], matches.

**4. B″.** B″ forks exactly at F in 30 of 30 worlds (F = 3/8/14/3 for base/start8/start14/board_off). Before F, events and calls are identical to the control (only run_id and game_start.config_hash differ). At F, all 10 turn prompts are identical, all 10 seeds are new, and 0 of 290 responses are identical to the control. The first action divergence is at r=F in every world.

**5. Spot checks** (recomputed from outcome.json):
- board_off noGod − G1 noGod: −0.200, t95 [−0.333, −0.067], p=0.031, n=6;
- board_off A−N: +0.056 [−0.170, +0.281];
- k1 A−N: −0.104 [−0.213, +0.005], p=0.062;
- start14 A−N: −0.025 [−0.080, +0.030];
- base N−B: +0.054 [−0.050, +0.158].

All of these equal SWEEP_RESULTS.md.

**Leak oracle.** It scanned 28,959 sweep agent requests (= agent calls in all 147 done games) with 0 hits.
