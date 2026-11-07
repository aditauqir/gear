# GRID_PLAN: openai/gpt-oss-120b experiment grid

**Status (2026-11-07 01:56): LAUNCHED** by `infra/grid_driver.py`, under the lead's pre-approval
("go" if smoke passes, projection ≤ $2.40, hard caps ≤ $2.50, abort conditions wired,
simultaneous mode, concurrency ≤ 16).

What is running (§2a) differs from the first proposal (§2b):
- sim only, so the seq cell G2 was dropped;
- 16 seeds instead of 12;
- OpenRouter concurrency 16, with cells run one after another;
- `reasoning.salvage_truncated` on.

Cost:
- Projected $1.62 (central) to $2.11 (×1.3 margin).
- Hard caps: G1 $1.35 + G3 $0.95 = $2.30.
- The ledger was $3.07 before the grid, so it can reach at most $5.37. The driver stops at $5.70.

## 1. What the smoke measured (`runs/or_oss_10x10_sim`, current code post-8ebbee7 + 98cb469)

The smoke used `configs/grid_oss120b_base.yaml` with `game.max_rounds=10`: N=10, simultaneous
turns, seed 0, one paired God/no-God fork, and God K=2 (fraud in r3, cot_control in r5). The model was
openai/gpt-oss-120b with `reasoning_effort: low` and `provider_sort: price`.

| | God | no-God |
|---|---|---|
| calls (paid / single-flight cache) | 102 (102 / 0) | 102 (73 / 29) |
| cost | $0.00610 | $0.00527 |
| cost per paid call | $0.000060 | $0.000072 |
| cost per branch-round (r10 alone) | $0.00061 ($0.0012) | $0.00053 ($0.0009) |
| prompt tokens mean / max | 3224 / 6150 | 3965 / 6018 |
| completion mean / max (of which reasoning) | 350 / 738 (217) | 345 / 774 (216) |
| latency p50 / p90 / max | 5.5 / 17.9 / 31 s | 4.9 / 24.1 / 51 s |
| parse failures / turns with a retry | 0 / 100, 0 / 100 | 0 / 100, 0 / 100 |
| truncation (finish=length) | 0 / 102 | 0 / 102 |
| HTTP errors | 0 | 0 |
| wall time (10 rounds) | 180 s | 235 s |
| welfare / wins at r10 | 0.500 / 6 | 0.433 / 6 |
| gives / defects ok (correct) / DMs / board | 32 / 11 (7) / 72 / 44 | 34 / 12 (8) / 65 / 47 |

The whole run cost $0.0114 for 175 paid calls (ledger run_id `or_oss_10x10_sim`). Probes cost
$0.0003 more, so this task spent **$0.0116** in total.

- **Fitted realized price:** $0.0142/M input and $0.0445/M output. That is the cheapest provider's
  list price ($0.011 / $0.041) plus about 18%. A few calls fell back to dearer providers (p99 is 2.9×
  the cheapest).
- **Prompt growth:** about 550 tokens per round in sim mode (r1 686 → r10 5658). Prompts plateau at
  `context.budget_tokens` 14000 around r24.
- **Play quality is good.** Agents state their needs, offer specific trades and give keys. Gives
  happen at about 3× the qwen3.6 rate (32 gives in 10 rounds, against 32 in 30). Defects are
  mostly correct, and DMs are coherent. The forged DM was taken up but not obeyed blindly: the
  victim offered a trade and did not hand over a key first. The fallback model (`qwen/qwen3.7-flash`)
  was not needed.

Sampled agent outputs (God branch, `content` only; the native reasoning is logged separately):
- r2 sandy_jasper: `send_message → jade_piper: "I have key 7 (info 7) which you need. I'd trade it for any key you have for info 10, 16, or 19."`
- r4 quiet_grove, who received the round-3 forged DM: `"thought": "Need key for info 15. Lunar_dune promised info15 for a key. Offer my key 11."`, then `send_message → lunar_dune: "...my key for info 11 ... in exchange for the info 15 you offered"` plus a board post asking who holds 15.
- r8 fern_beacon: `"thought": "Need key24; only jade_piper has been asked. Send another private offer of key11 for key24."`

**Fixes the smoke needed (commit 98cb469 and the grid commit):**
- gpt-oss rejects `reasoning: {enabled: false}` with HTTP 400 ("Reasoning is mandatory"). The new
  `llm.openrouter.reasoning_effort` sends `{effort: low}` instead.
