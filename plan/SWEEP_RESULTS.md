# SWEEP_RESULTS: one-factor sweeps around G1, God vs noGod vs fork-matched noise (2026-11-07, 03:10-05:21 EST)

The design, knobs, incidents and costs are in `plan/SWEEP_PLAN.md`.
- Numbers: `plan/figs/sweep_stats.json` and `plan/figs/sweep_stats.txt`, from
  `swarm/analysis/sweep_stats.py --seeds 0-7`.
- Figures: `plan/figs/sweep_*.png` (`infra/sweep/plot.py`).
- Tables: `infra/sweep/results.py`.

All numbers are real. n = number of worlds (paired, game_idx 0-7 = G1's worlds 0-7). Every CI is a
Student-t 95% CI (t95) with an exact sign-flip p. The percentile bootstrap is in the JSON and is too
narrow at this n.

## TL;DR

1. **No condition shows a God effect on welfare distinguishable from fork-matched sampling noise.**
   - Every A−N (God − B″) t95 contains 0. This holds for start round 1/3/8/14, K 1/2/4, and board off.
   - The smallest p is **K=1: −0.104, t95 [−0.213, +0.005], p=0.062, n=8**.
   - About 8 primary tests were run with no multiple-comparison correction, so this is not
     evidence.
   - At n=8 the A−N MDE is about 0.15-0.25 welfare. Only large effects are excluded.
2. **Divergence is not a God signal.**
   - Resampling all agents at God's round (B″) makes 0.80-0.95 of agents act differently from
     noGod in every post-fork round.
   - God's one-agent perturbation reaches *less*: 0.65-0.92.
   - The gap God − B″ is negative in every cell, and the t95 excludes 0 for base, start8,
     start14, K=1 and K=4 (p ≤ 0.016).
   - So "God changed behaviour" claims based on divergence are confounded by sampling chaos.
   - B″ resamples all 10 agents while God touches one input, so B″ is an upper bound on noise.
     The tighter control is to resample only the victim (next step).
3. **The fork point of the noise baseline matters only a little for welfare.** On G1's worlds:
   - B′ (forks at r1): N−B = −0.000, t95 [−0.199, +0.199];
   - B″ (forks at r3): N−B = +0.054, t95 [−0.050, +0.158].
   - The B″ CI is half as wide, because the shared prefix removes early noise.
4. **Turning the board off is a big game-design effect, independent of God.**
   - With no God, welfare drops by **−0.200, t95 [−0.333, −0.067], sign-flip p=0.031, n=6 (low n)**,
     against G1's noGod on the same worlds.
   - All 6 worlds are negative. The board carries 4-9 posts per agent per game in G1.
   - In those worlds God's effect stays null: A−N +0.056 [−0.170, +0.281].
5. **Late God is tightly null.** God first acting at r14 gives A−N −0.025, t95 [−0.080, +0.030]. By
   r14 most agents have already won or are locked in.

## Cells (all healthy: 0 LLM errors and 0 parse failures)

| cond | God | God/noGod run | noise run (branch, fork) | worlds | sweep cost |
|---|---|---|---|---|---|
| base (= G1) | fraud r3, cot r5 | `grid_oss_sim_k2` (existing) | `b2_sweep_base` (B″@r3) | 0-7 | $0.136 |
| start1 | fraud r1, cot r3 | `sweep_start1` | G1 B′ (`grid_oss_sim_k2`, noise@r1 ≡ fork-matched) | 0-7 | $0.167 |
| start8 | fraud r8, cot r10 | `sweep_start8` | `r3b2_sweep_start8` (B″@r8) | 0-7 | $0.132 + $0.157 |
| start14 | fraud r14, cot r16 | `r3_sweep_start14` | `r3b2_sweep_start14` (B″@r14) | 0-7 | $0.074 + $0.099 |
| K=1 | fraud r3 | `sweep_k1` | `b2_sweep_base` (same control world, same F=3) | 0-7 | $0.175 |
| K=4 | fraud r3/r5, cot r4/r6 | `r3_sweep_k4` | `b2_sweep_base` | 0-7 | $0.134 |
| K=6 (= G3) | fraud r3/5/7, cot r4/6/8 | `grid_oss_sim_k6` (existing) | none | 0-7 | (grid) |
| board_off | G1's | `sweep_board_off` | `b2_sweep_board_off` (B″@r3) | 0-5 | $0.164 + $0.079 |
| N=5 | G1's | `r3_sweep_n5` | none (budget) | 0-7 | $0.085 + $0.015 smoke |
| N=20 | G1's | `sweep_n20` | none (budget) | 0-3 (low n; worlds 4-5 crashed, see the plan's incidents) | $0.577 + $0.147 smoke |

