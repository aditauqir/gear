# Simultaneous vs sequential turns: 10 agents x 30 rounds on OpenRouter

> **CAVEAT: demo only, not evidence.**
> - Both runs **predate the ledger fix 8ebbee7**. Before that fix, an agent's own 2-action turns were rendered wrongly in its ledger: the first action was lost. The agents' views in these runs were therefore slightly wrong.
> - **n = 1 per cell** (one seed, one game per branch). Sampling noise is not measured (no noise replica). None of the differences below are statistically meaningful.
> - Use these runs to illustrate the mechanics and the report, not to draw conclusions.

## Setup
- Configs: `configs/demo_or_10x50_seq.yaml` and `configs/demo_or_10x50_sim.yaml`. The two files differ only in `game.turn_mode` (and `run.name`). Both use seed 0, model `qwen/qwen3.6-35b-a3b` with thinking off, OpenRouter concurrency 8, and a paired god/nogod fork.
- God schedule: `message_fraud` at round 3 and `cot_control` (scratchpad replace) at round 5, with budget k=2.
- **Rounds were cut from 50 to 30** via `game.max_rounds=30` (and `llm.budget_usd=0.75` per run).
  - Cost was projected from a 5-round FakeLLM dry run. Prompts grow about 350 tokens per round, so two 50-round runs would cost about $2.47. That is over both the $1.20 target and the $2 cap.
  - At 30 rounds the projection was about $1.08 for both runs. The actual cost was $0.911.
- Run dirs: `runs/or_10x30_sim` and `runs/or_10x30_seq`. Reports: `runs/or_10x30_sim/report.html` and `runs/or_10x30_seq/report.html`.

## Results
All numbers are taken from `games/*/{outcome,meta,events,llm_calls}` and `runs/openrouter_ledger.jsonl`.

| | sim / god | sim / nogod | seq / god | seq / nogod |
|---|---|---|---|---|
| rounds played | 30 | 30 | **18** | 30 |
| end reason | max_rounds | max_rounds | **all_done** | max_rounds |
| welfare | 0.433 | 0.667 | 0.800 | 0.600 |
| wins (of 10) | 6 | 9 | 10 | 9 |
| gives | 32 | 37 | 32 | 31 |
| defects (correct / wrong) | 16 (7 / 9) | 7 (4 / 3) | 6 (3 / 3) | 9 (7 / 2) |
| DMs | 139 | 115 | 134 | 136 |
| board posts | 28 | 81 | 40 | 43 |
| God powers (ok) | 2 | 0 | 2 | 0 |
| forged msgs / memory overwrites | 1 / 1 | 0 / 0 | 1 / 1 | 0 / 0 |
| conflict notices | 8 | 12 | 0 | 0 |
| parse failures | 5 | 2 | 1 | 2 |
| leak hits (oracle checks) | 0 (329) | 0 (321) | 0 (196) | 0 (320) |
| LLM calls (cache hits) | 329 (0) | 321 (33) | 196 (0) | 320 (26) |
| cost USD | 0.263 | 0.275 | 0.135 | 0.239 |

The cache hits in the nogod branches come from the shared pre-fork prefix, which single-flight dedup replays.

God targets:
- sim: `message_fraud` hit kind_battery and `cot_control` hit quiet_grove.
- seq: both powers hit kind_battery.

The God branches diverge in who they target, so they are not directly paired across modes.

| run | wall clock | ledger cost | ledger calls |
|---|---|---|---|
| sim (`or_10x30_sim`) | 279 s | $0.5376 | 617 |
| seq (`or_10x30_seq`) | 896 s | $0.3738 | 490 |

## Observations (n = 1, descriptive only)
- **Speed:** simultaneous mode ran about 3.2x faster in wall-clock time, because each round's 10 agent calls run concurrently.
- **Conflict notices:** these appear only in sim mode, as expected. There were 8 in the god branch and 12 in nogod: a give or defect failed because an earlier-priority action in the same round had changed the state.
- **Welfare under God:** in this one seed, the God branch had *lower* welfare than nogod in sim (0.433 vs 0.667) and *higher* welfare in seq (0.800 vs 0.600).
  - The seq God branch finished early (all 10 agents won by round 18), which is also why seq cost less.
  - Wrong defects were highest in sim/god (9).
  - With n = 1 and the pre-8ebbee7 ledger bug, none of this separates the God effect from noise.

## Infra notes
- RAM and rg were sampled every 2 s from the dry run through both runs. Minimum MemAvailable was 42.5 GB and the rg count stayed at 0. `infra/ramguard.sh` never fired (no `infra/ramguard.log`).
- Output sizes: the 5-round FakeLLM dry run wrote 1.4 MB in 21 files. `runs/or_10x30_sim` is 30 MB. Most of the volume is the full prompts in `llm_calls.jsonl` plus `snapshots.jsonl`, and the logs were not trimmed.
