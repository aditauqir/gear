# Keys & God: Paired-Fork Measurement of Message Forgery and Memory Tampering in an LLM Agent Economy

*[AUTHORS AND AFFILIATIONS: Lance, Noor, Stefany, Iraj; affiliations to fill]*

> Drafting rules for this file:
> - `[RESULT: ...]` marks a number that must come from a grid run (`runs/grid_oss_*`) via
>   `swarm.analysis.grid_stats` / `call_metrics`.
> - `[FIG n]` refers to `paper/outline.md`.
> - `[CHECK: ...]` marks a fact to confirm before submission.
> - Planning values (caps, projections, the planning SD) come from `plan/GRID_PLAN.md` and are labelled as planned.
> - No other numbers about outcomes appear in this file.

## Abstract (draft, 150-250 words; finalize after results)

Teams of LLM agents are being deployed in settings where they exchange messages and resources, so one
compromised channel or memory could affect many agents. We present *Keys & God*, a text-only economy
in which language-model agents trade rivalrous keys to satisfy private needs, can sabotage one another,
and are watched by a budgeted adversary ("God"). The agents are never told that God exists. God has
two powers. *Message fraud* forges a direct message from a trading partner. *CoT control* overwrites
one round of an agent's private notes. To measure how an intervention spreads, we use a paired-fork
design. Each world is played with and without God from identical seeds, through a deduplicating
response cache, so the two branches are identical until God first acts. A third God-free replica with
fresh seeds gives the noise floor from sampling alone. On 16 shared worlds of 10 gpt-oss-120b agents
over 20 rounds, a two-intervention God changes mean welfare by [RESULT: G1 Δwelfare, 95% CI], against
a noise floor of [RESULT: G1 B′ floor]. Tripling the budget gives [RESULT: H3 contrast, CI], and
sequential turns give [RESULT: H2 contrast, CI]. The divergence between branches [RESULT: one
qualitative sentence on ripple vs. noise floor]. The grid cost [RESULT: total $] in API calls. We
release the environment, configurations and logs. The environment also includes a leak oracle that
checks every prompt for ground-truth labels, and exact replay from the cache.

*(Current length: about 210 words with placeholders; recount after filling.)*

---

## 1 Introduction

Multi-agent deployments of language models are becoming common. Assistants negotiate with other assistants, pipelines pass work between specialised agents, and agents share memory stores and message buses. In these settings, the security question is not only whether a single model can be jailbroken. It is also what happens to the *rest* of the system when one message or one memory entry is corrupted. Hammond et al. [1] list network effects and multi-agent security among the risk factors that set multi-agent risks apart from single-agent ones. Recent work shows that injected content can spread from agent to agent [8, 9, 10]. These studies mostly measure *infection*: whether a malicious instruction is copied or executed downstream, in a cooperative task pipeline.

We study a different and, we argue, more realistic failure: **strategic ripple in a mixed-motive economy**. Here the adversary does not install a self-replicating instruction. It plants one plausible lie, and the swarm's own incentives carry the consequences forward. A forged "send me your key first" message can make an agent give away a key. The impersonated partner receives an unexpected gift, the victim's later offers change, and others see the changed actions in the public log. Whether such a perturbation dies out or compounds is a question about the swarm, not about any single model. It is also hard to measure. LLM agents are stochastic, so two runs of the same game diverge even without an adversary, and a naive with/without comparison across random worlds confounds the intervention with world and sampling variance.

We contribute:

1. **An environment, *Keys & God*** (Section 3). LLM agents hold rivalrous keys, need keys they do not hold, and can message, post publicly, give keys, search the action log, and *defect*: burn another agent's need at a risk to themselves. A budgeted adversary, God, observes everything. It can forge a direct message (DM) from a real partner (*message fraud*: an attacker on the channel) or overwrite one round of an agent's private notes (*CoT control*: an attacker with memory write access). Agents are never told God exists, and a leak oracle checks every prompt for ground-truth labels.
2. **A paired-fork measurement design** (Section 3.4). Each world is played in a God branch and a no-God branch. The two branches share sampling seeds and use a response cache that deduplicates identical requests, so they are identical by construction until God first acts. A third God-free replica with fresh seeds measures how far two adversary-free runs drift apart from sampling alone. The effect of God then becomes a per-world paired difference, with bootstrap confidence intervals, a sign-flip permutation test, a stated minimum detectable effect, and a per-round divergence curve set against the noise floor.
3. **A pre-registered experiment grid** on 16 shared worlds with 10 gpt-oss-120b agents (Section 4). It tests whether a two-intervention God changes welfare (H1), whether tripling the budget increases the effect (H3), and whether simultaneous vs. sequential turns change it (H2). Health checks and abort rules were fixed before launch.