**God fired exactly as configured in every real God branch** (god_power events, worlds 0-7, all ok):
- start1: r1 + r3;
- start8: r8 + r10;
- start14: r14 + r16;
- K=1: r3;
- K=4: r3, r4, r5, r6;
- board_off and N=5/20: r3 + r5.

**B″ forks exactly at F in every world:** the first round where any agent's actions differ from the
control is 3/3/3/3/3/3/3/3 (base), 8×8 (start8), 14×8 (start14) and 3×6 (board_off). Before F the
prefix is identical (cache), and after F the responses are fresh (seed tag `0@rF`; 0 of 10 r3
responses identical in `b2_sweep_base` g00).

**Spend:**
- **Sweep total $2.142** (≤ $2.30), including $0.192 of smokes and about $0.11 of stopped or
  partial runs (re-run from the cache).
- The ledger went from $5.06 to $7.20 (< $7.80).
- Per run id: `python3 -c` over `runs/openrouter_ledger.jsonl` (in SWEEP_PLAN §4).

## Results by factor

Column key:
- **A−N** = God − fork-matched noise (primary);
- A−B = God − noGod;
- N−B = noise − noGod;
- div = post-fork mean share of agents acting differently from noGod (God / noise), with the gap
  (t95, p).

Welfare levels are means over the same worlds. The `base` row repeats in each table as the
reference (K=2, start r3, board on, N=10).

### God's first intervention round

| cond | n | welfare God / noGod / noise | **A−N welfare** (t95, p) | A−B welfare | N−B welfare | A−N win rate | A−N defects/agent | A−N board posts/agent | div God / noise (gap) |
|---|---|---|---|---|---|---|---|---|---|
| start1 | 8 | 0.475 / 0.467 / 0.458 | +0.017 [-0.147, +0.180] p=0.86 | +0.008 [-0.143, +0.160] p=0.97 | -0.008 [-0.203, +0.186] p=0.94 | +0.075 [-0.102, +0.252] p=0.38 | -0.112 [-0.513, +0.288] p=0.61 | +0.11 [-1.65, +1.87] p=0.91 | 0.92 / 0.95 (-0.02 [-0.06, +0.01] p=0.12) |
| base | 8 | 0.450 / 0.458 / 0.512 | -0.062 [-0.207, +0.082] p=0.36 | -0.008 [-0.126, +0.110] p=0.94 | +0.054 [-0.050, +0.158] p=0.34 | -0.075 [-0.199, +0.049] p=0.28 | +0.100 [-0.119, +0.319] p=0.37 | +0.29 [-1.61, +2.19] p=0.78 | 0.90 / 0.95 (-0.04 [-0.07, -0.01] p=0.01) |
| start8 | 8 | 0.467 / 0.467 / 0.429 | +0.037 [-0.038, +0.113] p=0.36 | -0.000 [-0.103, +0.103] p=1.00 | -0.037 [-0.111, +0.036] p=0.33 | -0.013 [-0.176, +0.151] p=1.00 | +0.025 [-0.049, +0.099] p=0.75 | +0.32 [-0.27, +0.92] p=0.23 | 0.81 / 0.88 (-0.07 [-0.10, -0.04] p=0.01) |
| start14 | 8 | 0.454 / 0.467 / 0.479 | -0.025 [-0.080, +0.030] p=0.50 | -0.013 [-0.095, +0.070] p=0.80 | +0.013 [-0.077, +0.102] p=0.84 | +0.000 [-0.063, +0.063] p=1.00 | +0.000 [-0.077, +0.077] p=1.00 | -0.05 [-0.52, +0.42] p=0.84 | 0.65 / 0.80 (-0.15 [-0.23, -0.06] p=0.02) |

