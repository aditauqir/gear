# Paper outline: "Keys & God" (Plan A)

Status: updated after the grid, the sweep and the board follow-ups. Every number must trace to
`plan/GRID_RESULTS.md`, `plan/SWEEP_RESULTS.md`, `plan/CODE_REVIEW.md` or `plan/figs/board_effect.txt`.
All numbers, including the board follow-ups, are verified by planA-review (`plan/CODE_REVIEW.md`, bc5839c).

## Title options

1. **Channels, Not Liars: A Hidden Forger Is Lost in Sampling Noise, but Removing the Public Board Breaks an LLM Agent Economy** (recommended; it is the current draft title)
2. Keys & God: Message Forgery Vanishes in the Noise, While the Public Channel Carries the Swarm
3. The Channel Matters More Than the Liar: Noise-Calibrated Paired Forks in an LLM Agent Economy
4. Who Breaks the Swarm? A Null Adversary and a Load-Bearing Board in Multi-Agent LLM Trading

## Track positioning

- **Primary: Track 2, The Science of Agent Networks.** The brief asks "how failures or compromised
  agents spread through a network". We answer it with two results. A compromised input (a forged
  DM or a tampered memory) does not spread into outcomes beyond sampling noise. The network's
  *channel structure* does matter: removing the broadcast channel harms the swarm robustly.
  Both are measured with noise-calibrated paired forks.
- **Secondary: Track 1, Sandboxes and Testbeds.** The environment itself is a contribution:
  deterministic world generation, seeded paired forks, a response cache that makes reruns exact, a
  per-prompt "truth leak" oracle that proves agents never see ground-truth labels, typed event
  logs, and pre-registered health/abort checks. Track 1 asks for "secure, reproducible environments
  where multiple LLM agents share resources".
- **Mention: Track 4, Oversight and Control.** There are two implications.
  - Oversight should protect shared coordination channels (their availability and integrity), not only individual agents.
  - God's exact ground-truth labels can score monitors non-circularly. The monitors are not evaluated here; that is future work.

Why not lead with Track 4: we have no monitor results. Why not lead with Track 1: judges reward a
finding; the testbed is the means, and the noise-calibrated (null) God effect plus the chaos result is the finding.

## Contribution statement

*Keys & God* is a text-only LLM economy: agents trade rivalrous keys over private DMs and a public
board, and can sabotage each other. An unseen, budgeted God forges messages and overwrites notes.
We contribute:
1. the environment, with an invariant checker, a leak oracle and exact cache replay;
2. **noise-calibrated paired forks**: shared seeds and cache until the intervention, plus God-free
   branches resampled at the same fork round;
3. a **bounded null** for the adversary. God's welfare effect is +0.013 [−0.048, +0.073] (n=16),
   with no effect beyond noise across timing, budget and swarm size. God's divergence is *below*
   fork-matched noise, so divergence curves measure chaos, not attack spread;
4. a **robust infrastructure effect** (verified). Removing the public board cuts welfare by 0.173
   [0.089, 0.257] (p=0.0003, n=16; it replicates on 10 new worlds). Agents send 1.8× the DMs, give
   26% fewer keys, and make 3× the wrong defects.

Framing: "the channel matters more than the liar". The delayed-board God result (+0.122, t95
includes 0, n=6) is suggestive only, a lead to replicate.

## Section plan and word budget (8 pages, body only)

| Section | Words | Status |
|---|---|---|
| Abstract (150-250) | 224 | final framing |
| 1 Introduction | 341 | done |
| 2 Related Work | 410 | done, 21 verified references |
| 3 Environment & Method | 1201 | done |
| 4 Experimental Setup | 606 | done |
| 5 Results | ~990 | done, all numbers verified |
| 6 Discussion | 264 | done |
| 7 Conclusion | 98 | done |
| Appendix A: Limitations and Dual-Use / Ethical Considerations (required) | ~900 | full prose (does not count toward 8 pages) |
| Appendix B: configs, prompts, decision list | n/a | to assemble from `configs/` and `swarm/prompts/templates/` |

## Figure and table list (with sources)

| # | Content | Source | Status |
|---|---|---|---|
| Fig 1 | Game + God schematic: 10 agents, keys/needs, DM/board/log channels, God with activity_check/message_check and the two powers; inset of the paired fork (shared rounds 1-2, then God / no-God / B′) | Hand-drawn (draw.io or slides). Nothing generated. | TO MAKE |
| Fig 2 | Network stills of world g02 (median-|Δwelfare| world of G1, |Δ| 0.067, rule-picked): God branch (A) vs no-God branch (B) at God's first move and at round 20 | `plan/figs/fig2_network.{pdf,png}` (planA-viz, `swarm.viz.paper_figs`) | EXISTS |
| Fig 3 | Divergence: post-fork share of agents acting differently from no-God, God (filled) vs fork-matched noise B″ (hollow), per sweep factor; shows God below noise | `plan/figs/sweep_{start,k,board,n}_divergence.png` (from `infra/sweep/plot.py`); per-round curves optional via `swarm/viz/figures.ripple_png` | EXISTS (sweep) |
| Fig 4 | Effect sizes: (a) grid paired Δ with t95 for G1/G2/G3 + B′ and H2/H3 (from `plan/GRID_RESULTS.md`; plot script paper-side, TO MAKE); (b) sweep A−N (filled) and A−B (hollow) welfare with t95 per factor | (b) `plan/figs/sweep_{start,k,board,n}_welfare.png` | (a) TO MAKE, (b) EXISTS |
| Fig 5 | Board-off mechanism: board on vs. off (no God, 16 worlds), paired per-world differences with t95 for welfare, win rate, DMs, gives, wrong and correct defects | numbers in `plan/figs/board_effect.txt`; plot script paper-side (TO MAKE) |
| Fig 6 (optional) | Per-agent timeline of one attacked world: who gave/burned/won per round, God bands, victim ring | `swarm/viz/figures.timeline_png` | optional |
| Table 1 | Game and model settings (N, rounds, keys/needs/copies, actions per turn, defect rules, visibility, context budget, model, sampling, reasoning effort) | `configs/grid_oss_sim_k2.yaml`, `configs/base.yaml`, run manifests | can fill now (settings, not results) |
| Table 2 | Grid cells: config, turn mode, God schedule, branches, seeds, cost caps | `plan/GRID_PLAN.md` §2a, `configs/grid_oss_*.yaml` | can fill now (as planned) |
| Table 3 | Main results: per cell, per metric, mean Δ, t95 CI, sign-flip p, bootstrap CI (secondary), noise baselines, n healthy seeds | `grid_stats` output | after grid |
| Table 4 (appendix) | Health: per cell, LLM error rate, parse failures, truncation (finish=length), excluded seeds, realized cost | `python -m swarm.analysis.call_metrics runs/<cell>`, `runs/grid_driver*.log`, `runs/openrouter_ledger.jsonl` | after grid |

## Open items for the lead

- Confirm the final G2 seed count (config says 8; there is also a `runs/r2_grid_oss_seq_k2` dir).
- Author names and affiliations for the template (team: Lance, Noor, Stefany, Iraj; affiliations unknown to me).
- Whether to cite the original project PDF (team-internal; not a public reference, so describe it as "the project brief", no citation).