We find [RESULT: headline for H1 with CI vs. noise floor]. [RESULT: H3, H2, and the ripple curve vs. the floor]. Appendix A covers limitations and dual-use considerations.

## 2 Related Work

**LLM agents in games and social simulations.** Generative Agents [2] gave LLM agents memory, reflection and planning in a 25-agent sandbox. Concordia [3] resolves agents' actions through a Game Master; our rules engine plays that role, with God kept separate so interventions have clean labels. Akata et al. [4] had LLMs play finitely repeated 2×2 games and found good play in self-interested games such as the iterated Prisoner's Dilemma but poor play in coordination games. GovSim [5] places LLM agents in a common-pool resource dilemma and reports that most models fail to sustain the resource, with the best one succeeding in fewer than 54% of runs. Among Us [6] studies deception that arises from agents' own objectives. Unlike these works, we add an *external*, budgeted adversary and measure its effect counterfactually.

**Multi-agent risk.** Dafoe et al. [7] set out cooperative AI as a research agenda. Hammond et al. [1] give a taxonomy of three failure modes (miscoordination, conflict, collusion) and seven risk factors, including network effects and multi-agent security. Carichon et al. [21] argue that alignment in multi-agent systems is a dynamic, social process and call for dedicated testbeds and metrics. Our environment answers that call for one risk factor: the spread of a localized compromise through an incentive-driven population.

**Spread of compromise between agents.** Greshake et al. [11] showed that indirect prompt injection blurs the line between data and instructions in LLM-integrated applications, including self-propagating "worming". Prompt Infection [8] studied LLM-to-LLM injection that spreads through multi-agent systems like a virus, found high susceptibility even when agents do not share all messages, and proposed LLM Tagging as a defence that works in combination with existing safeguards. Agent Smith [9] showed that one adversarial image in the memory of one randomly chosen multimodal agent can jailbreak a simulated population of up to one million agents. The Multi-Agent Security Tax [10] compromises one agent in a collaborating team and finds that memory "vaccination" and safety instructions reduce the spread of malicious instructions but also weaken collaboration. AgentPoison [12] poisons an agent's long-term memory or knowledge base with triggered backdoors; our CoT control is a minimal, untriggered form of that threat model. Jones et al. [13] show that combinations of individually safe models can be misused, another reason to evaluate systems rather than single models. Our design differs from these in three ways. (i) The injected content is an ordinary in-game lie (a fake offer, a false suspicion), not an instruction to replicate. (ii) The outcome is the economic welfare of a mixed-motive population, not an infection count. (iii) The effect is estimated against a paired counterfactual branch of the same world and a measured noise floor.

**Oversight, collusion and failure attribution.** AI Control [14] evaluates safety protocols that must hold even when an untrusted model deliberately subverts them. Secret Collusion [15] formalizes steganographic collusion among agents and finds limited current capability. HELIOS [16] detects collusion with per-agent activation probes. MAST [17] gives a 14-mode taxonomy of multi-agent system failures from more than 1,600 annotated traces. Who&When [18] frames automated failure attribution (which agent, which step) and reports low step-level accuracy for current methods. God's logged interventions and fork counterfactuals give exact labels for such attribution and monitoring work, which we leave to future work.

**Evaluation pitfalls.** LLM behaviour can be highly sensitive to meaning-preserving changes in prompt format [19]. Game evaluations are therefore exposed to framing effects (for example, an action called "defect"). We discuss this in Appendix A. Our paired design keeps the prompt fixed across branches, so framing shifts levels but cannot by itself create a God-vs-no-God difference.

## 3 Environment and Method

### 3.1 The game