### Message board variant

| cond | n | welfare God / noGod / noise | **A−N welfare** (t95, p) | A−B welfare | N−B welfare | A−N win rate | A−N defects/agent | A−N board posts/agent | div God / noise (gap) |
|---|---|---|---|---|---|---|---|---|---|
| base | 8 | 0.450 / 0.458 / 0.512 | -0.062 [-0.207, +0.082] p=0.36 | -0.008 [-0.126, +0.110] p=0.94 | +0.054 [-0.050, +0.158] p=0.34 | -0.075 [-0.199, +0.049] p=0.28 | +0.100 [-0.119, +0.319] p=0.37 | +0.29 [-1.61, +2.19] p=0.78 | 0.90 / 0.95 (-0.04 [-0.07, -0.01] p=0.01) |
| board_off | 6 (low n) | 0.294 / 0.272 / 0.239 | +0.056 [-0.170, +0.281] p=0.69 | +0.022 [-0.162, +0.207] p=0.88 | -0.033 [-0.164, +0.098] p=0.69 | +0.183 [-0.009, +0.376] p=0.12 | -0.167 [-1.031, +0.698] p=0.81 | +0.00 [+0.00, +0.00] p=1.00 | 0.88 / 0.94 (-0.06 [-0.10, -0.02] p=0.06) |

### God budget K (interventions per game)

| cond | n | welfare God / noGod / noise | **A−N welfare** (t95, p) | A−B welfare | N−B welfare | A−N win rate | A−N defects/agent | A−N board posts/agent | div God / noise (gap) |
|---|---|---|---|---|---|---|---|---|---|
| k1 | 8 | 0.408 / 0.467 / 0.512 | -0.104 [-0.213, +0.005] p=0.06 | -0.058 [-0.126, +0.010] p=0.12 | +0.046 [-0.059, +0.151] p=0.50 | -0.075 [-0.215, +0.065] p=0.38 | +0.100 [-0.123, +0.323] p=0.37 | +1.10 [-0.32, +2.52] p=0.14 | 0.89 / 0.95 (-0.06 [-0.09, -0.03] p=0.01) |
| base | 8 | 0.450 / 0.458 / 0.512 | -0.062 [-0.207, +0.082] p=0.36 | -0.008 [-0.126, +0.110] p=0.94 | +0.054 [-0.050, +0.158] p=0.34 | -0.075 [-0.199, +0.049] p=0.28 | +0.100 [-0.119, +0.319] p=0.37 | +0.29 [-1.61, +2.19] p=0.78 | 0.90 / 0.95 (-0.04 [-0.07, -0.01] p=0.01) |
| k4 | 8 | 0.462 / 0.467 / 0.512 | -0.050 [-0.178, +0.078] p=0.45 | -0.004 [-0.100, +0.092] p=1.00 | +0.046 [-0.059, +0.151] p=0.50 | +0.000 [-0.100, +0.100] p=1.00 | +0.125 [-0.123, +0.373] p=0.31 | -0.43 [-1.92, +1.07] p=0.54 | 0.89 / 0.95 (-0.05 [-0.09, -0.02] p=0.01) |
| k6 | 8 | 0.500 / 0.446 / – | – | +0.054 [-0.110, +0.218] p=0.47 | – | – | -0.075 [-0.310, +0.160] p=0.55 | -0.45 [-1.89, +0.99] p=0.53 | 0.88 / –  |

### Number of agents N

