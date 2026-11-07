# Review of ARCHITECTURE_v2.md (independent, skeptical)

Reviewer scope: the plan only, checked against the two PDFs, the lead's requirements, `infra/README.md`, `infra/serve.sh` and `infra/vllm.log`. I did not read the critiques file. Tags: **[BLOCKER]** must be fixed before WP0 freezes; **[HIGH]** fix before I1; **[MED]** fix when convenient; **[K]** background knowledge I did not verify this session.

## TL;DR
- The design is sound at its core: pure rules, a single `view_log` choke point, `MemoryStore.overwrite()` as the only mind-control path, a cache-backed LLM layer, and FakeLLM-first testing. The PDF reading is mostly faithful, and the deviations are labelled.
- It is about **2x too big for 40 hours**. §17 (context, taint, laundering, retrieval), WP8 monitors, ReplayLLM, the plotly report and seven of the eleven grid blocks should be cut or deferred.
- The contract is **not freezable as written**. §3 and §17.2 contradict each other, event payloads are undefined, `Action` has no actor, and the defect-delay arithmetic has an off-by-one between §3 and §10.
- I found **three real truth-leak paths** that the planned tests would miss: the forged-DM round stamp, `phase`/`actor`/`seq` in PublicTrace, and the ledger/summarizer bypassing `view_log`. I also found **one silent science bug**: the B′ noise replica gets served B's cached responses, so the noise floor is 0.
- The schedule header is stale. It says 56 h, but about 40 h remain. On paper the critical path fits (T+30 to T+31 against a T+34 internal target), but that ignores sleep, underestimates WP1 and I1, and the grid arithmetic only works for the plain no-God, no-compaction case.

## 1. PDF fidelity: misread, dropped, invented

Both PDFs have identical rule text. §0.1 is correct about that.