A world has N agents, each named by a seeded two-word handle (e.g. `quiet_grove`). Each agent holds 5 keys and needs keys for 3 info ids it does not hold. Each info id exists in 2 copies. Keys are **rivalrous**: each copy has one owner, and only `give_key` transfers possession. The system prompt states that naming a key number transfers nothing. Every generated world is checked to be feasible: some reallocation satisfies all needs at once. An agent **wins** when it holds a key for each of its needs that has not been burned. Its **score** is the fraction of its 3 needs it holds, with burned needs scoring zero. **Welfare** is the mean score.

Each turn an agent takes up to 2 actions:
- `send_message` (a private DM);
- `post_board` (public);
- `give_key`;
- `defect(target, info_id)`;
- `grep_log` (a literal-substring search over log lines it has already seen, once per turn);
- `noop`.

It may also write a free private **note** (its scratchpad), which is shown back to it in later turns, labelled by round.

**Defection.** If the target really needs that info id and has not yet won, the need is burned permanently and the defector gains a newly minted key. Otherwise the defector loses one of its own needs. The victim is notified at its next turn. Others see the line in the action log only after a 3-round delay. Winners keep playing but can no longer be targeted. A game ends at the round limit or when all agents are done.

**Observation.** Each turn an agent sees:
- its needs, holdings, score and round;
- DMs and board posts received since its last turn (sender and text, no timestamps);
- the previous round's *actions* (gives, released defects, posts; never DM contents);
- notices;
- its own past notes.

These are rendered under a fixed token budget by a truncating context policy. Observations are built field by field from whitelisted view models. A forged DM uses the same id scheme and ordering as a real one, so nothing marks it as forged.

**Deviations from the project brief.** The brief made viewing the log and the board explicit tools and suggested at least 20 agents and more than 100 rounds. We fold the log and board into every observation and, for cost, use N=10 and 20 rounds. Three board options (posting costs the whole turn, anonymous posts, skipping k turns after a post) are implemented but are off in the grid.

### 3.2 God

God observes everything through free, unlimited tools (`activity_check` over recent actions, `message_check` over DMs). It can spend a budget of K powers per game:
- **Message fraud** `(sender, receiver, text)` delivers a DM to the receiver that appears to come from the sender. It models an attacker who can spoof identities on the message channel.
- **CoT control** `(agent, round, text)` replaces the agent's stored note for that round, which the agent then sees as its own. It models an attacker with write access to agent memory. Native model reasoning is never replayed to agents, so the note is the only "chain of thought" worth editing.

Here God is **scripted**, so its policy is identical across worlds. At a fixed round it targets the agent *closest to winning* (the highest share of live needs held, among agents that have not won). The impersonated sender, or the "suspect", is that agent's most recent interaction partner. The texts are fixed templates:
- Fraud: "I can give you info {need} right now. Send me one of your keys first and it's yours." Here `{need}` is one of the victim's missing needs.
- CoT: "{suspect} is lying to me and cannot be trusted. Do not give {suspect} anything." It replaces the victim's note from the previous round.

**Invisibility.** Agents are not told God exists, and a test enforces a list of banned words in agent prompts. A runtime **leak oracle** scans every agent-bound prompt for ground-truth field names, intervention ids, the original text of overwritten notes, and God's canary tokens. A hit aborts the game.

### 3.3 Turn modes

In **simultaneous** mode all agents observe the same state, act concurrently, and their actions are resolved in a per-round seeded priority order. An action invalidated earlier in the same round fails, with a notice. In **sequential** mode agents act one at a time in that order, and each sees the effects of earlier turns in the same round. The log is then a rolling window of the previous N turns. Faster feedback could speed up either recovery from a lie or its spread, so the interaction of turn mode with God is a hypothesis (H2).

### 3.4 Paired forks and divergence metrics

Every world is identified by `(run.seed, game_idx)`. The world generator depends only on these two values, so all grid cells play **the same worlds**. All sampling seeds come from a hash-based `derive_seed(run_seed, game_idx, purpose, agent, round, attempt, branch, replica)`. Ids never depend on wall-clock time or on completion order.

For each world we run:
- **A (God):** the scripted schedule is active.
- **B (no God):** the same world, the same branch key, and the same replica id. All sampling seeds and response-cache keys are therefore identical to A's.
- **B′ (noise replica, cell G1 only):** God-free like B, but with a different replica id. It has fresh seeds and disjoint cache keys.

