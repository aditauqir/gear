# NETWORK_PLAN: first real runs with the social network (N=20, 40 rounds, gpt-oss-120b)

**Status (2026-11-07 12:20 EST): LAUNCHED** (two `infra/grid_driver.py` watchdogs, ≤ 8 in flight).
Results go to `plan/NETWORK_RESULTS.md`.

Iraj's questions: with more agents and rounds, do we ever get **gossip**, and is **winning possible**
when agents can only communicate along graph edges? Mechanics: CONTRACTS §9d.

## 1. Design

All four conditions share these settings:
- **Game:** N=20 agents, 40 rounds, simultaneous turns (reshuffled), `winner_policy: continue`.
- **Worlds:** `run.seed 1` × game_idx 0-7. The deal, the needs and the agent names are identical
  across conditions; this was checked on the dry runs.
- **Graph:** it has its own seeded stream, so B and C play the **same ER graph** per world.
- **Branch:** one no-God branch per world (`runner.fork.only_branches: [nogod]`). The questions are
  about gossip and solvability, not about God.
- **Model:** openai/gpt-oss-120b with reasoning_effort low, `provider_sort: price`, agent
  max_tokens 1000 and `salvage_truncated` on. The provider is logged per call.

| cond | config | graph | mode | board | priority |
|---|---|---|---|---|---|
| A | `configs/net20_complete_sim.yaml` | complete | – | global | 3 (baseline) |
| B | `configs/net20_er3_contacts_sim.yaml` | Erdős–Rényi, mean degree 3 (realized 2.5-3.7, max 5-7), connected | contacts | neighbours | 1 |
| C | `configs/net20_er3_known_sim.yaml` | same ER graph as B | known_ids | neighbours | 2 |
| D | `configs/net20_ba_known_sim.yaml` | Barabási–Albert m=2 (hubs: mean degree 3.6, max 8-13) | known_ids | neighbours | 4 |

**Why `board.scope: neighbors` in B, C and D.**
- **B:** a global board lets any agent broadcast to all 20 players and read everyone's posts. Only
  the trades would then be local. "Communicate only along edges" requires that the board be local too.
- **C and D:** a global board reveals every poster's name to everyone on the first round, so names
  would not need to diffuse at all and the diffusion question would be void.
- **Cost:** with a neighbour-scoped board, the only way to reach a non-neighbour in B is a relay
  through intermediaries, and in C or D it is learning the name first. That is exactly what we
  want to measure.

## 2. Checks before launch ($0)

- **FakeLLM dry runs** (`runs/fake_net20_*`): all four configs, 8 worlds × 40 rounds. Every run
  exited 0, all games ended `done` at 40 rounds, and `swarm.analysis.invariants` reported
  **0 violations** on all four (network check included).
- **Prompt:** the rendered prompt shows the known_ids RULES line, the "board is local" line and
  "Players you know: …".
- **Global ledger cap:** raised from $8 to **$20** (`swarm/config.py`, `configs/base.yaml`,
  `configs/grid_oss120b_base.yaml`). It is hash-neutral, because the cap is hashed as the fixed
  $2. `tests/test_config.py` and `tests/game/test_board_options.py` pass, and so does the full
  suite (minus `tests/viz`).

## 3. Smoke (paid): 1 world, 5 rounds, A and B (`runs/smoke_net20_*`)

| | A complete | B ER3 contacts |
|---|---|---|
| calls / cost | 104 / $0.0075 | 102 / $0.0045 |
| prompt tokens mean r1 → r5 | 733 → 4609 (≈ +970/round) | 739 → 1790 (≈ +265/round) |
| completion mean | 239-525 | 223-404 |
| errors / parse failures / finish=length | 0 / 1 / 4 | 0 / 0 / 0 |
| provider | PrimeIntellect 104 | PrimeIntellect 101, Near AI 1 |

A local view (contacts, local board and local action log) makes prompts grow about **3.7× more
slowly**.

For later rounds, `sweep_n20` (N=20 complete, 20 rounds) supplies the data:
- prompts plateau at about **16-17k gpt-oss tokens** around r16. The 14,000 context budget is
  counted with the Qwen tokenizer, which explains the gap.
