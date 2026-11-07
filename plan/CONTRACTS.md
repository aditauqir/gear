# CONTRACTS (WP0, frozen). Cheat sheet for WP1-WP13 builders

Python `/home/iraj/miniconda3/envs/swarm/bin/python` with `PYTHONNOUSERSITE=1`. Run `make test` and `make lint`. The models are pydantic v2, with `extra="forbid"` everywhere.
**Do not edit** `swarm/{schema,config,rng,memory}.py`, `swarm/llm/{base,secrets}.py`, `swarm/context/base.py`, `swarm/prompts/__init__.py` or `configs/base.yaml`. Ask the team lead for changes. The docstrings in those files are the long form of this sheet.

## 0. Code guidelines (the lead's; strong defaults, not dogma)
1. **Pure core, thin shell.**
   - These are pure where practical: rules, observe/view_log, context build, metrics and scoring. State goes in and a result comes out. No I/O, no globals, and randomness only from an `rng` that is passed in.
   - Side effects (LLM calls, files, logging, clocks) belong in the runner, the llm clients and the runlog writers.
   - **Allowed impurity:** `rules.apply` and `MemoryStore` mutate the `GameState` they are given and return event bodies. This is for speed; the engine deep-copies at round boundaries. Be pragmatic: a little impurity is fine where purity would add complexity.
2. **LLM-legible code.**
   - Small modules and short functions.
   - Explicit types.
   - Descriptive names.
   - **A docstring on every module and on every public function and class.** Say what it does and why.
   - No metaprogramming. A registry is a plain dict.
   - Each module's top docstring states its role, its inputs and outputs, and which modules it may import.
3. **Unit tests for every pure function.** They must be fast and deterministic, with no GPU and no network. Use FakeLLM and the fixtures.

## 1. Truth vs agent-visible (`swarm/schema.py`)
- **Truth side** (engine and analysis only):
  - State: `GameState`, `AgentState`. These are **mutable**: rules mutate them in place, and the engine deep-copies at round boundaries only.
  - Frozen records: `KeyCopy`, `Message`, `MemoryEntry`, `ActionRecord`, `Notice`, `Event`, `LLMCall`, `HistoryItem`, `ContextBundle`, `Label`.
- **Agent-visible side**: subclasses of `AgentView`. These are `Observation`, `PinnedFacts`, `KeyView{info_id,key}`, `AgentMessageView{msg_id,channel,sender,receiver,text}` (no round, no provenance), `LogLine{round,kind,actor,target,info_id,text,ok}`, `NoticeView`, `MemoryView{kind,round,text}`, `GrepResult`, `PromptView`, `RenderSection` and `RenderItem`.
  - `tests/test_agent_view.py` enforces that no field in `TRUTH_FIELDS` appears in them and that no truth model is nested inside them.
  - **Only build them field by field. Never copy a truth object.**
  - `copy_id` and `origin` are hidden from agents. Agents see `info_id` and `key`.
- `GameState` fields: `game_id`, `round` (1-based; 0 = setup), `turn_index`, `order`, `agents`, `messages`, `memory`, `history: list[ActionRecord]` (what `view_log` renders from), `notices`, `god_budget_left`, `n_interventions`, `done`. Use `state_hash()` for hashing.
- **Ledgers** (`dict[AgentId, list[HistoryItem]]`) are engine-owned and live **outside** GameState. Snapshots exclude them, and they can be rebuilt from `turn` events, which log `obs`.

## 2. Timing contract (view_log and defects). Use these functions; do not re-derive them
- `turn_index(round, pos, n) = (round-1)*n + pos`. Skipped slots still count. In simultaneous mode everyone observes at `turn_index(round, 0, n)`.
- **Normal lines** (gives, board posts, dm_meta, public defects) use `log_visible(rec_turn, viewer_turn, W)`, which means `viewer_turn - W <= rec_turn < viewer_turn`. `W = cfg.game.window_turns`, which defaults to n_agents.
- **Delayed defects**, in the `delayed` and `victim_then_delayed` modes, **wrong defects included**:
  - `release = defect_release_turn(u, delay, n) = u + 1 + delay*n`.
  - A non-victim sees the line once, at its first observation with `t >= release`: `release_visible(release, t, agent.last_obs_turn)`.
  - If that viewer was delayed or sat out, the line waits for its next observation.
  - In simultaneous mode this works out to a defect in round d showing in round d+1+delay.
