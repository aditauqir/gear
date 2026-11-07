# SWEEP_PLAN: one-factor-at-a-time sweeps around G1 (gpt-oss-120b, 2026-11-07)

**Status (05:21 EST): DONE.**
- Sweep total **$2.142** (≤ $2.30); the ledger is $7.20.
- Results: `plan/SWEEP_RESULTS.md`.
- Ran:
  - start1, start8, start14;
  - K=1, K=4;
  - board_off (6 worlds);
  - N=5 and N=20 (N=20 has 4 healthy worlds);
  - B″ for base@r3 (serving G1, K=1 and K=4), start8, start14 and board_off.
- Not run (no money): board delay/anon/skip3, keys, rounds, and B″ for the N cells. They are
  ranked in §5.

**Follow-ups (lead, 05:25-06:15, from the $7.80 headroom; ≤ 8 in flight):**
- `c16_sweep_board_off`: board-off noGod only on worlds 0-15, $0.134. It confirms the board-off
  main effect at n=16.
- `sweep_board_delay2`: God + noGod + B″@r3, 6 worlds, $0.358.
- Sweep total is now $2.634 and the ledger $7.69. Results are in SWEEP_RESULTS.

**Incidents (all handled; the affected worlds were re-run or excluded):**
1. **False `budget_exceeded` (b2_sweep_start8: 4 worlds; b2_sweep_start14: 8; sweep_start14: 3 God branches).**
   - Cause: RunBudget reserves a worst-case estimate for **every pending call**, before the
     concurrency semaphore. The estimate was prompt × $0.1/M + 1000 × $0.5/M.
   - With 8-12 games of 10 agents in rounds 15-20 that reservation reaches about $0.15, so cells
     whose caps were tight stopped although they had really spent only $0.05-0.13.
   - Fix (5a4a7fc): pre-call estimates of $0.03/$0.15 per M (operational, hashed fixed) and caps
     at 1.25 × projection + $0.06.
   - k4, n5 and board_off were stopped at 04:47 before reaching that point and re-run.
   - Every re-run (`r3_*`, `r3b2_*`) replays all completed calls from the cache and finishes the
     games. Partial dirs: `runs/partial_*_0447`.
2. **N=20: 3 games crashed (g04-nogod, g05-god, g05-nogod; `status error`).**
   - Cause: the `sweep_n20` process started at 03:28 with the old `llm_agent` code but loads
     templates per game. The new system.j2 (board knobs, committed 03:52) needs
     `game.board_enabled`, so games started after that failed.
   - No other running process was affected (all other cells started after the commit, or had
     loaded their games earlier).
   - N=20 is analyzed on its 4 healthy worlds (low n). Re-running seeds 4-5 would cost about $0.2.
3. **Two false starts of `sweep_start1` (03:26, 03:28).**
   - They led to the driver fix: a cell counts only the spend since its launch.
   - The partial dirs are `runs/aborted_sweep_start1_*`, about $0.012 in the sweep total.
