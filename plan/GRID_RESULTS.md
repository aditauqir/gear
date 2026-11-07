# GRID_RESULTS: gpt-oss-120b God vs no-God grid (N=10, 20 rounds)

All numbers come from the run dirs below and `runs/openrouter_ledger.jsonl`. They were produced by:
- `python -m swarm.analysis.grid_results --g1 runs/grid_oss_sim_k2 --g2 runs/r2_grid_oss_seq_k2 --g3 runs/grid_oss_sim_k6`
  (10k bootstrap resamples, rng seed 0);
- `python -m swarm.analysis.invariants runs/<cell>`;
- the health scan described in §2.

Design and abort rules are in `plan/GRID_PLAN.md`.

## Headline

**Neither K=2 nor K=6 had a detectable effect of God on any outcome.**
- None of the cells (sim K=2, seq K=2, sim K=6) shows one.
- Neither contrast (dose K=6 vs K=2, turn mode seq vs sim) shows one.
- Every welfare CI contains 0.
- The only nominally interesting result is "needs lost to wrong defects" in the mode contrast:
  seq − sim = −0.113, t95 [−0.207, −0.018], but sign-flip p = 0.062 at n=8, with no correction
  across about 27 tests. Treat it as noise.
- Within a few rounds of God's first act, almost every agent's actions differ between the God and
  no-God branches. That divergence (0.89) is close to the independent-replica noise level (0.97).
  God perturbs the swarm, but the outcome changes are indistinguishable from sampling noise at
  these n.

## 1. Cells as run

All cells share these settings:
- worlds run.seed 1, game_idx 0..n−1, so all cells play the same worlds;
- N=10, 20 rounds, paired fork (rounds 1-2 shared through the cache);
- openai/gpt-oss-120b, `reasoning_effort: low`, `provider_sort: price`, agent max_tokens 1000;
- `reasoning.salvage_truncated: true`.

| cell | run dir | turn mode | God | seeds (kept) | branches | cost (ledger) | wall |
|---|---|---|---|---|---|---|---|
| G1 | `runs/grid_oss_sim_k2` | simultaneous | K=2: fraud r3, cot_control r5 | 16 (16) | god, nogod, noise B′ = 48 | $0.8508 | 06:56-07:49Z (52 min) |
| G2 | `runs/r2_grid_oss_seq_k2` | sequential | K=2, same schedule | 8 (8) | god, nogod = 16 | $0.3431 (+$0.0075 for the aborted 10-seed attempt) | 07:03-08:07Z (64 min) |
| G3 | `runs/grid_oss_sim_k6` | simultaneous | K=6: fraud r3/r5/r7, cot r4/r6/r8 | 16 (16) | god, nogod = 32 | $0.7849 | 07:49-08:19Z (30 min) |

- **Spend:** the grid cost **$1.9863** in total, against hard caps of $2.84. The ledger total after the
  grid and the seed probe was $5.233.
- **G2 restart:** the first G2 launch (10 seeds, OpenRouter concurrency 8) was stopped by the
  watchdog's live cost projection ($0.66 > $0.55). It was relaunched as `r2_` with 8 seeds and
  concurrency 4, and its finished turns replayed from the cache.
- **Ran in parallel:** G2 with G1, then G2 with G3.
- **Commits:** the manifests record commits 49b0226 (G1), 7f12001 (G2) and abc72d1 (G3). All are
  dirty working trees because other agents' files were uncommitted. None of those edits touched
  configs these cells loaded.

## 2. Health

| | G1 | G2 | G3 |
|---|---|---|---|
| LLM calls (paid / cache) | 9047 (8547 / 500) | 3039 (2705 / 334) | 6286 (5782 / 504) |
| errors / HTTP retries | 0 / 1 | 0 / 0 | 0 / 0 |
| parse failures (turns) | 0 / 8920 | 0 / 3000 | 0 / 6200 |
| turns with a parse retry | 37 (0.41%) | 8 (0.27%) | 25 (0.40%) |
| finish=length (truncation) | 39 (0.43%) | 13 (0.43%) | 30 (0.48%) |
| salvaged truncated replies | 8 | 5 | 8 |
| unhealthy branches (>10% errors or >30% error noops) | 0 | 0 | 0 |
| cost per paid call / per branch-round | $0.000100 / $0.00095 | $0.000127 / $0.00114 | $0.000136 / $0.00127 |
| latency p50 / p90 / max | 29.3 / 40.2 / 81 s | 19.8 / 28.5 / 59 s | 15.7 / 22.7 / 62 s |
| calls at the cheapest-provider price | 87% | 78% | 36% |
| calls at about 2.5-3.3× that price | 13% | 22% | 64% |

