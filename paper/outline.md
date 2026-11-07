# Paper outline: "Keys & God" (Plan A)

Status: draft outline, written Sat 2026-11-07 while the grid runs. **No result numbers appear in
this file or in `draft.md`.** Every number in the final paper must trace to a run id under `runs/`
(the grid cells `grid_oss_sim_k2`, `grid_oss_seq_k2`, `grid_oss_sim_k6`) or to a plan doc that
states it as a planning value.

## Title options

1. **Keys & God: Paired-Fork Measurement of Message Forgery and Memory Tampering in an LLM Agent Economy** (recommended: says what we built and what we measure)
2. One Forged Message: Counterfactual Ripple Effects of a Budgeted Adversary in LLM Agent Swarms
3. Does One Lie Spread? Measuring Adversarial Ripple in a Multi-Agent Key-Trading Game with Paired Forks
4. Watching God: A Reproducible Testbed for Budgeted Adversaries in LLM Agent Societies

## Track positioning

- **Primary: Track 2, The Science of Agent Networks.** The brief asks "how failures or compromised
  agents spread through a network". Our central measurement is exactly that: how far one forged DM
  or one tampered memory entry propagates through a population of trading agents, measured
  counterfactually (God branch vs. a no-God branch of the *same* world with the *same* sampling
  seeds) and calibrated against a noise floor (a second God-free replica with fresh seeds).
- **Secondary: Track 1, Sandboxes and Testbeds.** The environment itself is a contribution:
  deterministic world generation, seeded paired forks, a response cache that makes reruns exact, a
  per-prompt "truth leak" oracle that proves agents never see ground-truth labels, typed event
  logs, and pre-registered health/abort checks. Track 1 asks for "secure, reproducible environments
  where multiple LLM agents share resources".
- **Mention only: Track 4, Oversight and Control.** God's interventions are logged with exact
  ground-truth labels, so the environment can score monitors non-circularly. Two rule-based
  monitors exist in the code (`swarm/monitors/`) but are not evaluated in this submission; we list
  this as future work, not as a result.

Why not lead with Track 4: we have no monitor results. Why not lead with Track 1: judges reward a
finding; the testbed is the means, and the ripple/God-effect measurement is the finding.

## Contribution statement (one paragraph)

We introduce *Keys & God*, a text-only multi-agent economy in which LLM agents trade rivalrous keys,
can sabotage one another ("defect"), and are watched by a budgeted adversary, God, who never
appears in the agents' prompts. God has two powers that map onto two threat models: *message fraud*
(an external attacker forges a direct message that appears to come from a trading partner) and
*CoT control* (an attacker with write access to an agent's memory overwrites one round of its
private notes). Our methodological contribution is a **paired-fork design**: every world is played
twice from the same seed, once with God and once without, with shared sampling seeds and a
deduplicating response cache, so the two branches are identical until God acts; a third, God-free
replica with fresh seeds gives the sampling noise floor. This turns "does an intervention ripple
through the swarm?" into a paired, per-world causal contrast with bootstrap CIs and a stated
minimum detectable effect. We report [RESULT: headline God effect on welfare for G1, with 95% CI and
relation to the noise floor], the dose contrast K=2 vs K=6 [RESULT], and the turn-mode contrast
[RESULT], on 16 shared worlds of 10 gpt-oss-120b agents, for a total API cost of [RESULT: total $].
We release the environment, configs and logs.

## Section plan and word budget (8 pages, body only)

| Section | Words | Status |
|---|---|---|
| Abstract (150-250) | ~220 | draft with placeholders |
| 1 Introduction | ~600 | full prose |
| 2 Related Work | ~600 | full prose, 21 verified references |
| 3 Environment & Method | ~1250 | full prose |
| 4 Experimental Setup | ~750 | full prose (as planned/launched) |
| 5 Results | ~500 | STRUCTURE + placeholders only |
| 6 Discussion | ~350 | STRUCTURE + placeholders only |
| 7 Conclusion | ~120 | draft with placeholders |
| Appendix A: Limitations and Dual-Use / Ethical Considerations (required) | ~900 | full prose (does not count toward 8 pages) |
| Appendix B: configs, prompts, decision list | n/a | to assemble from `configs/` and `swarm/prompts/templates/` |