- The runner builds its OpenRouter client in `swarm/runner/wiring.py`, not through
  `registry.from_cfg`, so the knob also has to be passed there. The first smoke attempt missed that.
- **Danger found:** with every call failing (HTTP 400), the games still ended `status: done`. Every
  turn became a parse-failure noop, so a provider outage would silently produce junk games. This
  is why abort check A1 below exists.

## 2a. The grid as launched (sim only)

| cell | config | God | branches per seed | seeds | branches | projected (central / ×1.3) | hard cap |
|---|---|---|---|---|---|---|---|
| G1 | `configs/grid_oss_sim_k2.yaml` | K=2: fraud r3, cot r5 | god, nogod, noise B′ | 16 | 48 | $0.97 / $1.27 | $1.35 |
| G3 | `configs/grid_oss_sim_k6.yaml` | K=6: fraud r3/r5/r7, cot r4/r6/r8 | god, nogod | 16 | 32 | $0.65 / $0.84 | $0.95 |
| **total** | | | | **16 worlds** | **80** | **$1.62 / $2.11** | **$2.30** |

Settings shared by both cells:
- N=10, 20 rounds, simultaneous turns, run.seed 1, game_idx 0-15.
- OpenRouter concurrency 16. `max_concurrency_games` is 12 for G1 and 8 for G3.
- `reasoning.salvage_truncated: true`.

Hypotheses as launched:
- **H1:** G1 god − nogod.
- **H0:** the G1 noise floor (B′ − nogod).
- **H1′:** G3 god − nogod.
- **H3 (dose):** G3 Δ − G1 Δ, paired by world.
- H2 (sim vs seq) is **not tested**. `configs/grid_oss_seq_k2.yaml` exists for later.

Power at n=16 (planning SD of the paired Δ is 0.19):
- H1 and H1′: SE ≈ 0.048, MDE ≈ **0.14 welfare**.
- H3: SD ≈ 0.27, SE ≈ 0.067, MDE ≈ **0.20**.

Wall time: about 15k calls at 16 in flight and about 7-8 s mean latency gives ≈ 2-2.5 h, so
G1 then G3 should finish around 04:15.

**Launch command (as run):**
```bash
cd ~/projects/swarm_hackathon
OPENROUTER_API_KEY="$(cat "/home/iraj/projects/swarm_data?/.planAdemoenv")" PYTHONNOUSERSITE=1 \
  setsid nohup conda run -n swarm --no-capture-output python infra/grid_driver.py \
  --cell grid_oss_sim_k2:1.35:3 --cell grid_oss_sim_k6:0.95:2 --seeds 16 --rounds 20 \
  > runs/grid_driver.out 2>&1 < /dev/null &
```

**The driver's abort checks** (every 10 s; on abort it kills the cell's process group and starts
no further cells):
- MemAvailable < 15 GB;
- more than 20 rg processes;
- ledger ≥ $5.70;
- live projected cell cost > the cell cap, after 150 paid calls. The projection is spent × W_total
  / W_done, using the smoke's per-call cost model weighted by round;
- LLM errors > 5%, or any HTTP 400;
- parse failures > 10% of turns;
- finish=length > 5% of responses.

Status lines go to `runs/grid_driver.log`.

**Analysis:**
```bash
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.grid_stats runs/grid_oss_sim_k2 runs/grid_oss_sim_k6
```

## 2b. First proposal (before the sim-only constraint; kept for reference)

ARCHITECTURE_v2 §15 (58 games: N=20, sequential, K ∈ {1,3,10} × timing × power) is cut down to what
$2.40 buys at N=10. The trims:
- N=10 (the world size of every demo so far) instead of N=20.
- 20 rounds instead of 30-50. At r10 the smoke already had 6 of 10 agents winning, and 20 rounds
  costs half of 30 per seed.
- Fewer seeds per cell, more cells.

All cells use the same settings:
- `run.seed: 1` with `n_games: 12`, so game_idx 0-11. World seeds depend only on (run.seed,
  game_idx), so **all cells play the same 12 worlds**. Seed 0 was the dev/smoke seed and is excluded.
- Paired fork: God vs no-God share rounds 1-2 exactly (single-flight cache), then diverge.
- openai/gpt-oss-120b, reasoning low, provider sort price, agent max_tokens 1000, context 14000.