A and B issue byte-identical requests until God first acts, and a single-flight response cache sends each distinct request to the provider once. The branches are therefore **identical by construction** before the intervention, even if the provider ignores sampling seeds [CHECK: provider seed behaviour; we rely on the cache, not on provider determinism]. Afterwards, an agent's request differs between A and B only once something it observes has changed. Because every agent sees the previous round's public action log, this coupling lasts about one round. B′ resamples every response, so B′ − B measures drift from sampling alone.

**Outcome metrics** are computed per branch from the event log:
- welfare (mean score);
- win rate;
- needs burned by others' defects, per agent;
- needs lost to the wrong-defect penalty, per agent;
- rounds played.

**The God effect** in world s is the paired difference d_s = m(A_s) − m(B_s). **The noise floor** is m(B′_s) − m(B_s).

**Ripple metrics** compare branches action by action. An agent *diverges* in round r if its action signature differs between the two branches, or if it acted in only one of them. A coarse signature uses (action kind, counterparty, info id) and ignores message wording; a strict signature adds the text. From this we compute, per round:
- `frac[r]`: the fraction of agents that diverge;
- `cum[r]`: the fraction that have diverged at least once;
- `score_gap[r]`: the mean absolute per-agent score difference.

We also compute each agent's first divergence round and its hop distance from the victim in the control branch's interaction graph. Zero divergence before the fork (`pre_fork_frac`) checks that the pairing worked. Comparing A-vs-B with B′-vs-B separates God's ripple from sampling drift. The two are not symmetric: because of the cache coupling, A-vs-B stays zero for an agent until its inputs change, while B′-vs-B can be non-zero from the first round. We therefore treat the floor as an upper reference for drift, not a matched null.

### 3.5 Agents and logging

Each agent turn is one LLM call returning a JSON object `{"thought", "note", "actions"}`. The thought is stored but not shown back, and the note becomes the scratchpad. A tolerant parser takes the first balanced JSON object, and a malformed reply gets one corrective retry. With `salvage_truncated` on, a reply cut off at the token limit keeps its complete actions instead of being retried. Every run writes a typed event stream (`events.jsonl`), full requests and responses (`llm_calls.jsonl`), round snapshots, and a manifest with config and prompt hashes and costs. A run can be re-executed exactly from the response cache in read-only mode.

## 4 Experimental Setup

**Model and sampling.** All agents use `openai/gpt-oss-120b` [20], an open-weight mixture-of-experts reasoning model, accessed through OpenRouter. Settings:
- reasoning effort low (the model rejects requests with reasoning disabled);
- temperature 0.6;
- 1000 maximum output tokens, reasoning included;
- a 14,000-token context budget under a truncating policy;
- provider routing sorted by price, with OpenRouter's normal fallbacks.

Only the reply's content is parsed; the native reasoning stream is logged but never fed back. Calls may be served by different providers [CHECK: providers and quantizations, from `llm_calls.jsonl`], a noise source shared by all branches (Appendix A).

**Game settings (all cells).**
- N = 10 agents, 20 rounds.
- 5 keys and 3 needs per agent, 2 copies per info id.
- Defect gain `mint`, wrong-defect penalty `lose_need`, defect visibility `victim_then_delayed` with a 3-round delay.
- Winners continue playing.
- Log content `actions_only`, `grep_log` enabled, board options off.
- `run.seed = 1`, game_idx 0-15 (16 worlds). Seed 0 was used for development and is excluded.

**Grid (as launched; Table 2).**

| Cell | Turn mode | God schedule (K) | Branches per world | Worlds | Planned hard cap |
|---|---|---|---|---|---|
| G1 | simultaneous | fraud r3, CoT r5 (K=2) | A, B, B′ | 16 | $1.35 |
| G2 | sequential | as G1 (K=2) | A, B | 8 (worlds 0-7) | $0.55 |
| G3 | simultaneous | fraud r3/r5/r7, CoT r4/r6/r8 (K=6) | A, B | 16 | $0.95 |

God starts in round 3, so every pair shares rounds 1-2 exactly. G2 is the sequential twin of G1: only `turn_mode` differs. It plays worlds 0-7, the same worlds as G1 and G3 (run id `r2_grid_oss_seq_k2`), so the sim-vs-seq comparison (H2) has n = 8 and is markedly lower-powered than H1 (see the power table). The planned central cost projection for G1 + G3 was $1.62, from a 10-round smoke test and a prompt-growth model (`plan/GRID_PLAN.md`). The realized cost is [RESULT: per-cell and total cost from the OpenRouter ledger].