**Invariants:** `swarm.analysis.invariants` reports **0 violations** on all three cells (exit 0).
It checks order, keys, defects, scores, delays, obs, god, prompts and the fork prefix.

**Providers and quantization:**
- The call logs do not record the serving provider. `response.model` is always
  openai/gpt-oss-120b.
- The ratio of realized cost to the cheapest list price shows two tiers.
  - **About 0.9×:** PrimeIntellect fp4 ($0.011/M in, $0.041/M out) is the only provider at this price.
  - **About 2.5-3.3×:** this matches the $0.03/M-input providers. Near AI fp4, CoreWeave fp4 and
    AkashML fp4 are at $0.15-0.19/M out, DekaLLM bf16 at $0.18/M out, and Venice int4 at $0.15/M
    out. Which of these served a given call can't be determined.
- **Confound:** the provider mix differs by cell. G3 ran 64% on fallback providers, against 13% for
  G1, which is a possible confound for the K=6 vs K=2 contrast.

**Seeds:** they cannot be checked from the grid logs, because an identical request in two branches
is always deduplicated by the cache or single-flight. A direct probe ($0.0006, run_id
`probe_oss_seed`, the round-10 prompt, temperature 0.6) gave:
- **seed 7, PrimeIntellect pinned and sort=price:** 5 of 6 calls returned byte-identical replies
  and 1 differed;
- **seed 8, two calls:** two different replies.

So seeds are **honoured only partly** (likely batching non-determinism), even on one provider.

## 3. Paired God effect per cell (Δ = God − noGod per seed)

How to read the tables below:
- Primary: mean Δ, Student-t 95% CI, and a two-sided sign-flip p (exact for n ≤ 16). Secondary:
  the percentile bootstrap 95% CI.
- `lost` = needs lost to the wrong-defect penalty, per agent.
- gives, defects_ok, board_posts and dms = successful actions per agent over the game.
- `div_post_fork` = mean fraction of agents whose round actions (kind, target, info_id) differ from
  the noGod branch from God's first act onward.
- `div_final_cum` = the fraction of agents that ever diverged.
- The divergence rows are measured against a zero baseline (noGod vs itself), so their p only says
  "the branches differ".

### G1: simultaneous, K=2 (n=16)
| metric | n | mean Δ | t95 CI | sign-flip p | bootstrap 95% |
|---|---|---|---|---|---|
| welfare | 16 | +0.013 | [-0.048, +0.073] | 0.721 | [-0.042, +0.065] |
| win_rate | 16 | -0.013 | [-0.103, +0.078] | 0.883 | [-0.094, +0.069] |
| lost | 16 | +0.044 | [-0.018, +0.105] | 0.227 | [-0.000, +0.100] |
| gives | 16 | +0.069 | [-0.718, +0.855] | 0.869 | [-0.644, +0.762] |
| defects_ok | 16 | +0.050 | [-0.043, +0.143] | 0.338 | [-0.031, +0.138] |
| board_posts | 16 | -0.231 | [-0.971, +0.508] | 0.523 | [-0.906, +0.425] |
| dms | 16 | -1.163 | [-2.869, +0.544] | 0.170 | [-2.713, +0.325] |
| div_post_fork | 16 | +0.893 | [+0.879, +0.908] | 0.000 | [+0.880, +0.906] |
| div_final_cum | 16 | +1.000 | [+1.000, +1.000] | 0.000 | [+1.000, +1.000] |

### G1 noise baseline: B′ − noGod (n=16; B′ = no-God replica with different seeds)
| metric | n | mean Δ | t95 CI | sign-flip p | bootstrap 95% |
|---|---|---|---|---|---|
| welfare | 16 | +0.046 | [-0.055, +0.146] | 0.378 | [-0.042, +0.135] |
| win_rate | 16 | +0.019 | [-0.079, +0.116] | 0.785 | [-0.069, +0.106] |
| lost | 16 | +0.050 | [-0.079, +0.179] | 0.477 | [-0.069, +0.163] |
| gives | 16 | +0.287 | [-0.977, +1.552] | 0.641 | [-0.888, +1.387] |
| defects_ok | 16 | +0.063 | [-0.145, +0.270] | 0.584 | [-0.131, +0.231] |
| board_posts | 16 | -0.137 | [-1.141, +0.866] | 0.785 | [-1.019, +0.781] |
| dms | 16 | -1.763 | [-3.679, +0.154] | 0.071 | [-3.513, -0.106] |
| div_post_fork | 16 | +0.967 | [+0.955, +0.979] | 0.000 | [+0.956, +0.978] |
| div_final_cum | 16 | +1.000 | [+1.000, +1.000] | 0.000 | [+1.000, +1.000] |