| cell | config | turn mode | God | branches per seed | seeds | branches | projected (central / ×1.3) | hard cap `llm.budget_usd` |
|---|---|---|---|---|---|---|---|---|
| G1 | `configs/grid_oss_sim_k2.yaml` | simultaneous | K=2: fraud r3, cot r5 (the demo design) | god, nogod, noise B′ | 12 | 36 | $0.73 / $0.95 | $1.00 |
| G2 | `configs/grid_oss_seq_k2.yaml` | sequential | same as G1 | god, nogod | 12 | 24 | $0.49 / $0.63 | $0.70 |
| G3 | `configs/grid_oss_sim_k6.yaml` | simultaneous | K=6: fraud r3/r5/r7, cot r4/r6/r8 | god, nogod | 12 | 24 | $0.49 / $0.63 | $0.70 |
| **total** | | | | | **12 worlds** | **84** | **$1.71 / $2.22** | **$2.40** |

How the projection is built:
- Per branch over 20 rounds: Σ_r 10 × min(686 + 550(r−1), 14000) prompt tokens = 1.18M tokens × $0.0142/M
  = $0.0168.
- Plus 200 calls × 350 output tokens × $0.0445/M = $0.0031, plus about 2% for grep follow-ups.
- That gives **$0.0203 per branch**, or about $0.04 per God/no-God pair.
- Seq games that end early (`all_done`) cost less.

### Hypotheses and comparisons

| | comparison | test | what it tests |
|---|---|---|---|
| H1 | G1 god − nogod, per seed | paired, n=12 | Does a K=2 God (one forged DM, one scratchpad overwrite) change welfare, win rate, burns and wrong-defect losses in sim mode? |
| H0 / noise | G1 noise − nogod | paired, n=12 | Noise floor: how far two God-free replays of the same world diverge from sampling alone. It calibrates H1 and the ripple metric (§12) |
| H2 | (G2 Δ) − (G1 Δ), paired by world | n=12 | Interaction of turn mode with God. The n=1 demo hint was God −0.23 in sim and +0.20 in seq |
| H3 | (G3 Δ) − (G1 Δ), paired by world | n=12 | Dose-response: does tripling the interventions (K 2 → 6) increase harm? |
| H1′ | G3 god − nogod | n=12 | God effect at the higher dose. If H1 is null at K=2, this is the best chance of seeing any effect |