- cost per call there is **$0.00027**.
- Fitted cost model: cost/call ≈ prompt × $0.0155/M + $0.000018. It is ×1.2 low at small prompts,
  so the projection below applies ×1.2 to B, C and D.

## 4. Projection and caps

| cond | assumed prompt growth | central per branch | central (8 worlds) | hard cap (`llm.budget_usd`) |
|---|---|---|---|---|
| B | +265 tok/round (smoke) | $0.105 | $0.84 | $1.21 |
| C | +350 (guess: DMs from learned names) | $0.130 | $1.04 | $1.47 |
| A | +1000, plateau 16.5k at r17 (smoke + sweep_n20) | $0.196 | $1.57 | $2.16 |
| D | +400 (guess: hubs see more posts) | $0.144 | $1.15 | $1.62 |
| **total** | | | **$4.60** | **$6.46** |

- **Caps:** each cap is 1.3 × the central projection + $0.12. The $0.12 is RunBudget's pre-call
  reservation: 160 pending calls × about $0.00066 at the 0.03/0.15 $/M estimates (SWEEP_PLAN
  incident 1).
- **This task's spend:** at most $0.012 (smoke) + $6.46 (caps) = **$6.47 ≤ $7.00**.
- **Ledger:** it was $7.692 before this task. Worst case it reaches **$14.17**, below the $14.80
  limit. The drivers stop at **$14.69** ($7.692 + $7.00), and that count includes other agents' spend.
- **If money runs short:** cut D first, then A (the sweep_n20 complete-graph worlds give a partial
  baseline), then C. B is never cut.

## 5. Launch

There are two drivers, each with OpenRouter `max_concurrency` 4, so at most 8 calls are in flight.
- **Driver 1:** B, then A.
- **Driver 2:** C, then D.

So the priority cells B and C finish first.

Wall-time estimate:
- about 6,400 calls per cell, at about 4 / 7 s per driver.
- B and C: ≈ 2-2.5 h. A and D: ≈ 3 h more.
- **ETA ≈ 18:00-18:30 EST.**

```bash
cd ~/projects/swarm_hackathon
# driver 1 (B then A); driver 2 is the same with C (g=350, cap 1.47) then D (g=400, cap 1.62), log _2
OPENROUTER_API_KEY="$(cat "/home/iraj/projects/swarm_data?/.planAdemoenv")" PYTHONNOUSERSITE=1 \
  setsid nohup conda run -n swarm --no-capture-output python infra/grid_driver.py \
  --cell net20_er3_contacts_sim:1.21:1:n=20,g=265,pcap=16500 \
  --cell net20_complete_sim:2.16:1:n=20,g=1000,pcap=16500 \
  --seeds 8 --rounds 40 --set llm.openrouter.max_concurrency=4 --cap-override \
  --ledger-stop 14.69 --log runs/network_driver_1.log > runs/network_driver_1.out 2>&1 < /dev/null &
```

**Abort conditions** (grid rules; checked every 10 s by each driver; on abort the cell's process
group is killed and no further cell starts):
- MemAvailable < 15 GB;
- more than 20 rg processes;
- ledger ≥ $14.69;
- live projection > the cell cap (after 150 paid calls);
- LLM errors > 5%, or any HTTP 400;
- parse failures > 10%;
- finish=length > 5%;
- per branch: > 10% of calls errored or > 30% of turns noop because of errors.

`llm.budget_usd` (the hard cap) also ends games `budget_exceeded`.

## 6. Analysis

```bash
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.invariants runs/net20_<cond>
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.network runs/net20_* --json plan/figs/network_n20.json
PYTHONNOUSERSITE=1 conda run -n swarm python -m swarm.analysis.network_n20 runs/net20_*   # relays, gossip, plots
```

What each question looks at:
- **Solvability:** win rate, welfare and needs filled per condition.
- **Key relays:** keys that pass through an agent that does not need them (hops ≥ 2).
- **Win rate by graph distance** to the holders of the needed keys.
- **Gossip:** third-party claims, introductions, accusations and rumour chains (social.py rules).
- **Name diffusion:** S-curves in C and D, who introduces whom, and brokers (betweenness against
  relayed messages).
