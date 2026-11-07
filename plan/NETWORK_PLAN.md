# NETWORK_PLAN: first real runs with the social network (N=40, gpt-oss-120b)

**Status (2026-11-07 13:23 EST): RUNNING the final design (Iraj, 13:20: "do parallelism and 4 worlds and
shorten complete-graph").**

| cond | config | worlds | rounds | in flight | hard cap |
|---|---|---|---|---|---|
| A complete | `configs/net40_complete_sim.yaml` | 0-3 | **20** | 6 | $1.61 |
| B ER3 contacts | `configs/net40_er3_contacts_sim.yaml` | 0-3 | 30 | 5 | $1.06 |
| C ER3 known_ids | `configs/net40_er3_known_sim.yaml` | 0-3 | 30 | 5 | $1.24 |

All three cells run at once, 16 in flight in total. B and C use the same concurrency. Three
`infra/grid_driver.py` watchdogs log to `runs/network40_driver4_{A,B,C}.log`, with
`--max-fallback 0.5` (§6b). The fallback share per cell is in every status line.

**How the conditions are compared:**
- **Primary:** A vs B vs C at matched rounds (≤ 20), from the round-20 state of B and C.
- **Secondary:** B vs C at 30 rounds.

Results go to `plan/NETWORK_RESULTS.md`.

**Restart at 13:22 (safe, replays from the cache):**
- B kept its 4 worlds. Those games replay from the cache up to the stop (about round 11).
- **A had to start from scratch.** `game.max_rounds` is game semantics (it is in the config hash
  and in the prompt), so the 20-round A has new game ids. The 30-round A partial, at round 7 and
  $0.309 spent, is `runs/partial_net40_complete_sim_30r_1322`.
- Worlds 4-5 of A and B were stopped, kept in `runs/partial*_1322`, and are excluded from the
  analysis.

**Superseded designs:**
- **12:49-13:22:** N=40 × 30 rounds × 6 worlds at 4 + 4 in flight (§0-§6).
- **12:14-12:38:** N=20 × 40 rounds × 8 worlds (§7).

History. A first launch at N=20 × 40 rounds × 8 worlds (A, B, C, D; §7) started at 12:14. The
operator stopped it at 12:38 when the lead relayed Iraj's "maybe try 40 agents" and asked for
6 in flight per driver.
- **Spend at the stop:** B $0.095 and C $0.087, all spent before round 10, so the games are unusable.
- **The partial runs:** kept as `runs/partial_net20_*_1238`.

Iraj's questions: with more agents and rounds, do we ever get **gossip**, and is **winning possible**
when agents can only communicate along graph edges? Mechanics: CONTRACTS §9d.

## 0. Why N=40 × 30 rounds and not 40 rounds, and why D was dropped

The lead's rule: prefer N=40 if ≥ 6 worlds × 40 rounds of B, C and A fit in $7. If not, use N=40
with 30 rounds. If that does not fit either, fall back to N=20.

Measured at N=40 (§3):
- In A (complete graph), the prompt grows by about **+1,900 tokens per round**. It reaches the context
  plateau (about 16.5k gpt-oss tokens) by round 9, so almost every A call is a full-context call.
- In B (contacts), it grows by only about **+215-265 per round**, because agents see only their
  neighbours.

Projected cost at today's price:

| design | A | B | C | total |
|---|---|---|---|---|
| N=40 × 40 rounds × 6 worlds | $3.24 | $1.48 | $1.81 | **$6.53** |
| N=40 × 30 rounds × 6 worlds | $2.34 | $0.91 | $1.09 | **$4.34** (caps $5.79) |

- **40 rounds does not fit.** $6.53 central is over the $6.78 that was left once margins are added.
- **30 rounds fits with caps.** $5.79 of caps + $0.22 already spent = **$6.01 ≤ $7**.
- **D (BA hubs) is dropped.** It would cost about $1.2 more.

**One line for Iraj:** we went to N=40 at 30 rounds, not 40. At N=40 the complete-graph baseline
fills the whole context window from round 9, so each of its calls costs about 2× an N=20 call. 40
rounds would have cost $6.5 against the $7 cap.

Context settings are identical across A, B and C: the base `context.budget_tokens` of 14000
(Qwen-tokenizer count, about 16.5k gpt-oss tokens), the same as every earlier grid and sweep run.
It was not tightened, because N=40 fits without that.

## 1. Design

All three conditions share these settings:
- **Game:** N=40 agents, 30 rounds, simultaneous turns (reshuffled), `winner_policy: continue`.
  There are 5 keys and 3 needs per agent, and 2 copies of each of the 100 infos.
- **Worlds:** `run.seed 1` × game_idx 0-5. The deal, the needs and the names are identical across
  conditions (checked on the dry runs).
- **Graph:** it has its own seeded stream, so B and C play the **same ER graph** per world.
- **Branch:** one no-God branch per world (`runner.fork.only_branches: [nogod]`). The questions are
  about gossip and solvability, not about God.
- **Model:** openai/gpt-oss-120b with reasoning_effort low, `provider_sort: price`, agent
  max_tokens 1000 and `salvage_truncated` on. The provider is logged per call.

| cond | config | graph | mode | board | priority |
|---|---|---|---|---|---|
| A | `configs/net40_complete_sim.yaml` | complete | – | global | 3 (baseline) |
| B | `configs/net40_er3_contacts_sim.yaml` | Erdős–Rényi, mean degree 3 (connected). Realized: mean degree 2.9-3.65, max degree 7-9, average path 2.9-3.4, diameter 6-8, clustering 0.03-0.16 | contacts | neighbours | 1 |
| C | `configs/net40_er3_known_sim.yaml` | same ER graph as B | known_ids | neighbours | 2 |

**Why `board.scope: neighbors` in B and C.**
- **B:** a global board lets any agent broadcast to all 40 players and read everyone's posts. Only
  the trades would then be local. "Communicate only along edges" requires that the board be local too.
- **C:** a global board reveals every poster's name to everyone on the first round, so the names
  would not need to diffuse at all.
- **Cost:** with a neighbour-scoped board, the only way to reach a non-neighbour in B is a relay
  through intermediaries, and in C it is learning the name first.

## 2. Checks before launch ($0)

**FakeLLM dry runs** (`runs/fake_net40_*`): 6 worlds × 30 rounds × 40 agents per config. Every run
exited 0, all games ended `done`, and `swarm.analysis.invariants` reports **0 violations**.

**Invariant checker fix** (`swarm/analysis/invariants/prompts.py`):
- **The false positive:** at N=40 there are 100 infos with 4-digit key values, so values repeat
  across infos. For example, in world 0 the value 4608 is the key of both info 54 and info 68. The
  "system line shows a key it never held" check matched on the value alone, so it fired 204 false
  positives.
- **The fix:** a value the agent itself held under another info no longer counts as a leak. The
  game is unaffected, because keys are (info, key) pairs. The invariant tests pass, and the N=20
  runs still show 0 violations.

**Global ledger cap:** raised from $8 to $20 (`swarm/config.py`, `configs/base.yaml`,
`configs/grid_oss120b_base.yaml`). The change is hash-neutral, because the cap is hashed as the fixed $2. The hash
tests pass, and so does the full suite (minus `tests/viz`).

## 3. Smokes (paid)

- **N=20:** 1 world, 5 rounds (`runs/smoke_net20_*`).
- **N=40:** 1 world, 4 rounds (`runs/smoke_net40_*`; 12 in flight during this smoke).

| | N=20 A | N=20 B | N=40 A | N=40 B |
|---|---|---|---|---|
| calls / cost | 104 / $0.0075 | 102 / $0.0045 | 176 / $0.0192 | 164 / $0.0077 |
| prompt mean r1 → last | 733 → 4609 | 739 → 1790 | 822 → 6431 | 738 → 1377 |
| growth per round | ≈ +970 | ≈ +265 | ≈ +1,870 | ≈ +215 |
| cost per call, last round | $0.000112 | $0.000056 | $0.000168 | $0.000059 |
| errors / parse failures / length | 0 / 1 / 4 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| provider (fallback) | PI 104 | PI 101, Near AI 1 | PI 168, Near AI 8 (4.5%) | PI 152, Near AI 12 (7.3%) |

PI = PrimeIntellect.

**Cost model:** cost per call ≈ prompt × $0.021/M + completion × $0.077/M. Those are
PrimeIntellect's current list prices, and the model matches the smoke within 5%.

**Plateau:** prompts flatten at about 16.2k (mean) to 17.4k (max) gpt-oss tokens, from
`sweep_n20` r16-20.

## 4. Provider prompt caching (Iraj's "can we not do more compaction?")

**OpenRouter pricing** (`/api/v1/models/openai/gpt-oss-120b/endpoints`, 12:30 EST):
- PrimeIntellect (fp4) supports implicit caching: prompt $0.021/M, **cache read $0.019/M (−10%)**,
  completion $0.077/M.
- Near AI caches at $0.015/M, half its $0.03/M prompt price, but its completions cost $0.15/M.
- Caching does not lower the cost on any provider below PrimeIntellect's.

**Probe** (`probe_cache_net20`, $0.0002): the same late-round B prompt (2,822 tokens) was sent
3× to PrimeIntellect only.
- **Cache hit:** `prompt_tokens_details.cached_tokens` = 2,816 on all three calls. The first call
  hit too, because the game had just sent that exact prompt.
- **Billed:** prompt cost $5.363e-5 = 2,816 × $0.019/M + 6 × $0.021/M.
- **So caching already applies.**

**Cost with and without caching:**
- Today our layout keeps only the system prompt (≈ 650 tokens) as a stable prefix. The user
  message opens with "You are X. Round r of R.", which breaks the prefix every round.
- A template that moved the volatile header last could cache most of the growing history. At
  PrimeIntellect's −10% cache price, that saves at most **≈ 7% per call** (input is about 75% of
  the cost). At the plateau that means about $0.00038 → about $0.00035 per call, and about $0.3
  on this whole experiment.