4. **Concurrency ran at 12 in flight, above the planned 8: 03:57-04:53 EST.**
   - Three drivers × OpenRouter `max_concurrency` 4 ran at once.
   - 03:57-04:47: stage-1 driver A (`sweep_start8` to 04:08, `sweep_start14` 04:08-04:16, `sweep_k1`
     04:16-04:36, `sweep_k4` from 04:36), stage-1 driver B (`sweep_n20` to 04:28, `sweep_n5` from
     04:28) and the B″ driver NF (`b2_sweep_base` 03:57-04:19, `b2_sweep_start8` 04:19-04:37,
     `b2_sweep_start14` 04:37-04:43), plus `sweep_board_off` 04:43-04:47 (stopped).
   - 04:46-04:53: the repair drivers R1 (`r3_sweep_start14`, then `r3_sweep_k4`), R2
     (`r3b2_sweep_start8`, `r3b2_sweep_start14`) and R3 (`r3_sweep_n5`), followed by R4
     (`sweep_board_off`, from 04:48).
   - From 04:53:35 at most 8 were in flight: R1 (k4, to 04:56) + R4, then R4 + R5
     (`b2_sweep_board_off`, 04:59-05:16).
   - **Provider share** (provider logged per call from ee03d98, 03:52; non-cached calls joined to
     the ledger by run id and call id, timestamps EST; "price" = realized cost / fitted cheapest
     list price $0.0142/$0.0445 per M):

     | window | calls with provider logged | PrimeIntellect | Near AI (fallback) |
     |---|---|---|---|
     | 12 in flight, 03:57-04:53 | 5,766 (+1,735 unlogged from processes started before 03:52: `sweep_start8`, `sweep_n20`) | 5,532 (95.9%), price ×1.14 | 234 (4.1%), price ×2.21 |
     | ≤ 8 in flight, 04:53-05:21 | 3,171 | 3,171 (100%), price ×1.27 | 0 |

   - The fallback share was small (4%) during the 12-in-flight window and zero afterwards.
   - The calls before 03:52 (stage-1 God/control branches of start1, start8 and N=20, and the
     smokes) have no provider record.


## 1. Design

- **Base = G1** (`configs/grid_oss_sim_k2.yaml`):
  - simultaneous turns, N=10, 20 rounds, 5 keys and 3 needs per agent, 2 copies per info;
  - God K=2: message_fraud in r3, then cot_control (scratchpad replace) in r5;
  - openai/gpt-oss-120b, reasoning_effort low, provider_sort price, `salvage_truncated` on.
- **One factor per condition.** Worlds are shared: run.seed 1 and game_idx 0..n-1, which are G1's
  worlds. Every world has three branches:
  - **God** (A);
  - **noGod** control (B);
  - **B″, fork-matched noise:** a God-free copy of B that keeps B's game_id and seeds before
    round F, then resamples every agent from F on. F is God's first scheduled round.
    `runner.fork.noise_fork` sets `run.resample_from_round`=F. From F on, agent seeds use the
    replica tag `0@rF`, so cache keys differ and responses are fresh.
- **Why B″** (lead, from planA-viz's G1 divergence figure, plan/figs/fig_divergence.png):
  - In G1 the noise replica B′ diverges from B almost completely, and the G1 God effect is null.
  - Sampling noise alone produces near-total divergence. A Δ or a divergence is only meaningful
    against a noise baseline that forks **at the same round** as God.
  - **Where G1's B′ forks (checked in code and logs):** B′ differs from B only in `run.replica`
    ("1"), and `derive_seed(..., replica=...)` is folded into every agent seed. So B′'s seeds and
    cache keys differ from round 1: B′ forks at r1, while God forks at r3.
  - **Primary God effect:** per world, (A − B) − (B″ − B) = A − B″. Outcome deltas A − B and the
    noise delta B″ − B are reported alongside.
- **Fresh stream, verified:**
  - FakeLLM: B″ seeds equal B's before F and differ at F and after, for every call
    (`infra/sweep.py dry` checks this).
  - Real run, `b2_sweep_base` g00 r3: 0 of 10 responses identical to G1's control.
  - Seeds are only partly honoured by the provider. B″ changes the seed itself, which also changes
    the cache key, so B″ is never served the control's cached response.
- **God-only conditions** (start round, K, base) set `runner.fork.control_god` = G1's god:
  - The control is exactly G1's nogod game (same game_id, seeds and config hash; verified for
    seeds 0-7). It replays from the LLM cache.
  - The God branch replays G1's cached prefix up to its first intervention.
  - **Caveat:** responses with empty text, from a finish=length cut, were never cached. 3 of G1's
    16 nogod games re-sample from r6, r8 and r6 in a replay. From there the control is a fresh
    continuation, and every Δ uses the cell's own control dir.
  - k1, k4 and base share the same control world and the same F=3, so **one B″@r3 serves G1, k1
    and k4**.
  - start1's F=1 B″ is exactly what G1's B′ already is: a God-free resample from r1. It is used
    instead of a new run.