| cond | n | welfare God / noGod / noise | **A−N welfare** (t95, p) | A−B welfare | N−B welfare | A−N win rate | A−N defects/agent | A−N board posts/agent | div God / noise (gap) |
|---|---|---|---|---|---|---|---|---|---|
| n5 | 8 | 0.483 / 0.508 / – | – | -0.025 [-0.199, +0.149] p=0.83 | – | – | +0.050 [-0.421, +0.521] p=0.88 | -0.50 [-2.05, +1.05] p=0.48 | 0.90 / –  |
| base | 8 | 0.450 / 0.458 / 0.512 | -0.062 [-0.207, +0.082] p=0.36 | -0.008 [-0.126, +0.110] p=0.94 | +0.054 [-0.050, +0.158] p=0.34 | -0.075 [-0.199, +0.049] p=0.28 | +0.100 [-0.119, +0.319] p=0.37 | +0.29 [-1.61, +2.19] p=0.78 | 0.90 / 0.95 (-0.04 [-0.07, -0.01] p=0.01) |
| n20 | 4 (low n) | 0.463 / 0.375 / – | – | +0.088 [-0.170, +0.345] p=0.38 | – | – | +0.012 [-0.164, +0.189] p=1.00 | -0.76 [-2.29, +0.77] p=0.25 | 0.84 / –  |

Notes on the tables:
- **K=6 (G3), N=5 and N=20 have no noise arm.** There was no money for a B″, so only A−B is shown.
  Read them against base's N−B (+0.054, t95 ±0.10): no A−B there is outside the noise range.
- The `div` column for those cells is God's divergence only.
- `board_off` board posts are 0 by construction; all posts failed with `board_disabled`, and
  none were made.
- `base` uses G1's worlds 0-7 only. G1's full 16-world numbers are in plan/GRID_RESULTS.md and are
  not re-computed here.

### Figures (plan/figs/)

| factor | Δwelfare (filled A−N, hollow A−B, t95) | divergence (filled God, hollow noise) |
|---|---|---|
| God first round | `sweep_start_welfare.png` | `sweep_start_divergence.png` |
| board | `sweep_board_welfare.png` | `sweep_board_divergence.png` |
| K | `sweep_k_welfare.png` | `sweep_k_divergence.png` |
| N | `sweep_n_welfare.png` | `sweep_n_divergence.png` |

Keys and rounds were not run (no money); their configs and dry runs are ready (SWEEP_PLAN §5).

## Caveats

- **Low power.** n=8 (6 for board_off, 4 for N=20). The A−N t95 half-widths are 0.06-0.22. A null
  here means "no large effect", nothing more. There is no correction for about 8 primary tests;
  the cells are exploratory.
- **B″ resamples every agent at F.** It is a conservative, upper-bound noise control. A God effect
  smaller than "resample everyone once" is not distinguishable here, and God's own divergence sits
  *below* it. The tighter control is to resample only God's victim(s) at F, with a new knob: a
  per-agent resample list.
- **Provider mix.** The serving provider was logged only from 03:52 on, and every logged sweep
  call went to PrimeIntellect or Near AI (10,553 vs 344). Stage-1 God and control branches
  (about 20k calls) are unlogged.
  - G3 got only 36% from the cheap provider (grid analysis), so a provider confound between
    branches cannot be excluded for stage 1.
  - Tomorrow: pin one provider for every branch (`llm.openrouter.provider_order` +
    `allow_fallbacks: false`).
- **Shared controls.** The God-only cells reuse G1's control games via the cache. Where G1's control
  hit an uncacheable empty response (3 of 16 worlds, from r6 or r8), the cell's control is a fresh
  continuation from there. Every Δ uses the cell's own control dir, so the pairing is intact.
- **start1's noise arm is G1's B′.** It is the identical construction (resample from r1) with a
  different replica id. It comes from a separate run, but the world, seeds and control are the same.
- **K=1/K=4 share base's B″.** It is the same control world and the same F=3, so it is exactly the
  right baseline. Their A−N values are correlated with base's.
- **board_off changes the game,** so its control is its own (not G1's). The −0.200 board main effect
  compares two control branches on the same worlds with different agent seeds.
- **N=20:** 2 of 6 worlds were lost to the template crash (SWEEP_PLAN incident 2).