How B′ differs from the God branch:
- B′ has a different replica id, so its game id and seeds differ from round 1 on. Its divergence
  is therefore not fork-matched. It is measured over the same post-fork rounds, but B′ already
  differs before the fork.
- The SD of the welfare Δ is 0.189 for B′ − noGod against 0.113 for God − noGod. God and noGod
  share game id and seeds (common random numbers), so their pairing is tighter than B′'s.

### G2: sequential, K=2 (n=8)
| metric | n | mean Δ | t95 CI | sign-flip p | bootstrap 95% |
|---|---|---|---|---|---|
| welfare | 8 | +0.012 | [-0.144, +0.169] | 0.891 | [-0.117, +0.121] |
| win_rate | 8 | +0.025 | [-0.107, +0.157] | 0.812 | [-0.088, +0.125] |
| lost | 8 | -0.062 | [-0.151, +0.026] | 0.250 | [-0.138, -0.000] |
| gives | 8 | +0.487 | [-1.226, +2.201] | 0.516 | [-0.688, +1.938] |
| defects_ok | 8 | +0.013 | [-0.151, +0.176] | 1.000 | [-0.113, +0.125] |
| board_posts | 8 | -0.675 | [-2.229, +0.879] | 0.297 | [-1.800, +0.575] |
| dms | 8 | -0.050 | [-1.463, +1.363] | 0.953 | [-1.162, +1.038] |
| div_post_fork | 8 | +0.897 | [+0.853, +0.940] | 0.008 | [+0.860, +0.928] |
| div_final_cum | 8 | +1.000 | [+1.000, +1.000] | 0.008 | [+1.000, +1.000] |

### G3: simultaneous, K=6 (n=16)
| metric | n | mean Δ | t95 CI | sign-flip p | bootstrap 95% |
|---|---|---|---|---|---|
| welfare | 16 | +0.004 | [-0.097, +0.105] | 0.965 | [-0.090, +0.090] |
| win_rate | 16 | -0.006 | [-0.098, +0.086] | 1.000 | [-0.081, +0.081] |
| lost | 16 | -0.031 | [-0.144, +0.082] | 0.640 | [-0.125, +0.075] |
| gives | 16 | -0.206 | [-0.911, +0.498] | 0.547 | [-0.812, +0.431] |
| defects_ok | 16 | -0.069 | [-0.205, +0.067] | 0.340 | [-0.181, +0.056] |
| board_posts | 16 | -0.306 | [-1.080, +0.468] | 0.440 | [-1.019, +0.363] |
| dms | 16 | -0.406 | [-2.175, +1.363] | 0.636 | [-1.994, +1.163] |
| div_post_fork | 16 | +0.882 | [+0.866, +0.898] | 0.000 | [+0.867, +0.896] |
| div_final_cum | 16 | +1.000 | [+1.000, +1.000] | 0.000 | [+1.000, +1.000] |

## 4. Contrasts (paired by world)

### Dose: G3 Δ − G1 Δ (K=6 vs K=2, simultaneous, n=16)
| metric | n | mean | t95 CI | sign-flip p | bootstrap 95% |
|---|---|---|---|---|---|
| welfare | 16 | -0.008 | [-0.118, +0.101] | 0.904 | [-0.104, +0.092] |
| win_rate | 16 | +0.006 | [-0.122, +0.135] | 1.000 | [-0.106, +0.125] |
| lost | 16 | -0.075 | [-0.216, +0.066] | 0.326 | [-0.200, +0.050] |
| gives | 16 | -0.275 | [-1.485, +0.935] | 0.643 | [-1.269, +0.881] |
| defects_ok | 16 | -0.119 | [-0.284, +0.047] | 0.169 | [-0.263, +0.037] |
| board_posts | 16 | -0.075 | [-1.070, +0.920] | 0.884 | [-1.000, +0.781] |
| dms | 16 | +0.756 | [-2.055, +3.567] | 0.581 | [-1.675, +3.312] |
| div_post_fork | 16 | -0.011 | [-0.032, +0.009] | 0.255 | [-0.029, +0.007] |