- History truncation at the context cap also moves the prefix on every round at the plateau, so
  the realistic saving is smaller still.

**Decision: no template change.** It would change the rendered prompts for an at most 7% saving,
and the per-call logs do not record `cached_tokens`. The measured per-round cost, with
caching as it already happens, is in §3. The "without caching" price is at most 10% higher on the
input part.

## 5. Projection and caps (N=40, 30 rounds, 6 worlds)

| cond | assumed prompt growth | central per branch | central (6 worlds) | hard cap (`llm.budget_usd`) |
|---|---|---|---|---|
| A | +1,900 tok/round, plateau 16.2k from r9 | $0.39 | $2.34 | $2.97 |
| B | +265 (smoke: +215) | $0.151 | $0.91 | $1.30 |
| C | +350 (guess: DMs from learned names) | $0.18 | $1.09 | $1.52 |
| **total** | | | **$4.34** | **$5.79** |

- **Caps:** 1.2-1.25 × the central projection + $0.16. The $0.16 covers RunBudget's pre-call
  reservation: 240 pending calls × about $0.00066 (SWEEP_PLAN incident 1).
- **Already spent by this task:** $0.221. That is the smokes ($0.039), the probe, and the stopped
  N=20 B and C ($0.182).
- **Task worst case:** $0.22 + $5.79 = **$6.01 ≤ $7.00**.
- **Ledger:** $7.913 at launch, so its worst case is **$13.70**, below $14.80. The drivers stop at
  **$14.69** ($7.692 + $7.00).