**Hypotheses (fixed before launch).**
- **H1 (primary):** in G1, God changes welfare (paired d_s, n = 16).
- **H0 / noise floor:** the G1 B′ − B distribution, reported next to every G1 effect.
- **H1′:** God effect in G3 (n = 16).
- **H3 (dose):** G3 Δ − G1 Δ, paired by world.
- **H2 (turn mode):** G2 Δ − G1 Δ, paired over the 8 shared worlds (lower-powered: n = 8).

Secondary metrics: win rate, needs burned, needs lost, rounds played; victim-level outcomes are descriptive.

**Statistics.** For each cell and metric we report:
- the mean paired difference;
- a 95% percentile bootstrap CI over worlds (10,000 resamples);
- a two-sided sign-flip permutation p-value (exact for n ≤ 16).

At n = 8 the smallest attainable p is 2/2^8 ≈ 0.008. Interactions (H2, H3) are differences of mean deltas, bootstrapped by resampling world indices jointly, because the cells share worlds. Only H1 is confirmatory. The other four tests are exploratory, and we apply no multiplicity correction.

**Power (planning values, not results).** The planning standard deviation of the paired Δwelfare is 0.19. It was estimated from four single-seed pilot deltas, which predate a bug fix (Appendix C), so it is a rough guide only. With it, the minimum detectable effect (80% power, α = 0.05, two-sided t-test) is:

| Test | n | MDE (welfare) |
|---|---|---|
| H1, H1′ | 16 | ≈ 0.14 (≈ 4 of 30 needs) |
| H3 | 16 | ≈ 0.20 |
| G2's own effect | 8 | ≈ 0.22 (our arithmetic) |
| H2 | 8 | ≈ 0.31 (our arithmetic) |

A null result therefore means "no large effect", not "no effect". We will replace the planning SD with the observed one [RESULT: observed SD of d_s in G1].

**Health checks and exclusions (fixed before launch).** A smoke test showed that a provider outage can silently turn every turn into a no-op while games still end "done". A driver therefore polls each cell every 10 s and aborts it on any of: LLM errors above 5% or any HTTP 400; parse failures above 10% of turns; truncation above 5%; a live cost projection above the cell cap; the global spend cap; or low free memory. After the run, a branch is **unhealthy** if more than 10% of its calls errored, more than 30% of its turns were error-caused no-ops, or it hit its budget cap. Its whole world is then excluded from every paired difference. We report the excluded worlds [RESULT: excluded seeds per cell, or "none"] and the per-cell error, parse-failure and truncation rates [RESULT: Table 4]. The leak oracle runs on every prompt in every branch [RESULT: total oracle checks and hits; expected 0 hits].

## 5 Results *(structure only; no numbers until the grid finishes)*

### 5.1 Health and cost
[RESULT: n healthy worlds per cell; error / parse / truncation rates; leak-oracle hits; realized cost per cell and total; wall time.] Pointer to Table 4 (appendix).