### Turn mode: G2 Δ − G1 Δ (seq vs sim, K=2, on the shared worlds 0-7, n=8)
| metric | n | mean | t95 CI | sign-flip p | bootstrap 95% |
|---|---|---|---|---|---|
| welfare | 8 | +0.021 | [-0.170, +0.212] | 0.859 | [-0.108, +0.183] |
| win_rate | 8 | +0.038 | [-0.186, +0.261] | 0.797 | [-0.138, +0.213] |
| lost | 8 | -0.113 | [-0.207, -0.018] | 0.062 | [-0.188, -0.038] |
| gives | 8 | +0.487 | [-2.152, +3.127] | 0.688 | [-1.438, +2.600] |
| defects_ok | 8 | -0.025 | [-0.238, +0.188] | 0.898 | [-0.200, +0.137] |
| board_posts | 8 | -0.763 | [-2.610, +1.085] | 0.375 | [-2.150, +0.687] |
| dms | 8 | +0.588 | [-2.186, +3.361] | 0.672 | [-1.625, +2.725] |
| div_post_fork | 8 | -0.006 | [-0.059, +0.048] | 0.891 | [-0.048, +0.035] |

### Per-branch means (all kept seeds)
| cell | branch | welfare | win_rate | lost | gives | defects_ok | board_posts | dms | div_post_fork |
|---|---|---|---|---|---|---|---|---|---|
| G1 | god | 0.452 | 0.819 | 0.356 | 6.775 | 0.831 | 6.625 | 12.844 | 0.893 |
| G1 | nogod | 0.440 | 0.831 | 0.312 | 6.706 | 0.781 | 6.856 | 14.006 | 0 |
| G1 | noise | 0.485 | 0.850 | 0.362 | 6.994 | 0.844 | 6.719 | 12.244 | 0.967 |
| G2 | god | 0.525 | 0.838 | 0.087 | 8.150 | 0.588 | 6.650 | 11.363 | 0.897 |
| G2 | nogod | 0.512 | 0.812 | 0.150 | 7.662 | 0.575 | 7.325 | 11.412 | 0 |
| G3 | god | 0.450 | 0.781 | 0.338 | 7.037 | 0.775 | 6.294 | 13.681 | 0.882 |
| G3 | nogod | 0.446 | 0.787 | 0.369 | 7.244 | 0.844 | 6.600 | 14.088 | 0 |

The no-God branches differ between cells (seq vs sim) for the descriptive comparisons below.
Their game ids differ, so they are separate samples of the same worlds.
- Seq: welfare 0.512 and wrong-defect losses 0.150 per agent.
- Sim: welfare 0.440 and losses 0.312 per agent.

This is not a God effect, and it rests on n=8 against n=16 without pairing on agent seeds.

## 5. Power achieved and caveats

**Observed SD of the welfare Δ and the resulting MDE** (80% power, α=0.05, two-sided t):

| comparison | n | observed SD | MDE |
|---|---|---|---|
| G1 | 16 | 0.113 | ≈ 0.085 |
| G3 | 16 | 0.189 | ≈ 0.14 |
| G2 | 8 | 0.188 | ≈ 0.22 |
| dose contrast | 16 | 0.206 | ≈ 0.15 |
| mode contrast | 8 | 0.228 | ≈ 0.26 |

The pre-registered planning SD was 0.19. Effects of God on welfare larger than about 0.09 (K=2,
sim) or about 0.14 (K=6, sim) are unlikely. The seq cell can rule out only large effects.

**Caveats:**
- **Multiple tests:** about 27 non-divergence tests in §3-4 with no correction. Only H1 (G1
  welfare) was primary.
- **Partial common random numbers:** seeds are honoured only partly (§2), and 13-64% of calls went
  to fallback providers of other quantizations. Post-fork divergence therefore mixes God's
  influence with provider and sampling noise. The independent replica B′ diverges at 0.97 vs
  God's 0.89.
- **Weak dose:** God's scripted powers are small relative to the world. K=2 means one forged DM
  and one scratchpad overwrite among 10 agents × 20 rounds. The victims are "closest to winning",
  who often win anyway.
- **One model and one size:** gpt-oss-120b at reasoning effort low, N=10 only. The earlier qwen
  n=1 hint (God −0.23 in sim, +0.20 in seq) did not replicate (G2 − G1 welfare: +0.021).