## 6b. Final launch (13:23:05 EST): 4 worlds, A at 20 rounds, 16 in flight

**Projection with the fallback price mix:**
- Near AI and Venice cost $0.03 / $0.15 per M, against PrimeIntellect's $0.021 / $0.077. That is
  about 1.45× per call at the plateau.
- At 12 in flight we saw 38% fallback. The projection assumes **40% fallback, ×1.2 on cost**.

| cond | central (PrimeIntellect only) | × fallback mix | cap |
|---|---|---|---|
| A, 20 rounds, 4 worlds | $0.96 | $1.15 | $1.61 |
| B, 30 rounds, 4 worlds | $0.60 | $0.73, less the cached prefix | $1.06 |
| C, 30 rounds, 4 worlds | $0.72 | $0.87 | $1.24 |
| **total** | $2.28 | **$2.75** | **$3.91** |

- **Caps:** 1.3 × the mix projection + $0.11. The $0.11 covers RunBudget's reservation for 160
  pending calls.
- **Task spend before this launch:** **$0.676**. That is the smokes, the probe, the stopped N=20
  runs ($0.182), the stopped 12-in-flight start ($0.019), the 30-round A ($0.309) and B's worlds
  4-5 plus its 30-round part.
- **Task worst case:** $0.676 + $3.91 = **$4.59 ≤ $7.00**.
- **Ledger:** $8.368 at launch, so its worst case is **$12.28**, below $14.80. The drivers stop at
  $14.69.