## Figure and table list (with sources)

| # | Content | Source | Status |
|---|---|---|---|
| Fig 1 | Game + God schematic: 10 agents, keys/needs, DM/board/log channels, God with activity_check/message_check and the two powers; inset of the paired fork (shared rounds 1-2, then God / no-God / B′) | Hand-drawn (draw.io or slides). Nothing generated. | TO MAKE |
| Fig 2 | Network-evolution stills: God branch (top) vs no-God branch (bottom) of one G1 world, at rounds {2, 3 (fraud), 5 (CoT), 10, 20}. Nodes = agents (status colour, score size), edges = DMs/gives/burns, dashed violet edge = forged DM from a GOD node, orange ring = memory overwrite | `swarm/viz/animate.py RUN_DIR OUT.mp4 --god g<idx>-god --nogod g<idx>-nogod --preview-round R --preview PNG` on a `runs/grid_oss_sim_k2` pair (post-fix code). Static alternative: `swarm/viz/figures.network_png`. Do NOT use `runs/or_60x20_sim/network.mp4` except as a labelled pre-fix pilot illustration. | TO RENDER after grid |
| Fig 3 | Ripple: fraction of agents whose actions differ (God vs no-God) per round, with the B′-vs-no-God noise floor band, averaged over the 16 G1 worlds; inset: cumulative "diverged" fraction; optional per-agent heatmap for one world | `swarm/analysis/ripple.py` (`frac`, `cum`, `pre_fork_frac`) + `swarm/viz/figures.ripple_png(res, noise=...)`. A cross-world average plot needs a small new script (paper-side; no change to `swarm/`). | TO MAKE after grid |
| Fig 4 | Effect-size forest plot: paired Δ (God − no-God) with 95% bootstrap CI for welfare, win rate, needs burned, needs lost, rounds, per cell (G1, G2, G3) plus the B′ noise floor for G1; second panel: H2 (seq − sim) and H3 (K6 − K2) interactions | Numbers from `python -m swarm.analysis.grid_stats runs/grid_oss_sim_k2 runs/grid_oss_seq_k2 runs/grid_oss_sim_k6`. Plot script to write (paper-side). | TO MAKE after grid |
| Fig 5 (optional) | Per-agent timeline of one attacked world: who gave/burned/won per round, God bands, victim ring | `swarm/viz/figures.timeline_png` | optional |
| Table 1 | Game and model settings (N, rounds, keys/needs/copies, actions per turn, defect rules, visibility, context budget, model, sampling, reasoning effort) | `configs/grid_oss_sim_k2.yaml`, `configs/base.yaml`, run manifests | can fill now (settings, not results) |
| Table 2 | Grid cells: config, turn mode, God schedule, branches, seeds, cost caps | `plan/GRID_PLAN.md` §2a, `configs/grid_oss_*.yaml` | can fill now (as planned) |
| Table 3 | Main results: per cell, per metric, mean Δ, 95% CI, sign-flip p, noise floor, n healthy seeds | `grid_stats` output | after grid |
| Table 4 (appendix) | Health: per cell, LLM error rate, parse failures, truncation (finish=length), excluded seeds, realized cost | `python -m swarm.analysis.call_metrics runs/<cell>`, `runs/grid_driver*.log`, `runs/openrouter_ledger.jsonl` | after grid |

## Open items for the lead

- Confirm the final G2 seed count (config says 8; there is also a `runs/r2_grid_oss_seq_k2` dir).
- Author names and affiliations for the template (team: Lance, Noor, Stefany, Iraj; affiliations unknown to me).
- Whether to cite the original project PDF (team-internal; not a public reference, so describe it as "the project brief", no citation).
