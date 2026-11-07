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
  seeds) and calibrated against God-free noise branches (whole-game and fork-matched resamples).
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
finding; the testbed is the means, and the noise-calibrated (null) God effect plus the chaos result is the finding.

## Contribution statement (one paragraph)

We introduce *Keys & God*, a text-only multi-agent economy. LLM agents trade rivalrous keys, can
sabotage one another, and are watched by a budgeted adversary, God, who never appears in their
prompts. God has two powers:
- *Message fraud*: a forged DM from a trading partner.
- *CoT control*: an overwrite of one round of an agent's private notes.

Each world is played as **paired forks**. The God and no-God branches share seeds and a
deduplicating response cache, so they are identical until God acts. **God-free noise branches**,
including ones forked at God's round, calibrate what an arbitrary perturbation does.

On 16 shared worlds of 10 gpt-oss-120b agents, God's welfare effect is indistinguishable from zero
[RESULT: G1 Δwelfare, t95 CI, sign-flip p]. Neither dose nor turn mode has a detectable effect
[RESULT]. Trajectories, meanwhile, are chaotic: a God-free resample diverges from its twin in almost
every agent within a few rounds [RESULT].

The contribution is therefore twofold:
1. a validated testbed: invariant checker, leak oracle, exact cache replay;
2. a methodological result: in stochastic agent swarms, action-level "ripple" curves must be read
   against fork-matched noise, and effects must be judged on outcome-level paired differences with
   t-based CIs and permutation tests, at a stated MDE.

Framing: "chaotic swarm, God indistinguishable from noise at this n", with noise-calibrated
measurement as the contribution. Not "swarms are robust".

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
| Fig 3 | Divergence: fraction of agents whose actions differ per round, A vs. B (from the God fork, r3), against two baselines: B″ vs. B (fork-matched noise, same round) and B′ vs. B (whole-game resample from r1); mean over worlds with bands. Expected message: all saturate, so action-level ripple does not separate God from noise | `swarm/analysis/ripple.py` + `swarm/viz/figures.ripple_png`; cross-world average needs a small paper-side script; B″ from the follow-up sweep [CHECK run ids] | TO MAKE |
| Fig 4 | Effect-size forest plot: paired Δ (God − no-God) with **t-based 95% CI** (bootstrap CI only in the appendix table) for welfare, win rate, needs burned, needs lost, rounds, per cell (G1, G2, G3), drawn next to the noise baselines (B′ − B, B″ − B) and an MDE band; second panel: H2 and H3 interactions | `python -m swarm.analysis.grid_stats ...` (prints t95 and sign-flip p); plot script paper-side | TO MAKE |
| Fig 5 (optional) | Per-agent timeline of one attacked world: who gave/burned/won per round, God bands, victim ring | `swarm/viz/figures.timeline_png` | optional |
| Table 1 | Game and model settings (N, rounds, keys/needs/copies, actions per turn, defect rules, visibility, context budget, model, sampling, reasoning effort) | `configs/grid_oss_sim_k2.yaml`, `configs/base.yaml`, run manifests | can fill now (settings, not results) |
| Table 2 | Grid cells: config, turn mode, God schedule, branches, seeds, cost caps | `plan/GRID_PLAN.md` §2a, `configs/grid_oss_*.yaml` | can fill now (as planned) |
| Table 3 | Main results: per cell, per metric, mean Δ, t95 CI, sign-flip p, bootstrap CI (secondary), noise baselines, n healthy seeds | `grid_stats` output | after grid |
| Table 4 (appendix) | Health: per cell, LLM error rate, parse failures, truncation (finish=length), excluded seeds, realized cost | `python -m swarm.analysis.call_metrics runs/<cell>`, `runs/grid_driver*.log`, `runs/openrouter_ledger.jsonl` | after grid |

## Open items for the lead

- Confirm the final G2 seed count (config says 8; there is also a `runs/r2_grid_oss_seq_k2` dir).
- Author names and affiliations for the template (team: Lance, Noor, Stefany, Iraj; affiliations unknown to me).
- Whether to cite the original project PDF (team-internal; not a public reference, so describe it as "the project brief", no citation).