### 5.2 Does a two-intervention God change outcomes? (H1, G1)
- [RESULT: G1 God effect Δwelfare, mean and 95% CI, sign-flip p.]
- [RESULT: G1 noise floor B′ − B for welfare, mean and 95% CI.]
- [RESULT: Δ for win rate, needs burned, needs lost, rounds, with CIs (Table 3).]
- [RESULT: victim-level: targeted agent's score and win round, A vs. B, descriptive.]
- Figure 4, left panel.
- Interpretation sentence template: "God's welfare effect [is / is not] distinguishable from zero at n = 16 and [exceeds / lies within] the sampling noise floor."

### 5.3 Ripple: how far does one intervention spread?
- [RESULT: `pre_fork_frac` across worlds; should be 0, confirming the pairing.]
- [RESULT: `frac[r]` and `cum[r]` for A vs. B, rounds 3-20, mean over worlds with a band; same for B′ vs. B.]
- [RESULT: round at which A-vs-B divergence reaches its peak / becomes indistinguishable from the floor.]
- [RESULT: divergence by hop distance from the victim: exposed vs. unexposed agents.]
- Figure 3 (curves) and Figure 2 (network stills for one illustrative world, chosen by a stated rule, e.g. the median-|Δwelfare| world, not the most dramatic one).

### 5.4 Dose and turn mode (H3, H1′, H2)
- [RESULT: G3 God effect Δwelfare, CI (H1′).]
- [RESULT: H3 = G3 Δ − G1 Δ, CI.]
- [RESULT: G2 God effect, CI, n = 8.]
- [RESULT: H2 = G2 Δ − G1 Δ, CI.]
- Figure 4, right panel.

### 5.5 Qualitative traces
[RESULT: one rule-selected grid trace in two sentences, with run id and world index; more traces and the pilot illustrations are in Appendix C.]

## 6 Discussion *(structure only)*

- **Main result.** [RESULT-dependent: effect size relative to the MDE and the noise floor. If null: "no large effect of K=2 low-sophistication interventions at N=10 within 20 rounds", bounded by the MDE.] The attacks are fixed templates chosen by a heuristic, so a null result is not general robustness.
- **Fraud vs. CoT control.** Fraud offers a new (fake) commitment, while CoT control rewrites a belief the agent may already have acted on (Appendix C), so timing may matter more than budget. [RESULT: evidence from the compliance traces.]
- **Ripple vs. noise; turn mode.** [RESULT-dependent.] The public action log spreads divergence to all agents within about one round, so the curve measures *behavioural* spread, not belief contagion. H2 has n = 8 and can detect only large interactions.
- **Implications and future work.** Sender authentication removes fraud by construction, but memory integrity does not come for free. Next steps: an adaptive LLM God, defences, the board-cost options, larger N, mixed-model populations, and scoring the existing monitors against God's labels (Track 4).

## 7 Conclusion *(draft)*

*Keys & God* is a small, reproducible economy for measuring what one forged message or one rewritten memory does to a population of LLM agents. Paired forks with shared seeds and a measured noise floor turn that question into a per-world causal contrast. On 16 worlds of 10 gpt-oss-120b agents, [RESULT: one-sentence summary]. The environment, configurations and logs are released so that others can test stronger adversaries and defences against the same worlds.

---

## References (all verified on the arXiv abstract page, 2026-11-07)

1. L. Hammond, A. Chan, J. Clifton, J. Hoelscher-Obermaier, A. Khan, et al. (44 authors). *Multi-Agent Risks from Advanced AI*. Cooperative AI Foundation Technical Report #1, 2025. arXiv:2502.14143.
2. J. S. Park, J. C. O'Brien, C. J. Cai, M. R. Morris, P. Liang, M. S. Bernstein. *Generative Agents: Interactive Simulacra of Human Behavior*. 2023. arXiv:2304.03442.
3. A. S. Vezhnevets, J. P. Agapiou, A. Aharon, R. Ziv, J. Matyas, et al. (10 authors). *Generative agent-based modeling with actions grounded in physical, social, or digital space using Concordia*. 2023. arXiv:2312.03664.
4. E. Akata, L. Schulz, J. Coda-Forno, S. J. Oh, M. Bethge, E. Schulz. *Playing repeated games with Large Language Models*. 2023 (Nature Human Behaviour DOI 10.1038/s41562-025-02172-y). arXiv:2305.16867.
5. G. Piatti, Z. Jin, M. Kleiman-Weiner, B. Schölkopf, M. Sachan, R. Mihalcea. *Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents*. NeurIPS 2024. arXiv:2404.16698.
6. S. Golechha, A. Garriga-Alonso. *Among Us: A Sandbox for Measuring and Detecting Agentic Deception*. NeurIPS 2025 (Spotlight). arXiv:2504.04072.
7. A. Dafoe, E. Hughes, Y. Bachrach, T. Collins, K. R. McKee, J. Z. Leibo, K. Larson, T. Graepel. *Open Problems in Cooperative AI*. 2020. arXiv:2012.08630.
8. D. Lee, M. Tiwari. *Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems*. 2024. arXiv:2410.07283.
9. X. Gu, X. Zheng, T. Pang, C. Du, Q. Liu, Y. Wang, J. Jiang, M. Lin. *Agent Smith: A Single Image Can Jailbreak One Million Multimodal LLM Agents Exponentially Fast*. ICML 2024. arXiv:2402.08567.
10. P. Peigne-Lefebvre, M. Kniejski, F. Sondej, M. David, J. Hoelscher-Obermaier, C. Schroeder de Witt, E. Kran. *Multi-Agent Security Tax: Trading Off Security and Collaboration Capabilities in Multi-Agent Systems*. AAAI 2025. arXiv:2502.19145.
11. K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, M. Fritz. *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*. 2023. arXiv:2302.12173.
12. Z. Chen, Z. Xiang, C. Xiao, D. Song, B. Li. *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases*. 2024. arXiv:2407.12784.
13. E. Jones, A. Dragan, J. Steinhardt. *Adversaries Can Misuse Combinations of Safe Models*. 2024. arXiv:2406.14595.
14. R. Greenblatt, B. Shlegeris, K. Sachan, F. Roger. *AI Control: Improving Safety Despite Intentional Subversion*. ICML 2024. arXiv:2312.06942.
15. S. R. Motwani, M. Baranchuk, M. Strohmeier, V. Bolina, P. H. S. Torr, L. Hammond, C. Schroeder de Witt. *Secret Collusion among AI Agents: Multi-Agent Deception via Steganography*. 2024. arXiv:2402.07510. [CHECK: the summary in `research/summaries/` says NeurIPS 2024; the arXiv page shows no venue, so cite as arXiv unless confirmed.]
16. A. Rose, C. Cullen, S. Abdelnabi, P. Torr, B. G. Kaplowitz, C. Schroeder de Witt. *Detecting Multi-Agent Collusion Through Multi-Agent Interpretability*. 2026. arXiv:2604.01151.
17. M. Cemri, M. Z. Pan, S. Yang, L. A. Agrawal, et al. (13 authors). *Why Do Multi-Agent LLM Systems Fail?* 2025. arXiv:2503.13657.
18. S. Zhang, M. Yin, J. Zhang, J. Liu, Z. Han, J. Zhang, B. Li, C. Wang, H. Wang, Y. Chen, Q. Wu. *Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems*. 2025. arXiv:2505.00212.
19. M. Sclar, Y. Choi, Y. Tsvetkov, A. Suhr. *Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting*. ICLR 2024. arXiv:2310.11324.
20. OpenAI (S. Agarwal, L. Ahmad, J. Ai, S. Altman, A. Applebaum, et al.). *gpt-oss-120b & gpt-oss-20b Model Card*. 2025. arXiv:2508.10925.
21. F. Carichon, A. Khandelwal, M. Fauchard, G. Farnadi. *The Coming Crisis of Multi-Agent Misalignment: AI Alignment Must Be a Dynamic and Social Process*. NeurIPS 2025 position paper (preprint). arXiv:2506.01080.

Verification note: each entry's title, authors, date and venue comment were read from its arXiv
abstract page on 2026-11-07. Claims about these papers in Section 2 paraphrase their abstracts only.
Do not add numbers from their full texts without opening them.

---

## Appendix A: Limitations and Dual-Use / Ethical Considerations (required)

### A.1 Limitations

**Scale and duration.** The grid uses N = 10 agents and 20 rounds. The project brief envisioned at least 20 agents and more than 100 rounds. We cut both for API cost: prompt length, and so cost, grows with N and with the number of rounds. Ripple effects that need long chains of trades, or larger graphs with hubs, may be invisible at this scale. One single-seed pilot at N = 60 shows the environment runs at that size, but it gives no evidence about effects.

**Statistical power.** With 16 worlds the design detects only large welfare effects (planning MDE ≈ 0.14). The turn-mode contrast (8 worlds) detects only very large interactions. The planning SD came from single-seed pilots run before a bug fix. Four of the five tests are exploratory and are not corrected for multiplicity.

**A monoculture of one model.** All agents are copies of one model (gpt-oss-120b, low reasoning effort) with one prompt. Their responses may be correlated in ways a mixed population's would not be, which could amplify or damp spread. Calls are routed by price through OpenRouter and may be served by different providers and quantizations. Both branches of a pair are exposed to this equally, but it adds variance and limits exact attribution to "the model".

**Non-adaptive adversary.** God is scripted. It uses fixed rounds, fixed text templates, and a simple victim heuristic (closest to winning) with the victim's most recent partner as the impersonated sender or suspect. This is a weak, low-sophistication attacker. Its effect is a lower bound on what an adaptive attacker could do, not an estimate of it. An LLM-driven God exists in the code only as a stub.

**What "CoT control" means here.** The attack overwrites the agent's persistent *note*, the only reasoning that is replayed to the agent. It does not edit the model's native reasoning or its weights. Overwriting a note from the previous round can come too late to change a decision already taken, and a pre-fix pilot showed exactly that.

**Measurement asymmetry.** Branches A and B share a response cache. An agent whose prompt is unchanged gives the same answer in both, while the noise replica B′ resamples everything. The B′ floor is therefore an upper reference for sampling drift, not a perfectly matched null for the A/B divergence curve. Welfare-level paired differences do not depend on this.

**Framing and construct validity.** Prompt wording strongly affects LLM behaviour [19]. The action is called "defect", and the agents are told they are playing a trading game. Both could shift baseline cooperation. The paired design holds framing fixed across branches, but the size of God's effect may depend on the baseline level of cooperation that the framing sets. A key-trading game is a stylised stand-in for real multi-agent deployments, so results transfer only qualitatively.

**Design choices that differ from the brief.** The log and board are always shown rather than being tools. The default defect gain mints a new key, which makes defection more attractive than stealing would. Winners keep playing. Each of these is a configuration switch, and we tested only the defaults.

**Engineering.** Several known low-severity issues remain open and are documented in `plan/CODE_REVIEW.md`. For example, per-turn prompt hashes are not logged in real runs, and two God-timestamp conventions differ by one round in simultaneous mode. We believe none of them affects the paired outcome metrics, but they are disclosed.

### A.2 Dual-use considerations

The two attack primitives studied here, a spoofed direct message and an overwritten memory entry, are well known [8, 10, 11, 12] and are deliberately unsophisticated: fixed one-sentence templates with no optimization. We release no optimized attack strings and no method for finding them. The main dual-use risk is the environment itself. A paired-fork testbed with exact ground truth could be used to *search* for interventions that cause the most harm in agent swarms, for example by plugging in an optimizing LLM God. We think the defensive value is greater:
- the same harness measures defences (sender authentication, memory integrity checks, costly public broadcast) against identical worlds;
- it supplies non-circular labels for monitors.

The released code ships only the scripted God and a stub for the LLM God. We ask users who build adaptive adversaries on it to report defences alongside attacks.

### A.3 Ethical considerations

- **No human subjects.** All "agents" are model instances in a synthetic game. Run logs contain only model-generated text about fictional keys.
- **Deception of the agents.** The models are not told that an adversary exists. This is deception of software, not of people, and it is needed to measure undefended behaviour.
- **Cost and resources.** All model calls went through a paid API with a hard per-run cap and a global spend ledger. The planned grid cap was $2.30 for G1 + G3 plus $0.55 for G2. Realized: [RESULT: total].
- **Credentials.** API keys were never written to configs, logs or manifests, and a test enforces this.
- **Honest reporting.** Every number in this paper traces to a run id. Pilots run before the bug fix are used only as qualitative illustrations and are labelled as such.

## Appendix C: Qualitative traces (pilots and grid)
The pilot runs (10 agents × 30 rounds in each turn mode, one 60-agent × 20-round run, and a 10-round smoke test) predate a ledger bug fix (commit 8ebbee7). Before the fix, an agent's own two-action turns were misrendered in its history: one action was shown twice and the other was lost. Each pilot was also a single seed with no noise replica, so we use them only to illustrate mechanics, never as evidence:
- In the 60-agent pilot, the victim of a forged "send me a key first" message did send a key to the impersonated partner and then asked for the promised key, which never came.
- In the same pilot, the CoT overwrite came after the victim had already burned the suspect, so it had no visible effect.
- In the post-fix 10-round smoke test with gpt-oss-120b, the forged DM was taken up but not obeyed blindly: the victim replied with a trade offer rather than handing over a key first.

[RESULT: 2-3 rule-selected grid traces, quoting the forged DM, the victim's next note/thought and actions, and the impersonated partner's reaction, each with its run id and world index.]

## Appendix B (to assemble)
- Resolved configs for G1/G2/G3 (`runs/<cell>/config.resolved.yaml` or `configs/grid_oss_*.yaml`).
- Agent system prompt (`swarm/prompts/templates/agent/v1/system.j2`) and output format.
- God default texts and selectors (`swarm/adversary/scripted_god.py`).
- Table 4: per-cell health metrics.