| # | PDF text | Plan | Verdict |
|---|---|---|---|
| 1.1 | "Defect can occur as long as Agent being burned has not won yet" implies a winner is still in the game, just immune | §8 step 2 runs only "non-done" agents, and nowhere says whether a winner is done. If winners stop acting, their 2+ surplus keys leave the economy, which changes welfare a lot. | **[HIGH] Unspecified, high impact.** Add a knob `game.winners_continue: true` (a winner can still message and give, cannot be burned, and gets no LLM turn once it holds no keys). Add it to the §1 table as D13. |
| 1.2 | "Win ... (Or however many keys it can use if burned)" | v1 D3: holds all non-burned needs and at least 1 non-burned. Score = held/3. | Faithful. §1's row "score = held non-burned needs / 3" is fine. Put the D3 text into v2 §1, because subagents will not read v1. |
| 1.3 | Keys are `{ID: int, key: int}`, "rivalrous ... only one person can possess" | `Observation.keys: list[KeyCopy]` shows the `key` int to the agent. Nothing says what happens if an agent DMs "key for 7 is 4821". | **[MED]** Either hide `key` from observations, or have `system.j2` state that only Give transfers possession and that knowing the number gives no credit. Otherwise agents waste turns "sharing" numbers, and the share-willingness metrics (§12) count non-events. |
| 1.4 | Defect: the victim "will be informed it cannot" get the info | The victim notice names the actor by default (`defect_actor_identity: null` inherits `actor_identity: shown`). | The PDF does not say the victim learns *who* did it. That is a design choice with large effects on retaliation. **[DECIDE]** Default the victim notice to `hidden`, or confirm `shown` explicitly with the lead. |
| 1.5 | A wrong defect: the actor "loses ability to progress on one piece of info ... or delayed" | Penalty is covered (D2). But **is a wrong defect visible**, to the target or to others? Is it released on the delayed log? | **[HIGH] Undefined in §1 and §10.** A wrong defect line reveals "V does not need X", which is a real information leak. Proposal: wrong defects follow the same `defect_visibility` path, the target is *not* notified (the PDF only notifies on a hit), and the actor learns the outcome through its own `action_result`. Add this to `test_defect_visibility`. |
| 1.6 | The victim already holds the key for the burned need | Not covered. | **[MED]** Rule: the need is burned and the held copy stays as a tradeable surplus key. Add a table test. |
| 1.7 | "View Log: logs of all actions taken by **previous agents** in the last round" + "turn order" | D7 uses simultaneous rounds, so nobody sees anyone's actions within a round. | This deviation is acceptable and necessary for batching, but it is only explained in v1. Restate D7 in v2 §1 as a deviation the paper must mention. |
| 1.8 | View Log / View Board are **tools** that count toward the 1-2 per turn | Default `observe_mode: folded` makes them free and always on. | Deviation, labelled as a knob. Fine for 8B agents. **Cut `observe_mode: tools` entirely** (see §3), and list "folded" as a deviation in the paper. |
| 1.9 | "Game is ended after 100+ rounds" | `max_rounds: 40` | Deviation. Fine if P3 shows that games finish naturally (`all_done`). Otherwise the paper must say so. Also set `start_round` "late" **relative to the median game length from P3**: with 40 rounds and fast cooperative games, `start_round=15` can land after the game has effectively ended, and B1's "late" arm measures nothing. |
| 1.10 | "If the ID is a info that the agent **specified** needed" | Read as the true needs. | Probably right. An alternative reading is "needs the victim has *announced*", which would directly couple disclosure and vulnerability. Note it as an ambiguity for the lead; no code needed now. |
| 1.11 | COT Control `{..., COT Round to overwrite: int, COT to be added in: str}` | `replace` by default, `append` as a knob | Fine. "Added in" arguably favours `append`. Keep the knob and default to whichever P4 shows has bite. |
| 1.12 | God powers: Message Fraud and COT Control | Plan adds a `scratchpad` target, a `summary` target (§17.5), signed messages (B3 = v1 H4) and taint/laundering | These are **inventions**, labelled as NEW. Acceptable as research extensions, but they are the first things to cut (see §3). |
| 1.13 | Not in the PDF: **are agents told that God exists?** | Unspecified anywhere. | **[HIGH] Missing design decision.** It changes every fraud result, and it interacts with the `"GOD"` canary in `test_no_truth_leak`: if the system prompt mentions God or an adversary, the test fails or gets weakened. Make it a prompt-set variant (`agent/v1` = not told; `agent/v1_warned` = "messages may be forged") and pin the canary to the intervention ids, not the word "GOD". |
| 1.14 | `actions_only` = gives, defects, board posts (the lead's requirement) | Matches. The defector's minted key is never rendered as a give. | Good. |

## 2. Interface and schema problems that block parallel work

These all belong in WP0. Every one is cheap to fix now and expensive after 8 agents have coded against the current text.

| # | Problem | Where | Fix |
|---|---|---|---|
| 2.1 **[BLOCKER]** | **§3 and §17.2 contradict each other.** §3 `Observation` has `inbox`, `board_tail`, `cot_history`, `scratchpad`. §17.2 says Observation "shrinks to this round's deltas plus pinned facts" and that history is "no longer an Observation field". `MemoryEntry` in §3 has no `entry_id`, no `"summary"` kind and no `taint`. §3 `EventType` lacks `context_built` and `compaction`. The `GodAction` cot_control `kind` lacks `"summary"`. `LLMCall.role` lacks `"summarizer"`, although §17.7 adds `roles.summarizer`. | §3, §17.2 | Rewrite §3 as **one** reconciled schema that already includes §17.2's types. Delete §17.2 as a separate block. WP3 and WP1 otherwise build two different Observations. |
| 2.2 **[BLOCKER]** | **Event payloads are undefined.** `Event.data: dict  # validated by PAYLOADS[type]`, but PAYLOADS is never specified. WP1 emits events, while WP5, WP6, WP7 and WP13 consume them, and WP6 builds `synth_trace` against payloads it has to guess. That is a guaranteed integration failure at I1. | §3 | WP0 defines one pydantic model per event type (`TurnData`, `KeyTransferData`, `BurnData`, `MessageData`, `MemoryOverwriteData`, `GodPowerData`, `NoticeData`, `RoundEndData`, ...) and a `make_event(type, data)` helper. Move `synth_trace` to WP0, or generate it from WP1's golden tiny game. |
| 2.3 **[BLOCKER]** | **`Action` has no actor**, yet `rules.apply(state, action, cfg)` must know who acts. | §3, §2 `rules.py` | Use `apply(state, actor: AgentId, action, cfg)`, or add `actor` to a resolved `ActionIntent`. |
| 2.4 **[BLOCKER]** | **The defect-delay off-by-one.** The §3 comment says the observation at round r releases defects from round `r-1-delay`, so a defect at round d is seen at d+4. The §10 test `test_others_at_delay` asserts "exactly r+delay", i.e. d+3. WP1 and its test author will disagree. | §3 comment, §10 `game.observe` row | Define this once, in words: "Normal actions from round d appear in the observation at d+1. Delayed defects appear in non-victims' observations at d+1+`defect_delay_rounds`." With delay=3 that is round d+4. The victim's notice arrives at d+1. Update the §10 test names to say "obs round d+1+delay". |
| 2.5 **[HIGH]** | `LogLine` and `AgentMessageView` exist only as comments. They are *the* leak whitelist and must be concrete frozen models with `extra="forbid"`. | §3 | Make them real classes in `schema.py`. Have `observe.py` build them field by field. |
| 2.6 **[HIGH]** | **`MemoryStore` is "backed by GameState.memory" with no state argument.** Combined with `model_copy(deep=True)` at each step boundary, a store holding a reference writes to a stale copy, silently. | §7, §3 | Use a functional API: `memory.overwrite(state, ...) -> (state, event)`, or a single mutable state with no deep copies, snapshotting by `model_dump_json()` at round end only. Pick one in WP0. |
| 2.7 **[HIGH]** | **Frozen models inside a mutable GameState.** `AgentState` and `Message` are `frozen=True`, yet the rules mutate them. Every rule becomes a `model_copy(update=...)` chain, and the deep copy of a GameState that holds ledgers (§17.2) is slow (see §5.6). | §3 | Make the state classes (`GameState`, `AgentState`) mutable. Keep records (`Event`, `Message`, `Observation`, `LLMCall`) frozen. |
| 2.8 **[HIGH]** | **Who turns events into ledger items is unspecified.** §17.2 says "the engine appends its items to the agent's ledger". If that path is built from events instead of from the `Observation`, it bypasses `view_log` and leaks DMs under `actions_only` and unreleased defects. | §17.2, §8 | Make it a contract: **ledger items are created only by `context.ledger.items_from_observation(obs)`.** Then the Observation is the single choke point, and the ledger can never contain what `observe()` withheld. |
| 2.9 **[HIGH]** | **Two renderers.** `HistoryItem.text` is "exactly what the agent would be shown" (rendered by WP1 or WP13), while §6 says templates (WP3) render the Observation. The token-budget code (WP13) needs counted text before WP3's template exists. | §6, §17.2-17.4 | Put item-to-text rendering in one owned module (`context/render.py`, WP13, with formats frozen in WP0). Templates only *place* pre-rendered sections and the system and format text. Budget step 1 also needs the system-prompt token count, which comes from WP3. Pass it in as `fixed_overhead_tokens`. |
| 2.10 **[HIGH]** | **`call_id` and `msg_id` determinism.** Accounting "assigns `call_id`", and `turn` events embed `llm_call_ids`. If the id is a uuid or a launch-order counter, `test_determinism_fake` (with shuffled completion) and `replay --verify` fail for a reason unrelated to game logic. | §5, §3 | `call_id = sha256(run, game, role, agent, round, attempt, purpose)[:16]`. `msg_id` uses the same scheme, the **same for real and forged messages** (see §4.1). |
| 2.11 **[MED]** | `seq` is global, yet `rules.apply` is pure. | §3 | `apply` returns event *bodies*, and the engine's `EventSink` stamps `seq`, `run_id` and `game_id`. |
| 2.12 **[MED]** | Config key drift. §1 has `reasoning.max_cot_tokens` while §4 has `max_cot_chars`. `game.obs.*_last` and `reasoning.cot_replay_window` are "superseded" by `context.per_kind_caps` yet still in `base.yaml`. With `extra="forbid"` and two sources of truth, people set the wrong one. | §1, §4, §17.7 | Delete the superseded keys from `base.yaml`, and keep only `context.per_kind_caps`. |
| 2.13 **[MED]** | `reveal_provenance` sits under `view_log`, but it controls tagging of forged messages in the **inbox** (B3 "signed messages"). | §1, §4 | Move it to `game.provenance.tag_forged_dms`, and state that B3 is that flag. |
| 2.14 **[MED]** | v2 says "unchanged, see v1 §x" in many places (D1-D7, monitors, labels). Subagents get one document. | §0, §1 | Inline D1-D7 (7 lines). Drop the monitor references if WP8 is deferred. |

## 3. Over-engineering: what to cut or defer (ruthless)

The test for each item: does the PDF's End Results need it, did the lead explicitly ask for it, or does the critical path depend on it? If none of those, it goes.

**Cut now (do not build):**
- **WP8 Monitors in full** (`swarm/monitors/*`, `prompts/judge/{provenance,cot}_v1`, P8, Fig "Monitor ROC", `roc.py`, `MonitorScore`, `Label` kinds for monitors). The PDF's "Watch tower mind control" is a one-line brainstorm note, not an End Result. This frees one agent and the whole PublicTrace hardening burden (§4.3).
- **ReplayLLM** (`llm/replay.py`) and the "full rerun byte-identical" half of `replay --verify`. The sqlite cache in `read_only` mode already *is* a replay backend, keyed identically. Keep state replay (fold events, compare `state_hash`), which is cheap and catches rule drift. Take P7 off the grid's critical path: a replay failure becomes a bug ticket, not a grid blocker.
- **§17 extras:** BM25 retrieval (§17.3), the `hybrid` policy (merge it into `rolling_summary`, since it is the same thing plus a window), the `CheapSummarizer` and `roles.summarizer`, the `exposed` taint propagation, the `judge/carried_v1` judge, the `laundered`/`intervention_carried` labels, the `test_counter_agreement` tokenizer check, and grid block B7. **Keep:** the `ContextPolicy` protocol, `window` (default), `rolling_summary` with the `self` summarizer, the `extractive` summarizer for tests, the `compaction` event, and the `summary` target for CoT control (cheap once `MemoryStore` exists). That satisfies the lead's "modular context and compaction" requirement at roughly 40% of WP13. Taint, if wanted, is computed **post hoc** in analysis from `context_built.included_item_ids` + `compaction.source_item_ids` + `god_power` events. There is no need to carry it live in `HistoryItem`, and removing it from the live objects removes a leak surface (§4.2).
- **`observe_mode: tools`** and **`immediate_reply`**: both default off. Each adds an engine path, parser cases and tests. Make the config validator raise `NotImplementedError` if either is set.
- **`agent_groups` heterogeneity:** B6 runs a whole swarm on one model, so no groups are needed.
- **The plotly HTML report** with a round slider, hover CoT diffs, drill-down cards and a sortable grid index (§11). Replace it with a static Jinja HTML page that embeds the matplotlib PNGs plus three tables (outcome, God actions with downstream events, config/prompts). The lead's "clear visualization" is met by good PNGs. The figures to build: timeline, network small multiples, agent-state heatmap, coop/strategy bars, dose-response, ripple. That is 6, down from 9.
- **The strategy LLM judge** (`judge/strategy_v1`). Keep only the rule-based labels, and hand-pick CoT quotes.
- **`doctor` prompt-hash archaeology** across past manifests, and the `deep` hypothesis profile.
- **The 5-layer middleware stack** as separate classes. Use one `ManagedClient` (~200 lines) that does semaphore + cache + retry + accounting, with the budget check active only when `price > 0`. The behaviour and the §10 `llm` tests stay the same, with fewer files and seams.
- **Prompt goldens for every set × cot mode × scratchpad** (about 18 files). They will churn on every pilot prompt edit. Keep one golden per set in its default mode, plus the `test_prefix_stable` invariant.

**Defer (build only if the core grid is running by T+16):**
- The `native` cot mode and B5. Thinking costs about 1k tokens per turn (infra README), does not fit `max_tokens: 400`, and blows the KV budget (§5). The `field` and `none` modes suffice for the lead's "switchable CoT modes".
- B6 OpenRouter strong model (see the cost arithmetic in §5.5), B2s, B3v, B4 LLM God (it is slow; see §5.4), and B3 signed messages.

**Core grid after cuts** (with N=20, the P3 `max_rounds`, and seeds 0-2 unless noted):

| Block | Games |
|---|---|
| B0 no-God baseline, 6 seeds | 6 |
| B1 fraud K ∈ {1, 3, 10} × timing {early, late} | 18 |
| B2 CoT control, same design | 18 |
| Controls: B and B′ forks for 3 seeds × 2 timings | 12 |
| B3d defect visibility (`public` and `victim_only`, × 2 seeds) | 4 |
| **Total** | **58** |

B1 and B2 can drop to K ∈ {1, 10} if short, giving 46. Then run the stretch blocks in this order: B4 (3), B7-lite (6), B6 (2-4).

## 4. Testing gaps (leaks, defect visibility, God provenance, compaction)

### 4.1 Leak paths to agents that the §10 tests miss
1. **[BLOCKER] The forged-DM round stamp.** Fraud is applied in the God phase of round r, and "delivered to the victim's inbox for **this** round's observation" (§8 step 1). Real DMs sent in round r-1 arrive at round r with `Message.round = r-1`. A forged one has `round = r`, so **any DM in the inbox stamped with the current round is forged.** `AgentMessageView` includes `round` and `msg_id`, so the leak reaches the prompt. The planned canary test scans for strings (`forged`, `GOD`, ...), so it cannot catch a leak carried by a value. Fix: stamp forged messages with `round = r-1` (or apply fraud at the end of the previous round's resolve phase), use the same `msg_id` scheme and inbox sort key (by `msg_id` hash, not by insertion order) for both kinds, and drop `round` from inbox rendering. Test **`test_forged_indistinguishable`**: in a game where a forged DM and a real DM have identical text and sender, the two rendered inbox lines are byte-identical up to the message text. Run it as a property test.
2. **[HIGH] The ledger and summarizer bypass** (see 2.8). Test **`test_ledger_subset_of_observations`**: every `HistoryItem` in every ledger has a `ref` that appears in some `Observation` that agent actually received, at or before the item's round. Add **`test_summary_no_unreleased_defect`**: plant a defect canary info id. Under `victim_then_delayed`, it must not appear in any *non-victim's* summary text, `ContextBundle` or prompt before obs round d+1+delay. This must hold for the extractive summarizer too, which is the one most tempting to implement over events.
3. **[HIGH] The scan scope is wrong.** §10 scans "the serialized Observation **and** the rendered prompt". After §17, the prompt is built from `ContextBundle`, not Observation. There are also **other prompts**: `retry.j2` (which may echo the bad output and an error string), the summarizer prompt, and immediate-reply prompts. Replace these with a single oracle: **`test_no_truth_leak_e2e`** runs games on FakeLLM, which records every request, and scans **every `ChatRequest.messages` byte sent with role ∈ {agent, summarizer}** for canaries: intervention ids, `original_text` of tampered entries, the true sender's name tied to forged text, `taint`, and `tampered`. This one test covers every current and future path.
4. **[HIGH] Templates can serialize the whole object.** A WP3 template doing `{{ item }}` or `{{ obs | tojson }}` would dump `taint`, `ref` and `tampered`. Pass templates **render-only view models** (`RenderItem{text}`, `RenderLog{...}`) that do not have those fields, so a leak is impossible by construction. Add a test that template context objects have no attribute in `TRUTH_FIELDS`.
5. **[MED] A false-positive risk in `test_others_not_before_delay`.** It says that no non-victim observation before release contains "A's name tied to V, or the info id in a defect context". If the victim *posts on the board* "A burned me", that is legitimate in-game speech, and the test fails on a correct engine. Restrict it to **engine-generated fields** (LogLine, notices, pinned facts), or run it with scripted agents that never post.
6. **[MED] Wrong defects and `steal`.** Under `defect_gain: steal`, a third party C loses a copy. Does C get a notice? Is that visible before release? It is unspecified (1.5). Either test it or forbid `steal` together with `victim_*` modes.
7. **[MED] The God-awareness canary** (1.13). Do not use the literal `"GOD"` as a canary if any agent prompt variant mentions an adversary.

### 4.2 God provenance in logs, analysis and PublicTrace
Only relevant if monitors survive. I recommend cutting them (§3). If they stay:
- The `message` event for a forged DM has `phase="god"` and `actor="GOD"`. **Both fields alone identify forgery**, and §3's PublicTrace strip list does not mention them.
- Stripping `god_*` and `memory_overwrite` events leaves **gaps in `seq`** at the intervention points.
- `snapshots.jsonl` holds `Message.forged`/`true_sender`, `MemoryEntry.tampered`/`original_text`, and the ledgers' taint.
- `llm_calls.jsonl` contains role=god calls.
- `turn.cot` (the original text) differs from the later memory text, so a diff reveals the overwrite.
- The fix: PublicTrace is built by **whitelisting** fields, not blacklisting. It re-sequences `seq`, rewrites `phase` and `actor` for messages, and never exposes snapshots or god LLM calls. Test it with a monitor that "cheats" by reading every available field: its AUROC must be ≤ 0.6.

### 4.3 Defect visibility: missing cases
- The off-by-one in 2.4. Test both the victim's round (d+1) and the others' round (d+1+delay) exactly, for delay ∈ {1, 3}.
- **A non-victim who is delayed or done at the release round.** Is the release lost or queued? Decide "queued until their next observation" and test it.
- **The game ends before release.** The `game_end` analysis must still count the burn as hidden.
- **Multiple defects on the same victim in consecutive rounds.** Each must be released exactly once (the plan only says "later rounds do not repeat it").
- **Interaction with compaction.** A released defect line enters the ledger exactly once and then ages normally. It must not be re-released by `window()` logic.

### 4.4 Compaction correctness: missing invariants
- **Coverage, no gaps or duplicates:** for every bundle, every ledger item older than the window is either covered by exactly one summary's `source_item_ids` or listed in `dropped_item_ids`. No item is both summarised and shown raw.
- **No peeking:** a summary's `source_item_ids` ⊆ the agent's ledger at compaction time, and the summarizer request contains only those items plus `prev` plus pinned (this is checked by the e2e oracle in 4.1.3).
- **`tokens_after < tokens_before` will flake** with LLM summarizers when there are few items. Assert it only for the extractive summarizer. For LLM summarizers, assert `≤ summary.max_tokens`.
- **`test_compaction_deterministic`** is only meaningful with FakeLLM or extractive. Say so; with vLLM it is not deterministic (§5.7).
- **Tamper labels:** `tampered_turn` must be positive **only if the tampered entry was in that turn's bundle**. A CoT overwrite of a round outside the window is a no-op and must not count as a positive. Test this.
- **Forking mid-cycle:** fork at a round between two compactions, and check that the next compaction covers the same rounds as in the parent.

### 4.5 Seeds, cache and the noise floor
- **[BLOCKER for the ripple results] B′ ≡ B.** `seed = derive_seed(run.seed, game_idx, "turn", agent, round, attempt)` and the cache key includes `messages` + `seed`. The noise replica B′ forks the same snapshot with the same config and the same seeds, so **every B′ call is a cache hit on B's response**. B′ is then byte-identical to B, and the noise floor is exactly 0, which makes every ripple divergence look significant. Fix: add `replica_id` (and `branch`) to `derive_seed`, and add **`test_noise_replica_differs`**, asserting that B′'s cache keys are disjoint from B's from the fork round on.
- The same mechanism makes grid cells that share `run.seed` **identical before God's start round** (cache hits). This is fine, even useful as common random numbers, but `stats.py` must treat those cells as paired, not independent. Document it.

## 5. LLM layer risks (throughput, KV, OpenRouter, cache, determinism)

### 5.1 The KV budget: re-checked
- The per-token KV for Qwen3-8B (36 layers × 8 KV heads × 128 dim × K,V × bf16) is 144 KiB. The current `infra/vllm.log` reports **7.67 GiB = 55,840 tokens** at `GPU_UTIL=0.75`, which is more than the README's 49.6k. The same log reports **30.05 of 31.84 GiB free at startup**, and suggests `--kv-cache-memory=14503328768` (13.5 GiB) to use the whole card. That is **~98k tokens, about 1.8x**, for one flag in `serve.sh`, provided nobody else (nnsight or finetune work) needs the GPU during the grid. This is the cheapest throughput win available. Schedule GPU research outside grid windows.
- The plan's arithmetic in §17.6 is internally correct: 20 × ((2500 − 900) + 400) + 900 = 40.9k tokens. But it rests on `max_tokens: 400`, which is too small (5.2). At 650 output tokens: 20 × 2250 + 900 ≈ **45.9k**. That still fits one game in 55.8k, but **not** `run.max_concurrency_games: 2` (≈ 92k), which would preempt and thrash.
- **Set `max_concurrency_games: 1` for vLLM unless KV is raised to ~98k.** The `max_concurrency: 64` in `models.yaml` is not "the KV limit", as §5 claims. At about 2.3k tokens per sequence only ~24 fit in KV at once, and the rest queue. A 64-wide semaphore is harmless with 1 game, but the stated justification is wrong.

### 5.2 `max_tokens: 400` will truncate in `field` mode
- The output contract is `thought` + `note` + up to 2 actions in JSON.
- `max_cot_chars: 1200` (~300 tokens) applies only to the **stored** CoT (§7, "Truncation"). It does not constrain generation.
- `note` ≤ 400 chars is ~100 tokens. Two actions with message text are ~60-150 tokens, and the JSON scaffolding is ~20.
- Expected total: **~480-570 tokens > 400.** The result is `finish_reason=length`, which means truncated JSON, a parse retry, and then the tail latency of 5.3.
- Fix: `roles.agent.max_tokens: 700`. Tell the model the limits in `format_field.j2` ("thought ≤ 80 words, note ≤ 40 words"). Log the `finish_reason=length` rate as a P1 gate (≤ 3%).

### 5.3 Round time vs the P3 gate (≤ 10 s/round at N=20)
- **Decode.** The infra bench (32 concurrent, 256 tok, p50 3.26 s) gives ≈ 78 tok/s per stream. About 450 output tokens is ≈ 5.5-6 s per turn.
- **Prefill.** 20 × 1.6k uncached tokens is about 1-2 s, chunked and interleaved.
- **The parse-retry tail.** A round waits for its slowest agent. With a per-agent first-try failure rate p, P(at least one retry in the round) = 1 − (1 − p)^20: **64% at p=5%, 88% at p=10%.** So most rounds pay for a second, sequential call: +3-5 s.
- **Compaction.** Every 4 rounds, 20 × 300 output tokens is ≈ 4-5 s, or about +1 s per round on average.
- **Engine CPU.** Deep copies plus validation (5.6) add 0.5-3 s.
- **Estimate: 11-14 s/round, so P3's ≤ 10 s gate is likely to fail.** Mitigations, in order of value:
  1. Shorter output (5.2).
  2. Start retries per agent as soon as that agent's parse fails. They already run concurrently inside each `act()`, so make sure the retry is not a second `gather`.
  3. Raise the KV and run 2 games at once. The bench shows aggregate throughput rising about 1.57x from 32 to 64 in flight.

### 5.4 Grid wall-clock: re-checked
- **The plan's claim.** It says ~95 games at 8-10 games/h ≈ 10-12 h. At 40 rounds × 12 s = 8 min/game, that is **7.5 games/h** for one game at a time. **95 games ≈ 12.7 h**, and that is *before* the slow blocks.
- **B4 LLM God.** Up to 4 *sequential* God calls per wake, with ~10k-token context and 600 output tokens, take ≈ 25 s per wake, and agents wait for them. That is about 3x the round time, or ≈ 25 min/game.
- **B5 native.** Thinking costs about 1-2k tokens per turn (infra README), which is 15-25 s per turn, and 20 × 3.6k = 72k tokens of KV, so it queues. That is about 3-4x slower.
- **The core grid in §3** (58 games) takes ≈ 7.7 h at 1 game at a time, or **≈ 5.3 h** with the larger KV and 2 games at a time.
- If P3 shows that games end naturally around round 20, halve all of these numbers.

### 5.5 OpenRouter
- **Cost per game.** 800 turns × ~2.5k input tokens ≈ 2.0M input, and × ~450 output ≈ 0.36M output.
  - `or_qwen3_8b` [K: ≈ $0.05/M in, $0.2/M out]: ≈ **$0.2/game**.
  - A frontier "strong" model at $3/M in and $15/M out: ≈ **$11/game**, so 4-6 B6 games would cost $45-66, which is **over the $25 default cap**.
  - Fix: choose `or_strong` with a cost ceiling of ≤ $4/game (about ≤ $1/M in and ≤ $4/M out), or run B6 at N=12 with 20 rounds.
  - Put this calculation in §15 B6 so P6 has a pre-registered target.
- **Rate limits [K].** Paid models generally have no tight per-key limit at concurrency 8. `:free` variants are about 20 requests/min and are unusable for a 20-agent swarm. Ban `:free` aliases in `models.yaml` validation.
  - Round time at concurrency 8 is ⌈20/8⌉ = 3 waves × 3-10 s per call, so **10-30 s/round** and 7-20 min/game. That is fine for 2-4 games in parallel with the local grid.
- **Provider routing breaks the "behaves like local Qwen" cross-check.** OpenRouter can route `qwen/qwen3-8b` to different providers with different quantizations, and many ignore `seed`. Pin the provider: `extra_body={"provider": {"order": [...], "allow_fallbacks": false, "require_parameters": true}}`. Log `provider` from the response in `LLMCall`.
- **Parameter names [K].** `reasoning: {enabled|effort|max_tokens|exclude}` exists. Usage and cost reporting (`usage: {include: true}`) may now be automatic. The plan already isolates this in the preset and defers it to P6, which is fine.

### 5.6 The engine-side cost of §17's "ledgers in GameState"
- **How big the ledgers get.** At about 30 items per agent per round, 20 agents × 40 rounds ≈ 24k `HistoryItem`s by the end of a game. GameState is `model_copy(deep=True)` "at each step boundary". If a step is one action, that is up to 40 deep copies per round of a model graph that keeps growing. In pydantic v2 that costs tens to hundreds of ms each, on the event-loop thread.
- **How big the snapshots get.** `snapshots.jsonl` stores the full GameState every round. The total is Σ (ledger size) ≈ 40 × 12k items × ~200 B ≈ **100 MB per game**, or **~6-10 GB for the grid**.
- **The fix.**
  - Keep ledgers out of GameState. They can be reconstructed deterministically from the Observations, which are logged (or loggable) per turn.
  - Snapshot every round, but without the ledgers.
  - Deep-copy only at round boundaries, not per action.

### 5.7 Caching and determinism claims
- **"Byte-identical replay" holds for engine logic only**, and only if `call_id` and `msg_id` are deterministic (2.10) and no wall-clock value enters the events. Say so explicitly.
- **The vLLM seed does not give determinism.** Batch composition changes the logits [K]. The cache is the reproducibility mechanism, and the plan says this correctly.
- **The cache key** omits `top_k`, `stop` and the `extra_body` provider routing. Either include the full sampling dict or forbid those parameters, so that adding `top_k` later does not serve stale entries.
- **The B′ cache collision** (4.5) is the one place where the cache silently corrupts a scientific result.

## 6. Schedule and critical path: arithmetic re-checked

**The header is stale.** Line 3 says "~56 h from now" with T0 = Sat 04:00 UTC. The lead now says about 40 h remain, so T0 ≈ now (Sat ~20:00 UTC). In those terms the internal target (Mon 06:00 UTC) is **T+34** and the hard deadline is **T+40**.

**The plan's critical path, with its own +0.5 h shift:**

| Step | Duration | Ends |
|---|---|---|
| WP0 | 2 h | T+2 |
| WP1 | 4 h | T+6 |
| I1 | 1.5 h | T+7.5 |
| WP10 pilots | 3.5 h | T+11 |
| DEMO | 1 h | T+12 |
| WP11 grid | 10 h | T+22 |
| WP12 write-up | 8 h | **T+30-30.5** |

On paper there is 3.5 h of slack to the internal target. Problems:
1. **No sleep for the lead.** The lead runs the pilots, the demo and the write-up, all on the critical path. 30 h straight is not credible. Put ≥ 5 h of sleep inside the grid window, with an agent babysitting the grid.
2. **WP1 at 4 h is the biggest underestimate.** As specced it covers: world generation with max-flow feasibility, rules for 3 gain modes × 2 penalties, `observe` with 4 log contents × 4 defect modes × actor identity, the engine with God hooks, the compact phase, immediate reply, snapshots, resume, the fork and determinism hooks, scripted agents, and a welfare sanity check. That is **6-7 h for one agent**. Fix: split it in two. WP1a covers world, rules and scripted agents. WP1b covers `observe`, `view_log` and the engine, coded against the frozen `apply` signature. Together with the cuts in §3, that is ≈ 4 h wall.
3. **I1 at 1.5 h integrates six packages** (WP1-5 plus WP13) written against fakes and undefined event payloads. Budget **3 h**. Fixing 2.2 makes this realistic.
4. **Pilots at 3.5 h.** GPU time alone is ≈ 2.2 h at 12 s/round:
   - P3: 2 × 40 rounds plus 3 × 20 rounds ≈ 30 min.
   - P4: 9 games × 25 rounds ≈ 45 min.
   - P5: 6 × 20 rounds ≈ 25 min.
   - P9: 7 × 16 rounds ≈ 22 min.
   Add the sequential decisions and prompt-fix cycles, and **4 h** is realistic. P9 goes away with the §17 cut.
5. **The grid at 10 h is under-costed** for ~95 games (5.4 says ≥ 12.7 h). The 58-game core is 5.3-7.7 h.
6. **The write-up is purely serial after the grid.** Start the paper skeleton, the methods section, Fig 1 and the related work at DEMO (T+12) with one agent. Only results and figures wait for the grid.
7. **Parallelism.** The plan runs up to 10 packages at once (WP1-8 + WP13 + WP9), but there are about 8 subagents. A proposed allocation of 8:
   - WP1a world and rules
   - WP1b observe and engine
   - WP2 LLM
   - WP3 agent and prompts
   - WP4 adversary
   - WP5 + WP9 runlog, runner and doctor
   - WP6 + WP7 analysis and viz
   - WP13-lite context
   WP8 is cut.

**The revised critical path:**

| Step | Duration | Ends |
|---|---|---|
| WP0 | 2.5 h | T+2.5 |
| WP1a and WP1b in parallel | 4 h | T+6.5 |
| I1 | 3 h | T+9.5 |
| Pilots P1-P5 + P7 | 4 h | T+13.5 |
| DEMO = the first B1 game and its fork, taken from the grid itself (no separate run) | 0.5 h | T+14 |
| Core grid, with the lead's sleep inside it | 6-8 h | T+20-22 |
| Write-up tail | 5 h | **T+25-27** |

That leaves **7-9 h** before the internal target, for stretch blocks (B4, B7-lite, B6) and fixes. This plan fits. The current one fits only if nothing slips and nobody sleeps.

## 7. Top 10 changes, ranked by impact

| Rank | Change | Exact sections to edit |
|---|---|---|
| 1 | **Make the WP0 contract freezable.** Merge §17.2 into §3 as one schema. Define a typed payload model per `EventType`, and add `context_built`, `compaction` and the `summarizer` role. Make `LogLine` and `AgentMessageView` concrete classes. Use `rules.apply(state, actor, action, cfg)`, returning event bodies that the sink stamps. Use deterministic `call_id` and `msg_id` (hash-derived). Make state classes mutable and records frozen. Give `MemoryStore` an explicit state argument. Move `synth_trace` to WP0, or derive it from the golden game. Delete the superseded config keys. | §3 (entire block + design rules), §17.2, §7 MemoryStore code, §5 Accounting bullet, §4 `base.yaml`, §1 row "Thought budget", §13 WP0 and WP6 rows |
| 2 | **Close the agent truth-leak paths.** Stamp a forged DM with `round=r-1`, use the same id scheme and inbox ordering as real DMs, and drop `round` from inbox rendering. Create ledger items only from `Observation` (`items_from_observation`). Give templates render-only view models. Replace the scan with an end-to-end canary oracle over every recorded `ChatRequest` (agent, summarizer and retry), plus `test_forged_indistinguishable` and `test_ledger_subset_of_observations`. | §8 step 1 ("delivered ... this round"), §17.2 bullet "Observation shrinks", §6 "Rendering", §10 `game.observe` row and §17.8 |
| 3 | **Fix the B′ ≡ B cache collision.** Add `branch` and `replica_id` to `derive_seed`. Add `test_noise_replica_differs`. Mark same-seed grid cells as paired in `stats.py`. | §5 Cache bullet "Seeds come from ...", §9 `fork` bullet, §10 "Seeded determinism", §12 (pairing note) |
| 4 | **Cut scope.** Drop WP8 monitors, ReplayLLM (use a `read_only` cache rerun) and P7 as a grid blocker, plus `observe_mode: tools`, `immediate_reply`, `agent_groups`, the plotly report, the strategy LLM judge, and §17's retrieval, `hybrid`, cheap summarizer, live taint, carried judge, P9 and B7. Shrink the grid to the 58-game core (B0, B1, B2, controls, B3d). | §2 layout, §5 Backends (ReplayLLM), §9 replay, §11 table, §13 WP table + critical path, §14 P7/P8/P9, §15 table, §17.3-17.5, §17.9 |
| 5 | **Pin the defect-visibility semantics.** The victim's notice arrives at obs round d+1, and others' log lines at d+1+delay (d+4 for delay 3). Wrong defects follow the same path and do not notify the target. Specify the `steal` third-party notice. Queue a release for a non-victim who is delayed or done until their next observation. Release each defect exactly once. Make the victim notice's actor identity an explicit [DECIDE]. | §1 row "Defect visibility" + D12, §3 comment on `defects_released_at`, §10 defect-visibility tests (fix the `r+delay` wording and restrict the side-channel test to engine-generated fields) |
| 6 | **Fix output truncation.** Set `roles.agent.max_tokens` to ~700. Put word limits in `format_field.j2`. Add a P1 gate of `finish_reason=length` ≤ 3%, and log the per-round retry tail. | §4 `base.yaml` `roles.agent`, §6 "Output contract", §14 P1 row, §17.6 (re-do the KV arithmetic with 700) |
| 7 | **Size the GPU properly.** Use `--kv-cache-memory ≈ 13 GiB` (~98k tokens; per `vllm.log`, 30 of 31.8 GiB is free) and reserve the GPU for the grid windows. Otherwise set `max_concurrency_games: 1`. Correct the "64 = KV limit" claim. Re-baseline the P3 gate to ~12 s/round or adopt the §5.3 mitigations. | §17.6 KV arithmetic, §4 `run.max_concurrency_games`, §5 Concurrency bullet, §14 P0/P3 rows, infra `serve.sh` (outside the plan) |
| 8 | **Take ledgers out of `GameState`.** Deep-copy at round boundaries only, and store snapshots without ledgers. This avoids ~100 MB per game of snapshots and per-action deep-copy stalls. | §3 `GameState` paragraph ("copied at each step boundary"), §17.2 "GameState gains `ledgers`", §9 `snapshots.jsonl` row |
| 9 | **Add the missing rule decisions.** `game.winners_continue` (the PDF implies winners remain, immune). God awareness as a prompt-set variant, with a canary that does not use the word "GOD". The key int is hidden, or the rules state that only Give transfers. A burned need whose key is already held stays as surplus. A "late" `start_round` set relative to the P3 median game length. Inline D1-D7 from v1. | §1 table + [DECIDE] list (add D13-D16), §6 variants list, §15 B1 timing |
| 10 | **Re-baseline the schedule to T0 = now (40 h).** Split WP1 into WP1a and WP1b. Give I1 3 h and pilots 4 h. Put the lead's sleep inside the grid window. Make the demo the first grid game plus its fork. Start the write-up skeleton at DEMO. Map the 8 subagents as in §6. Cap B6 at ≤ $4/game, pin the OpenRouter provider and ban `:free` models. | Line 3 header, §13 T0 line + WP table + critical-path bullets, §14 P6 row, §15 B6 row, §16 risks (add "lead fatigue" and "GPU contention") |