**Abort rules:**
- the grid rules, which already cover errors and 429s above 5%;
- the new `--max-fallback 0.5`: abort when more than 50% of fresh (non-cached) responses come
  from a provider other than PrimeIntellect, after 200 fresh responses.

On a fallback abort, the cells restart at 12 in flight, replaying from the cache.

**ETA:**
- A: 3,200 calls at 6 in flight, about 10 s each, so ≈ 1.5 h.
- B: 4,800 calls minus about 1,700 cached, at 5 in flight, so ≈ 1 h.
- C: 4,800 calls at 5 in flight, about 6 s each, so ≈ 1.6 h.
- **Done ≈ 15:00 EST.**

## 6c. Side run: high reasoning (Iraj, 13:35: "run with high reasoning and see if it changes things")

**What it is:** `configs/net40_er3_contacts_high_sim.yaml` is B with exactly two changes:
- `llm.openrouter.reasoning_effort: high`, where B uses low;
- agent `max_tokens: 8000`, where B uses 1000, because reasoning tokens count toward it.

**How it runs:**
- Worlds 0-1 only, at 4 in flight, so 20 are in flight in total with A, B and C.
- `max_rounds` stays 30 so the prompt is word-for-word B's. A watcher
  (`scratchpad/stop_r10.sh`) stops the run once both worlds finish round 10.
- It is compared with B's worlds 0-1 at rounds ≤ 10.
- Hard cap $0.60. Driver log: `runs/network40_driver4_Bhigh.log`.

**Round 1, which doubles as the smoke:**
- 94 calls cost $0.0113, or $0.00012 per call.
- Output: 1,565 tokens per call on average, of which 1,389 are reasoning; the max is 3,843. Truncation 0/94.
- Fallback 7%.
- A round takes about 7 minutes.

**Projection:** $0.16 for 10 rounds. ETA ≈ 14:45.

## 6. Launch (12:45:17 at 6 + 6 in flight; relaunched 12:49:07 at 4 + 4; superseded at 13:22)

**The 12-in-flight attempt was stopped under the fallback rule:**
- It was supposed to be the same setting for every condition, at 6 per driver.
- Earlier tonight, 12 in flight sent only about 4% of calls to the fallback provider.
- **This time it sent 38%.** Round-1 calls went 287 to PrimeIntellect, 155 to Near AI and 24 to
  Venice. Near AI costs about 1.6× per call.