Primary metric: welfare (mean score). Secondary: win rate, needs burned, needs lost, rounds played.
Victim-level outcomes (the targeted agent's final score and round of winning) come from
`swarm/analysis/outcomes.py`.

### Statistical power (stated before running)

- **SD of the paired delta Δwelfare** is unknown. The four n=1 deltas we have are −0.23 (qwen sim),
  +0.20 (qwen seq), +0.13 (qwen N=60) and +0.07 (oss smoke at r10). They give SD ≈ 0.19, and this is
  the planning value.
- **H1 at n=12:** SE ≈ 0.055. The MDE for 80% power, α=0.05 two-sided (t₁₁) is ≈ **0.17 welfare**,
  about 5 of the 30 needs.
- **H2 and H3** are differences of two deltas, with SD ≈ 0.27, SE ≈ 0.078 and MDE ≈ **0.24**. The
  demo's sim/seq gap of 0.43 would be detectable. A modest real interaction would not be.
- **Reporting:**
  - mean Δ with a 95% percentile bootstrap CI over seeds (10k resamples);
  - an exact two-sided sign-flip permutation p (4096 flips at n=12; smallest possible p ≈ 0.0005);
  - the B′ noise floor next to each Δ.
  - There is no multiple-comparison correction across the 5 tests. They are labeled
    exploratory, and only H1 is primary.
- **Honest framing:** this grid can detect large God effects (≥ 0.17 welfare) and large interactions
  (≥ 0.24). A null result means "no large effect", not "no effect".

### Considered and left out

- **Board options** (`anonymous`, `post_costs_turn`, `post_skip_rounds`): none of them tests a
  God hypothesis, and the demos only showed mechanics. Adding a cell at 12 seeds costs about $0.50,
  which does not fit. They are first in line if money is left.
- **Power split** (fraud-only vs cot-only): in the demos the cot_control overwrite had no visible
  effect (SIM60 §God). The dose cell G3 is the better use of $0.63. If H1′ is positive, a split is
  the follow-up.
- **N=20/60:** prompts and calls scale with N, so this is about 2.5-6× the cost per seed. Not
  affordable at a useful n.
- **Late God start** (`start_round` 15) and the LLM God: dropped for budget.

## 3. Run commands (first proposal; the launched command is in §2a)

Run from `~/projects/swarm_hackathon`. The key is exported only inside the command and never echoed.

```bash
cd ~/projects/swarm_hackathon
K="/home/iraj/projects/swarm_data?/.planAdemoenv"
run_cell() { OPENROUTER_API_KEY="$(cat "$K")" PYTHONNOUSERSITE=1 conda run -n swarm \
  python -m swarm.run --config "configs/$1.yaml" --run-id "$1" > "runs/$1.log" 2>&1; }

# 0. dry run (free): every cell, 2 seeds x 9 rounds, FakeLLM
for c in grid_oss_sim_k2 grid_oss_seq_k2 grid_oss_sim_k6; do PYTHONNOUSERSITE=1 conda run -n swarm \
  python -m swarm.run --config configs/$c.yaml --run-id fake_$c roles.agent.backend=fake \
  roles.god.backend=fake roles.judge.backend=fake roles.summarizer.backend=fake \
  llm.openrouter.enabled=false "llm.cache.mode='off'" runner.report=false game.max_rounds=9 run.n_games=2; done

# 1. G1 first (gives the SD estimate and the real cost per branch-round). Watch it with check A below.
run_cell grid_oss_sim_k2
# 2. if G1 passes the checks: G2 and G3 in parallel (separate processes; each has its own hard cap)
run_cell grid_oss_seq_k2 & run_cell grid_oss_sim_k6 & wait

# analysis
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.grid_stats \
  runs/grid_oss_sim_k2 runs/grid_oss_seq_k2 runs/grid_oss_sim_k6
```

The analysis prints H1/H1′ and the B′ noise floor per cell, plus H2 (seq − sim) and H3
(k6 − k2), each paired by world.

**Health check (A), during and after each cell:**
`PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.call_metrics runs/<cell>`.
It prints, per game: errors, finish reasons, cost per call and per round, parse-failure, retry and
truncation rates, and latency. `runs/<cell>/progress.txt` shows live progress and spend.

### Projected wall time

The smoke ran at about 20 s per sim round. Each round waits for its slowest call, and the
cheapest provider has slow tails (p90 18-24 s).
- **G1:** `max_concurrency_games` 12, so 4 seeds × 3 branches at a time. That is 3 waves × about
  9 min ≈ **30 min**.
- **G2 (seq):** 10 calls in series per round × about 7 s ≈ 70 s per round, or about 23 min per
  branch. All 24 branches run at once (`max_concurrency_games` 24, OpenRouter concurrency 32), so
  **≈ 30 min**.
- **G3:** 4 pairs at a time, 3 waves ≈ **30 min**.
- **Total ≈ 1 h**: G1, then G2 and G3 in parallel. Budget for 2 h if the provider throttles.

## 4. Abort conditions (pre-registered)

Stop the cell (Ctrl-C; finished games stay valid) and report to the lead if any of these holds:

- **A1. Errors.** Any game has more than 5% of its llm_calls with `error` set, or any HTTP 400 at
  all. Errors become silent noop turns, so the games would look `done` while being junk.
- **A2. Parse/truncation.** Parse failures above 10% of turns, or `finish=length` above 5% of calls,
  in any game after round 5.
- **A3. Cost rate.** Realized cost above **$0.002 per branch-round**, which is 2× the projection at
  the r10 level, averaged over the first 20 rounds completed. Stop and re-plan seeds or rounds; do
  not just raise caps.
- **A4. Caps.**
  - A cell hits its `llm.budget_usd`: games end with `end_reason: budget_exceeded`. Do not top up
    without the lead.
  - The global ledger reaches **$5.60**: stop everything, keeping $0.40 under the $6 cap.
- **A5. Throughput.** Wall time above 2× the projection (G1 > 60 min), or sustained 429s. Lower
  `llm.openrouter.max_concurrency` or `run.max_concurrency_games` and re-run. Finished games are
  re-run from the cache: `read_write` replays them at $0.
- **A6. Play sanity**, checked after the first G1 wave. Gives per game fall below 10, or agents
  mostly noop. That would mean a provider or model regression, so stop and inspect samples.

If G1 comes in under budget, the order for the money left is:
1. +4 seeds to G1 (`run.n_games=16`). Seeds 0-11 replay from the cache for free.
2. A board-option cell.