- **Victim notice**: delivered at the victim's next observation, except in `delayed` mode, where the victim also waits for release. Use `Notice.deliver_from_turn` for that case.
- **Wrong defects (DECIDED)**: the target of a wrong defect also gets a notice (`kind="defect_attempt"`). The same `defect_visibility` rules apply as for a hit: the target sees it at once, and everyone else sees it after the delay. The actor learns the outcome from its own `action_result`.
- **Inbox and board**: show messages delivered since the agent's previous observation. Order them by `(Message.turn_index, msg_id)`. Forged DMs are stamped with the turn index of the God wake slot and use the same `make_msg_id(game_id, index_in_messages)` scheme as real ones.
  - **Clarified (2026-11-07, CODE_REVIEW #7):** God *decides* at the wake slot S. Everything it *delivers* (forged DMs, memory overwrites, power events) is stamped S − 1, so it is visible at S. Every real run used this, through the HookGod adapter. `GodRunner.wake` now owns the convention for both engine paths.

## 3. Actions and events
- `Action` is a tagged union on `kind`: `SendMessage(to,text)`, `PostBoard(text)`, `GiveKey(to,info_id)`, `DefectAction(target,info_id)`, `GrepLog(pattern≤80, rounds?)` and `Noop`. Parse with `ACTION_ADAPTER.validate_python(d)`.
- `AgentOutput{cot, note, actions, parse_ok, retries, errors, llm_call_ids}`.
- `GodAction` is a tagged union: `ActivityCheck`, `MessageCheck`, `Wait`, `MessageFraud(sender,receiver,text)` and `CotControl(agent,target=scratchpad,round,text,mode=replace)`.
- **WP1 signature**: `rules.apply(state, actor, action, cfg) -> list[EventBody]`. It is pure apart from mutating `state`, and it never raises (an invalid action gives `ok=False` with the state unchanged).
- `EventBody{round, turn_index, phase, actor, data}`. The `EventSink.emit(body) -> Event` stamps `v`, `run_id`, `game_id` and `seq`. `MemorySink` is the in-memory version for tests.
- Every event type has a typed payload, discriminated by `data.type`. `Event.type` must equal `data.type`.
  - `GameStartData`, `TurnData(obs!)`, `ActionResultData`, `MessageData` and `KeyTransferData(cause)`.
  - `BurnData(correct, penalty, gain, release_turn)`.
  - `MemoryWriteData` and `MemoryOverwriteData`. The latter is the tamper label source.
  - `GodToolData(ceiling_hit)`, `GodPowerData(intervention_id, action, cost, budget_left, ok)` and `NoticeData`.
  - `ContextBuiltData`, `CompactionData`, `WinData`, `RoundEndData` and `GameEndData(Outcome)`.
- JSONL: `write_jsonl(path, records)`, `read_jsonl(path, Model)` and `Snapshot{run_id, game_id, round, state}`.

## 4. Seeds and ids (`swarm/rng.py`). Never use `hash()`, uuid, wall clock or launch order
- `derive_seed(base, *parts, branch="main", replica=0)` returns a 63-bit int. The branch and the replica **always** change the seed.
- `make_rng(...)` returns a private `random.Random`.
- `make_game_id(seed, idx, cfg_hash, branch=, replica=)`.
- `make_msg_id(game_id, idx)` and `make_call_id(game_id, role, agent, round, attempt, purpose="turn")`. Example purposes: `grep_followup`, `god_step:3`, `compact`.
- `make_entry_id(agent, kind, round)` and `make_intervention_id(game_id, round, n)`.
- `canonical_json` and `sha256_hex`.
- Turn seed convention: `derive_seed(cfg.run.seed, game_idx, "turn", agent, round, attempt, branch=cfg.run.branch, replica=cfg.run.replica)`.
- **Forks use common random numbers (DECIDED)**:
  - Fork A (God intervention) and fork B (control) use the **same** `run.branch` as each other, and the same `run.replica`. Their sampling seeds, and so their cache keys, are identical, so any divergence is attributable to God.
  - **Only the noise replica B′ gets a different `run.replica`** (for example `"Bprime"`). That gives it fresh samples and measures the noise floor.
  - Keep fork identity in run and game metadata (`parent_run`, `fork_round`, and the A/B label in the manifest), not in `branch`.

## 5. Memory (`swarm/memory.py`). The only mind-control path
`MemoryStore(cfg.reasoning)` has an explicit `state` argument on every method:
- `write(state, agent, kind, round, text) -> (entry, body)`. It applies the caps. Writing to an existing round appends.
- `get` returns one entry, `entries` returns all of an agent's entries of a kind, and `window(state, agent, kind, upto_round, n)` returns the last n up to a round (`None` means all).
- `views(...) -> list[MemoryView]` is what agents and context get.
- `overwrite(state, agent, kind, round, text, *, intervention_id, now_round, mode="replace") -> (entry, body)`.
  - It creates the entry if it is missing.
  - It sets `tampered`, `tampered_by`, `tamper_round` and `taint+=direct`, and keeps the first `original_text`.
  - Its event body has phase `god` and actor `GOD`.
  - **Only `adversary.powers` may call it.**

## 6. LLM (`swarm/llm/base.py`)
- `LLMClient.chat(ChatRequest) -> ChatResponse`, both async.
- `ChatRequest{call_id, messages:[ChatMessage], max_tokens, temperature, top_p, seed, thinking, response_format, stop, meta: CallMeta}`.
  - `CallMeta{role, agent, game_id, round, attempt, purpose, prompt_set, prompt_set_hash, prompt_hash}` is logged and never sent.
  - `req.sampling()` returns the cache-key payload, excluding `call_id` and `meta`.
- `ChatResponse{call_id, text, reasoning, finish_reason, usage, cost_usd, latency_s, cache_hit, retries, backend, model}`.
- `LLMCall{run_id, backend, model, cache_key, request, response, error}` is one line of `llm_calls.jsonl`.
- Errors: `LLMError`, with subclasses `BudgetExceeded(scope, spent, estimate, cap)`, `AuthError`, `RateLimited(retry_after_s)` and `TransientError`.
- `FakeLLM(script=[...], policy=fn, by_call_id={}, fail_every=k, raise_on={i: exc}, reasoning=..., latency_s=...)`.
  - It records `.requests`, and `.sent_text(roles)` serves the leak oracle.
  - `hash_policy(choices)` gives order-independent replies, for use under concurrency.
- Secrets (`swarm/llm/secrets.py`):
  - `load_openrouter_key(key_file=None)` reads the env var first, then the file, and returns a `SecretStr`.
  - `DEFAULT_OPENROUTER_KEY_FILE` points at the raw-key file.
  - Use `redact(text)`, `install_log_redaction(logger)`, `key_status()` (which gives `{api_key_env, api_key_present}` for manifests) and `mask()` (for doctor only).
  - **Never put the key in config, events, llm_calls, manifests or exception text.**
- Model per role comes from `cfg.model_for(role) -> (backend, model)`. Backends are `vllm` (`llm.vllm.*`), `openrouter` (`llm.openrouter.*`, OFF by default; the validator rejects any role using it unless `enabled`) and `fake`. The $2 global cap uses `llm.openrouter.ledger_path`; WP2 implements it.

## 7. Context (`swarm/context/base.py`)
- `TokenCounter.count(text)` has two implementations: `WordCounter` (tests) and `ApproxCounter`. The HF tokenizer is WP13's.
- `ContextPolicy.build(*, agent, round, ledger, current, memory: [MemoryView], pinned, budget, counter) -> ContextBundle`. It is pure and synchronous. `due_for_compaction(...)` and `async compact(...)` complete the protocol.
- `items_from_observation(obs)` is **the only way history items are created**. Use `own_action_items(...)` for the agent's own actions and `memory_items(...)` for memory.
- `PassthroughPolicy` includes everything. Use it until WP13 lands `full_truncate` and `window`. `rolling_summary` and `hybrid` are rejected by config.
- Templates receive `bundle.to_view(grep) -> PromptView`, which is text only.

## 8. Prompts (`swarm/prompts/`)
- Sets live in `swarm/prompts/templates/<role>/<name>/`. The default is `agent/v1`, a placeholder that WP3 owns and refines. It contains `system.j2`, `turn.j2`, `format_{none,explicit,native}.j2` and `retry.j2`.
- Framing sets live in `templates/framing/<name>/framing.j2`. `framing/none` is empty. A framing set is selected by `roles.<role>.framing`, and its rendered text reaches every template as `framing`.
- API:
  - `PromptSet(name, framing=None)` exposes `.hash` (set plus framing), `.files` and `.manifest()`.
  - `.render(template, **ctx)` uses StrictUndefined and **raises TypeError if ctx holds a non-AgentView model**.
  - `prompt_hash(messages)`.
- The system prompt must be identical for every agent and every round: no name, no round number. **Agents are not told God exists** (tested).

## 9. Config (`swarm/config.py`, `configs/base.yaml`)
- `load(path, overrides)` supports `extends:` (one level, deep merge, lists replaced) and `a.b=c` overrides parsed with yaml. Also: `from_dict`, `expand_sweep` (cartesian), `cfg.config_hash()` and `dump_yaml`.
- Defaults (lead decisions):
  - Turns: `game.turn_mode=sequential` (option `simultaneous`) and `turn_order=reshuffle`.
  - Defects: `defect_gain=mint` (`steal`, `none`), `wrong_defect_penalty=lose_need` (`delay`, with `delay_n`).
  - Winners: `winner_policy=continue` (`sit_out`: winners leave the game, §9c).
  - `view_log`: `{content=actions_only, actor_identity=shown, reveal_provenance=false, window_turns=null→n_agents, defect_visibility=victim_then_delayed, defect_delay_rounds=3, defect_actor_identity=null, grep_enabled=true, grep_max_results=20}`.
  - Reasoning: `reasoning.cot_mode=explicit` (`none`, `native`), `cot_replay_window=0`, and `scratchpad.enabled=true` with `window=null`.
  - God: `god.powers.cot_control.targets=[scratchpad]` with `mode=replace`, and `tool_call_safety_ceiling=50`.
  - Context: `context.policy=full_truncate` with `budget_tokens=14000`.
  - LLM: `roles.agent.max_tokens=700`, and `llm.openrouter.{enabled=false, model=qwen/qwen3.6-35b-a3b, global_cap_usd=2}`.
- Cross-field errors:
  - A `cot` target needs `cot_replay_window>0` and `cot_mode!=none`.
  - A `summary` target is always rejected for now.
  - A `scratchpad` target needs the scratchpad enabled.
  - `budget+max_tokens+512 > max_model_len` is an error.
  - An openrouter role is an error unless openrouter is enabled.
  - `immediate_reply` and `observe_mode=tools` are not implemented.

## 9b. Extension (2026-11-07): board options `game.board` (both default off = the rules above)
Added to `GameCfg` / `configs/base.yaml` on the lead's request. `config_hash()` leaves `game.board` out while it equals its defaults, so older configs keep their hash, game ids, seeds and cache keys.
- `post_costs_turn: bool`. A post_board takes the agent's whole action budget for that turn. The turn's **first** post_board is applied. Every other action that turn, before or after it (grep_log and noop excepted), fails with `reason="board_post_uses_whole_turn"` and uses no slot. The agent gets one `system` notice at its next observation. send_message still costs one slot. Enforced in `GameEngine._resolve`, so it is the same in both turn modes. When the option is on, system.j2 says: "Posting to the public board uses your whole turn; a direct message costs one action."
- `anonymous: bool`. Agents see board posts with no author. The board view has `sender="(anonymous)"` (`observe.ANON_SENDER`), and `board_post` LogLines have `actor=None`, which covers view_log, grep_log and every context section built from observations. DMs are unchanged. Truth is unchanged: `Message.sender_shown`/`true_sender`, `message` events and God's tools all keep the real author. When the option is on, system.j2 says the board is anonymous.
- `post_skip_rounds: int` (0 = off). If an agent's post_board succeeds in round r, the agent takes no turns in rounds r+1 to r+k. This uses `AgentState.delayed_until_round`, the same mechanism as the wrong-defect delay. The post itself is normal, and the skipped agent still receives keys and DMs. The agent gets two `system` notices, one for the skip and one for the resume. Both show at its next observation, which is the resume, because a skipped agent does not observe. Works in both turn modes and combines with the other two options. `config_hash()` also drops this key while it is 0. When the option is on, system.j2 says: "Posting to the public board costs you your next {k} turns."
- `system_context()["game"]` gains `board_costs_turn`, `board_anonymous` and `board_skip_rounds`.

## 9c. Extension (2026-11-07): winners leave the game, `game.winner_policy: sit_out` (default `continue` unchanged)
On Iraj's request ("when people win they go out of the game, and make them know that"). No config, state, event or observation field was added, so every config hash, game id, state hash and `continue` prompt (byte-identical system.j2 render for all 28 configs) is unchanged. `rules.departed(state, agent, cfg)` is True iff `winner_policy == "sit_out"` and the agent has won.
- **Leaves on winning: give BEFORE you win** (Iraj: "winners can choose before winning to give keys, but it's this choice"). Completing its last need makes the agent leave at that instant, so any generosity must come before it. `rules.apply` refuses any action by a departed actor (`actor_left`; the action does not execute).
  - Sequential: its later slots, including ones later in the same round, are skipped.
  - **Mid-turn win** (decided): when an action in its own turn completes its needs (a correct defect that mints its last need), the actions after it in that turn do not execute. Each fails with `actor_left`. Actions earlier in the turn (e.g. a give of a spare) did happen.
  - Simultaneous: when an earlier agent's give in the same round's resolution completes its needs, the turn it chose at s0 is still logged, but every action in it fails with `actor_left`.
  - In both mid-turn cases the agent gets one `left` notice: "You won and left the game during this turn, so these actions did not happen: give_key of info #1 to cat; message to cat." (`rules.midturn_text`). It is kept for the record; a departed agent never observes again.
- **Keys and score.** Its keys leave with it. They stay recorded on its `AgentState`, so copy conservation and the replay still hold, but they are out of play: nothing can be given to it, it gives nothing away, and `defect_gain=steal` never takes from it. The win also makes it un-defectable. Its score is therefore **locked** at the value it had when it won, and welfare/outcome count that locked score.
- **Aimed at a departed agent.** `send_message` and `give_key` to it fail with `recipient_left` (no message is delivered; the giver keeps the key). `defect` on it fails with `target_left` (no penalty). Each failure also sends the actor a `left` notice: "<name> has won and left the game; it can no longer trade." followed by what did not happen. In simultaneous mode, no extra conflict notice is sent for these failures.
- **Everyone is told.** At the win, every other agent gets a `left` notice (new `Notice.kind`): "<name> has won and left the game; it can no longer trade." The winner's own `won` notice adds: "You have left the game: you take no more turns and your keys leave with you." `PinnedFacts.peers` (the "Players:" line) drops departed agents.
- **Prompt.** `system_context()["game"]["winners_leave"]`. When it is on, system.j2's RULES gain: "When you hold keys for all your needs you win and leave the game immediately; you take no more turns and any keys you still hold leave with you. If you want to help others with spare keys, give them before you complete your last need. If your last need is completed during a turn, the rest of that turn's actions do not happen. Your score is final at that moment. Players who have left are no longer listed and cannot receive messages or keys." (`rules.LEFT_RULE` + `rules.MIDTURN_RULE`)
- **End.** Unchanged: the game ends at max_rounds, or when every agent is done (won/departed, or has no open need). An agent whose missing key left with a winner stays in the game until max_rounds.
- **Invariants.** A new `left` check covers: no turn after leaving (simultaneous: none after the win round); no successful action after leaving; no key transfer to or from a departed agent; no real DM to or from one; a locked score at every round_end and in the outcome; exactly one departure notice per other agent. The `obs` check now also requires pinned peers to equal the players still in the game.
- **God.** God cannot forge a DM whose shown sender or receiver has left. `GodRunner(..., winners_leave=cfg.game.winner_policy == "sit_out")` → `apply_message_fraud`. The fraud fails on God's side: one `god_power` event with ok=False and `reason="sender_left"` / `"receiver_left"`. No budget is spent, no intervention id is created, and nothing is delivered. ScriptedGod's target picks are unchanged, so under sit_out a scheduled fraud whose `recent_partner` has left fails and leaves the budget unspent. The `left` invariant now also covers forged DMs.
- **Cache and prompt-set hash.** Editing system.j2 changes `PromptSet.hash` (in `CallMeta.prompt_set_hash` and the manifest), but this hash is not in the LLM cache key: `cache_key` = backend + model + `ChatRequest.sampling()` (messages, seed, sampling params; `meta` and `call_id` excluded). It is not in seeds (`derive_seed`) or game ids (`config_hash` has no prompt field) either. Tested in `tests/llm/test_cache_key_meta.py`. An offline replay of G1 `grid_oss_sim_k2` g00-nogod (network blocked, cache read_only) got 203/203 cache hits at $0. It was identical up to r6, where the base game's own call got an empty response, which was never cached. `invariants --base`: "base break r6, control diverges at r6", 0 violations.
- Config: `configs/winners_leave_sim.yaml` is `grid_oss_sim_k2` with `winner_policy: sit_out`.

## 10. Fixtures (`tests/conftest.py`)
- `tiny_cfg` is 6 agents, 5 rounds, every role on the fake backend, with the `words` tokenizer.
- `fake_llm`, `tmp_run_dir`.
- `fixed_state` is 4 agents. It has a forged DM from GOD posing as blue_owl, a tampered scratchpad on amber_fox, and a correct burn of dune_cat's need 3 with a minted key. Its canaries are in `tests/fixtures/fixed_state.py`.
- Markers `gpu`, `openrouter` and `slow` are auto-skipped.

## Open questions for the lead
Resolved: fork seeds (common random numbers, §4) and the wrong-defect notice (§2).
1. Naming. `turn_mode` holds sequential/simultaneous and `turn_order` holds fixed/reshuffle, following the doc. `cot_mode` uses `explicit` instead of the doc's `field`.