**It was stopped at 12:48 (rule: fallback > 15%) and relaunched at 4 per driver.**
- The relaunch replays the 480 completed calls from the cache. The 12-in-flight partial dirs are
  `runs/partial_net40_*_1248`, and their $0.019 is sunk.
- **Fresh calls at 8 in flight** (first 4 min): A has 244 PrimeIntellect / 15 Near AI (6%); B has 322
  PrimeIntellect / 27 Near AI / 8 Venice (10%).
- **The final setting is 4 in flight for every condition** (`max_concurrency: 4` in the configs).
- **Driver A:** `net40_complete_sim`, the slowest cell (full-context prompts).
- **Driver BC:** B, then C.

Wall-time estimate at 4 in flight: 7,200 calls per cell.
- A takes about 4-5 h (full-context prompts are slower).
- B and C take about 1.5-2 h each.
- **ETA ≈ 17:00-18:00 EST.**

```bash
cd ~/projects/swarm_hackathon
OPENROUTER_API_KEY="$(cat "/home/iraj/projects/swarm_data?/.planAdemoenv")" PYTHONNOUSERSITE=1 \
  setsid nohup conda run -n swarm --no-capture-output python infra/grid_driver.py \
  --cell net40_complete_sim:2.97:1:n=40,g=1900,pcap=16500 --seeds 6 --rounds 30 \
  --set llm.openrouter.max_concurrency=4 --cap-override --ledger-stop 14.69 \
  --log runs/network40_driver_A.log > runs/network40_driver_A.out 2>&1 < /dev/null &
# driver BC: --cell net40_er3_contacts_sim:1.30:1:n=40,g=265,pcap=16500 \
#            --cell net40_er3_known_sim:1.52:1:n=40,g=350,pcap=16500   (same flags, log _BC)
```

**Abort conditions** (grid rules; checked every 10 s; on abort the cell's process group is
killed and no further cell starts):
- MemAvailable < 15 GB;
- more than 20 rg processes;
- ledger ≥ $14.69;
- live projection > the cell cap (after 150 paid calls);
- LLM errors > 5%, or any HTTP 400;
- parse failures > 10%;
- finish=length > 5%;
- per branch: > 10% of calls errored or > 30% of turns noop because of errors.

`llm.budget_usd` also ends games `budget_exceeded`.

## 7. First design (N=20 × 40 rounds × 8 worlds; stopped at 12:38, kept for reference)

The configs are `configs/net20_{complete,er3_contacts,er3_known,ba_known}_sim.yaml`. Each driver
ran at 4 in flight: driver 1 ran B then A, driver 2 ran C then D.

| cond | projection (8 worlds) | cap |
|---|---|---|
| B | $0.84 | $1.21 |
| C | $1.04 | $1.47 |
| A | $1.57 | $2.16 |
| D | $1.15 | $1.62 |

The total was $4.60, with caps of $6.46. The projection used sweep_n20's realized price, which was
about 25% below today's.

**At the stop:**
- B: 1,513 calls, live projection $0.95.
- C: 1,448 calls, projection $1.04.
- Errors: 0. Parse failures: 0.

## 8. Analysis

```bash
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.invariants runs/net40_<cond>
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.network_compare runs/net40_complete_sim \
    runs/net40_er3_contacts_sim runs/net40_er3_known_sim --ref-graph runs/net40_er3_contacts_sim \
    --json plan/figs/network_n40.json --figs plan/figs
```

What each question looks at:
- **Solvability:** win rate, welfare and needs filled (paired by world, t95 CI, sign test).
- **Key relays:** an agent receives a key it does not need and passes on the same copy. Relay
  chains are deliveries with ≥ 2 hops.
- **Fill rate by graph distance** to the nearest holder. For A this is a placebo computed on the
  same ER graph.
- **Gossip:** social.py claims, introductions, forwarding requests and rumour chains.
- **Name diffusion in C:** the S-curve, channels, who introduces whom, and introducer betweenness.