- **Game conditions** (board, keys, N, rounds) change the world or rules and get their own
  control. B″@r3 comes from the cell itself.
- **Provider:** every call now logs `response.provider`. The B″ runs show PrimeIntellect in the
  first calls.
  - The serving provider was **not logged** before tonight (stage 1 and the grid), so G1's main
    provider cannot be identified. A pin knob exists (`llm.openrouter.provider_order` +
    `allow_fallbacks`, default off, hashed when set).
  - Tonight's runs stay unpinned, because their God and noGod branches were unpinned. Pinning only
    B″ would add a provider confound.
  - Tomorrow: pin a single provider for every branch of a fresh sweep.
- **Stats:**
  - mean Δ with a **t-based 95% CI (t95)** and an exact **sign-flip p**, plus the bootstrap CI
    (too narrow at n ≤ 8, per planA-review);
  - n is given per cell, and n < 8 is flagged;
  - an unhealthy seed is dropped whole: > 10% call errors, > 30% error-noop turns, or
    budget_exceeded;
  - independence comes from different worlds (game_idx), not from renamed runs.

## 2. New knobs (all default off = original behaviour, hash-neutral at defaults, tested)

| knob | where | effect | tests |
|---|---|---|---|
| `runner.fork.control_god` | spec.py | control and id_hash built from this god section (reuses a base cell's control games) | tests/runner/test_spec.py |
| `runner.fork.noise_fork`, `run.resample_from_round` | spec.py, llm_agent.py | adds B″ (branch `noisefork`) | test_spec.py (spec + real `LLMAgent._request` seeds) |
| `runner.fork.only_branches` | spec.py | run only some branches (add B″ to finished pairs) | used by `infra/sweep.py launch --only-branches` |
| `game.board.enabled` | config, rules.py, system.j2 | false: post_board not offered and fails `board_disabled`; no board in observations or prompts | tests/game/test_board_sweep_knobs.py (sim and seq) |
| `game.board.visible_delay_rounds` | config, observe.py, system.j2 | others see a post k rounds later than normal, in the board view, view_log and grep | same (k=1,2, sim and seq) |
| `llm.openrouter.provider_order`, `allow_fallbacks` | openrouter.py, wiring.py | provider pin | tests/llm/test_openrouter.py |
| `ChatResponse.provider` | schema, openai_compat.py | serving provider logged per call | same |

Checks on the new knobs:
- Rendered prompts are byte-identical at defaults. system.j2 was diffed old vs new for the
  default, G1, anonymous, skip3 and costs-turn configs.
- The prompt-set hash recorded in manifests and events changes, because the template file changed.
- G1/G3 game ids are unchanged (48/48, 32/32).
- Global ledger cap is now $8, hashed as a fixed value.

## 3. Conditions (`configs/sweep/<cond>.yaml`, generated by `python infra/sweep.py write`)

Priority order (lead): 1 start round, 2 board, 3 K, 4 N, 5 keys, 6 rounds.

| cond | factor | change vs G1 | F (B″ fork) |
|---|---|---|---|
| base | start | G1 design (fraud r3, cot r5): adds B″ to G1's worlds | 3 |
| start1 / start8 / start14 | start | fraud r, cot r+2, start_round r (r = 1, 8, 14) | 1 / 8 / 14 |
| board_off | board | `game.board.enabled: false` | 3 |
| board_delay2 | board | `game.board.visible_delay_rounds: 2` | 3 |
| board_anon | board | `game.board.anonymous: true` | 3 |
| board_skip3 | board | `game.board.post_skip_rounds: 3` (a post costs the next 3 turns) | 3 |
| k1 / k4 | K | K=1: fraud r3. K=4: fraud r3, cot r4, fraud r5, cot r6 (G3's first four acts; K=6 = G3) | 3 |
| n5 / n20 | N | 5 or 20 agents | 3 |
| keys3 / keys8 | keys | 3 or 8 keys per agent (needs 3, copies 2; world feasibility checked) | 3 |
| r40 | rounds | 40 rounds | 3 |

**FakeLLM dry runs: all 15 conditions PASS** (`python infra/sweep.py dry all --rounds 16 --seeds 2`,
$0). The checks run on the logs, with 2 worlds × 3 branches each:
- God powers fire exactly at the scheduled rounds (K = their number), and only in the God branch.
  Examples: start14 [(14, fraud), (16, cot)]; k4 [(3, fraud), (4, cot), (5, fraud), (6, cot)].
- All three branches share a game_id.
- B″ seeds equal the control's before F and all differ from F on.
- n_agents, max_rounds and rounds_played match the condition.
- The world has keys_per_agent keys per agent and is feasible.
- board_off: 22 attempted posts all failed `board_disabled`, there are 0 board messages, no board
  items in any observation, and no post_board in the system prompt.
- board_delay2: every post is first seen exactly 3 rounds after it was posted (1 normal + 2),
  against 1 at the default.
- board_anon: no sender is ever shown.
- board_skip3: nobody takes a turn within 3 rounds of posting.

## 4. Cost model, budget and runtime

`infra/sweep.py`, `call_cost`:
- per-call cost(r) = price × (min(686 + 49·N·(r−1), 16500) prompt tokens × $0.0142/M + 350
  output × $0.0445/M);
- calls per branch-round = N.

| check | model | measured |
|---|---|---|
| price 1.06, N=10, 20 rounds, per branch | $0.0187 | $0.0177 (G1: $0.85 for 48 branches; about $0.0009 per branch-round) |
| N=20, pair | $0.166 | smoke $0.147 |
| N=5, pair | $0.0144 | smoke $0.0146 |

- Projections use **price 1.35**. Tonight's smokes and G3 paid 1.35-1.6× the fitted price
  (fallback providers), against G1's 1.06×.
- Hard cap per cell = 1.25 × projection (`llm.budget_usd`, passed per cell by the driver
  `--cap-override`).
- Runtime assumes about 7 s mean latency, so about 1.1 calls/s per 8 concurrent calls.

### Tonight (≤ $2.30 total; the ledger was $5.06 before the sweep)

| run | seeds | branches paid | projected | hard cap | spent so far / final |
|---|---|---|---|---|---|
| smokes (seed 0 of k1, n5, n20; reused) | 1 | | | $0.35 | $0.192 |
| `sweep_start1` (2 false starts included) | 8 | God (control = G1 cache) | $0.22 | $0.27 | $0.167 final |
| `sweep_start8`, `sweep_start14` | 8 | God | $0.19, $0.12 | $0.23, $0.15 | running / queued |
| `sweep_k1`, `sweep_k4` | 8 | God | $0.18, $0.22 | $0.21, $0.26 | queued |
| `sweep_n20` | 6 | God + own control | $0.74 | $0.86 | running |
| `sweep_n5` | 8 | God + own control | $0.10 | $0.125 | queued |
| B″: `b2_sweep_base`, `b2_sweep_start8`, `b2_sweep_start14` | 8 | B″ only | $0.19, $0.16, $0.10 | $0.24, $0.21, $0.13 | running |

Expected total ≈ $2.1-2.2. Guards:
- Driver NF stops at ledger **$7.35** (= $5.06 + $2.30).
- Every driver stops at **$7.80**.
- Per-cell hard caps apply.

Cut tonight (no money): the four board variants, keys, rounds. Board is the first thing to run
if N=20 is stopped. The lead decides; N=20 would free about $0.5, enough for board_off at 6 seeds.

### 5. Full plan for tomorrow (ranked; projected at price 1.35 with B″, `python infra/sweep.py list`)

| priority | cond | 6 seeds | 8 seeds | B″-only add-on for an existing pair (8 seeds) | calls (6 seeds) | wall time at 8 concurrent |
|---|---|---|---|---|---|---|
| 1 | base | $0.31 | $0.41 | $0.19 (running tonight) | 3.2k | 0.8 h |
| 1 | start1 | $0.32 | $0.43 | (G1 B′) | 3.6k | 0.9 h |
| 1 | start8 | $0.27 | $0.36 | $0.16 (tonight) | 2.3k | 0.6 h |
| 1 | start14 | $0.18 | $0.24 | $0.10 (tonight) | 1.3k | 0.3 h |
| 2 | board_off / delay2 / anon / skip3 | $0.44 each | $0.58 each | | 3.4k each | 0.8 h each |
| 3 | k1 / k4 | $0.31 each | $0.41 each | (B″ = base's) | 3.2k each | 0.8 h each |
| 4 | n5 | $0.14 | $0.18 | $0.06 | 1.7k | 0.4 h |
| 4 | n20 | $1.47 | $1.96 | $0.65 | 6.7k | 1.6 h |
| 5 | keys3 / keys8 | $0.44 each | $0.58 each | | 3.4k each | 0.8 h each |
| 6 | r40 | $1.51 | $2.02 | $0.67 | 7.0k | 1.7 h |

- God-only rows count the control as replayed from the cache. Their K and start-round runs from
  tonight are reused, so only B″ is new.
- **All four board variants at 6 seeds cost $1.74.** That is the next $2.30 block once tonight's
  results are in. The order would be board (4 × 6 seeds, $1.74), then n5 B″ ($0.06), then keys
  (≈$0.87).
- N=20 and 40 rounds are expensive ($1.5 each at 6 seeds) and come last.

## 6. Commands

```bash
cd ~/projects/swarm_hackathon
PYTHONNOUSERSITE=1 conda run -n swarm python infra/sweep.py list            # table above
PYTHONNOUSERSITE=1 conda run -n swarm python infra/sweep.py write           # configs/sweep/*.yaml
PYTHONNOUSERSITE=1 conda run -n swarm python infra/sweep.py dry all         # FakeLLM + log checks, $0
# paid (reads the key file itself; never prints it); --dry-run prints the plan and the driver command
PYTHONNOUSERSITE=1 conda run -n swarm python infra/sweep.py launch board_off board_delay2 board_anon board_skip3 \
    --seeds 6 --tag BOARD --dry-run
# B'' only, for pairs that already exist (as run tonight):
PYTHONNOUSERSITE=1 conda run -n swarm python infra/sweep.py launch base start8 start14 \
    --only-branches noisefork --run-prefix b2_ --seeds 8 --tag NF
# analysis
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.sweep_stats --seeds 0-7 --json plan/figs/sweep_stats.json ...
PYTHONNOUSERSITE=1 conda run -n swarm python infra/sweep/plot.py plan/figs/sweep_stats.json plan/figs
```

Stage 1 was launched before `infra/sweep.py` existed:
- it used `configs/sweep_*.yaml` from `infra/sweep/make_configs.py` (the same cells without B″)
  and `infra/sweep/launch.sh`;
- the commands are in git history (cdd3f7b);
- those configs are removed once driver A has finished. `configs/sweep/<cond>.yaml` produces the
  same God and control games (same config hashes, verified) plus B″.

## 7. Abort conditions

The watchdog is `infra/grid_driver.py`, checking every 10 s and logging to `runs/sweep_driver.log`:
- MemAvailable < 15 GB;
- more than 20 rg processes;
- ledger ≥ $7.80 (driver NF and new launches: $7.35);
- live projected cell cost > the cell's cap (after 150 paid calls);
- LLM errors > 5% or any HTTP 400;
- parse failures > 10%;
- finish=length > 5%;
- per branch: > 10% call errors or > 30% error-noop turns.

Driver fix made during the run: a cell counts only the ledger spend since its own launch. A
relaunched run id replays its earlier calls for free, and counting the old spend inflated the
projection; it nearly caused a false abort at 03:28.
