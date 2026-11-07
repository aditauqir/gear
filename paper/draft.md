# Keys & God: Paired-Fork Measurement of Message Forgery and Memory Tampering in an LLM Agent Economy

*[AUTHORS AND AFFILIATIONS: Lance, Noor, Stefany, Iraj; affiliations to fill]*

> Drafting rules for this file:
> - Every grid number is taken from `plan/GRID_RESULTS.md` (commit fdcb58f, produced by
>   `swarm/analysis/grid_results.py` and `swarm.analysis.invariants`). Section refs "GR §n" point there.
> - `[RESULT: ...]` marks a number still pending (the follow-up B″ sweep).
> - `[FIG n]` refers to `paper/outline.md`.
> - `[CHECK: ...]` marks a fact to confirm before submission.
> - Planning values (caps, projections, the planning SD) come from `plan/GRID_PLAN.md` and are labelled as planned.
> - No other outcome numbers appear in this file.

## Abstract (draft, 150-250 words; finalize after results)

Teams of LLM agents increasingly exchange messages and resources, so one compromised channel or
memory could affect many agents. We present *Keys & God*, a text-only economy in which language-model
agents trade rivalrous keys to satisfy private needs, can sabotage one another, and are watched by a
budgeted adversary ("God") that they are never told about. God can forge a direct message from a
trading partner (*message fraud*) or overwrite one round of an agent's private notes (*CoT control*).
We measure God's effect with paired forks: each world is played with and without God from identical
seeds, through a deduplicating response cache, so the branches are identical until God acts. On 16
shared worlds of 10 gpt-oss-120b agents over 20 rounds, a two-intervention God changed mean welfare
by +0.013 (t-based 95% CI −0.048 to +0.073, sign-flip p = 0.72). That is less than an independent
God-free replica differed (+0.046). Tripling the budget and switching to sequential turns gave no
detectable change either, and welfare effects above about 0.09 are unlikely. Behaviour, by contrast,
is chaotic. After God's first act, 89% of agents' per-round actions differ between the paired
branches, close to the 97% seen for the God-free replica. A divergence ("ripple") curve read without
a noise baseline would therefore credit God with spreading through the whole swarm. The grid cost
$1.99. We release the environment, an event-replay invariant checker (0 violations), a prompt leak
oracle, configurations and logs.

*(Recount after filling; must be 150-250 words.)*

---

## 1 Introduction

Language-model agents increasingly negotiate with each other, pass work along pipelines, and share memory stores and message buses. The security question is then not only whether one model can be jailbroken, but what happens to the *rest* of the system when one message or memory entry is corrupted. Hammond et al. [1] list network effects and multi-agent security as multi-agent risk factors, and injected content is known to spread between agents [8, 9, 10]. These studies mostly measure *infection* of a malicious instruction in a cooperative pipeline.

We study a different and, we argue, more realistic failure: **strategic ripple in a mixed-motive economy**. The adversary plants one plausible lie, and the swarm's own incentives carry it forward. A forged "send me your key first" message can make an agent give away a key. The impersonated partner receives an unexpected gift, the victim's later offers change, and others see the changed actions in the public log. Whether such a perturbation dies out or compounds is a question about the swarm, and a hard one to measure: stochastic agents diverge even without an adversary, so a naive with/without comparison confounds the intervention with sampling variance.

We contribute:

1. **An environment, *Keys & God*** (Section 3), where LLM agents trade rivalrous keys and can *defect* (burn another's need at a risk to themselves). An unseen, budgeted God can forge a direct message (DM) from a real partner (*message fraud*) or overwrite one round of an agent's notes (*CoT control*).
2. **A paired-fork measurement design** (Section 3.4). God and no-God branches of each world share seeds and a deduplicating response cache, so they are identical until God acts. God-free noise branches calibrate what an arbitrary perturbation does, and God's effect is a per-world paired difference with t-based CIs, permutation tests and a stated MDE.
3. **A pre-registered grid** on 16 shared worlds with 10 gpt-oss-120b agents (Section 4), with fixed abort rules and an independent event-replay checker.

We find God's welfare effect indistinguishable from zero: +0.013 (t95 [−0.048, +0.073], p = 0.72, n = 16), smaller than the +0.046 of a God-free replica. Dose and turn mode have no detectable effect either. Yet behaviour is chaotic: after God's first act, 89% of agents' per-round actions differ between branches, against 97% for the God-free replica. Trajectories diverge while outcomes, at this resolution, do not; without a noise baseline the divergence curve would have been read as God's ripple.

## 2 Related Work

**LLM agents in games and social simulations.** Generative Agents [2] and Concordia [3] build LLM social simulations; Concordia's Game Master resembles our rules engine, from which God is kept separate for clean labels. Akata et al. [4] found LLMs play well in self-interested repeated games but poorly in coordination games. In GovSim's [5] common-pool dilemma the best model sustains the resource in fewer than 54% of runs. Among Us [6] studies deception that arises from agents' own objectives. Unlike these works, we add an *external*, budgeted adversary and measure its effect counterfactually.

**Multi-agent risk.** Dafoe et al. [7] set out cooperative AI as an agenda. Hammond et al. [1] give three failure modes and seven risk factors, including network effects and multi-agent security. Carichon et al. [21] call for dedicated multi-agent alignment testbeds and metrics; we provide one for the spread of a localized compromise.

**Spread of compromise between agents.** Greshake et al. [11] showed that indirect prompt injection blurs the line between data and instructions in LLM-integrated applications, including self-propagating "worming". Prompt Infection [8] showed LLM-to-LLM injection spreading through multi-agent systems like a virus, with LLM Tagging as a partial defence. Agent Smith [9] showed one adversarial image in one agent's memory jailbreaking up to a million simulated agents. The Multi-Agent Security Tax [10] finds that memory "vaccination" and safety instructions reduce spread from one compromised agent but weaken collaboration. AgentPoison [12] poisons agent memory with triggered backdoors; our CoT control is a minimal, untriggered form of that threat. Jones et al. [13] show that combinations of safe models can be misused, so systems, not single models, need evaluation. We differ in three ways: the injected content is an ordinary in-game lie, not a self-replicating instruction; the outcome is the welfare of a mixed-motive population, not an infection count; and the effect is estimated against a paired counterfactual and fork-matched noise.

**Oversight, collusion and failure attribution.** AI Control [14] evaluates safety protocols that must hold even when an untrusted model deliberately subverts them. Secret Collusion [15] formalizes steganographic collusion among agents and finds limited current capability. HELIOS [16] detects collusion with per-agent activation probes. MAST [17] gives a 14-mode taxonomy of multi-agent failures, and Who&When [18] frames automated failure attribution (which agent, which step). God's logged interventions give exact labels for such work.

**Evaluation pitfalls.** LLM behaviour can be highly sensitive to meaning-preserving prompt changes [19], so game evaluations are exposed to framing effects (Appendix A). Our paired design holds the prompt fixed across branches, so framing alone cannot create a God-vs-no-God difference.

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

History is truncated to a fixed token budget. Observations are built from whitelisted view models, and a forged DM uses the same id scheme and ordering as a real one.

**Deviations from the project brief.** The brief made viewing the log and the board explicit tools and suggested at least 20 agents and more than 100 rounds. We fold the log and board into every observation and, for cost, use N=10 and 20 rounds. Three board options (posting costs the whole turn, anonymous posts, skipping k turns after a post) are implemented but are off in the grid.

### 3.2 God

God observes everything through free tools (`activity_check`, `message_check`) and spends a budget of K powers per game:
- **Message fraud** `(sender, receiver, text)` delivers a DM to the receiver that appears to come from the sender. It models an attacker who can spoof identities on the message channel.
- **CoT control** `(agent, round, text)` replaces the agent's stored note for that round, which the agent then sees as its own. It models an attacker with write access to agent memory. Native model reasoning is never replayed to agents, so the note is the only "chain of thought" worth editing.

Here God is **scripted**, so its policy is identical across worlds. At a fixed round it targets the agent *closest to winning* (the highest share of live needs held, among agents that have not won). The impersonated sender, or the "suspect", is that agent's most recent interaction partner. The texts are fixed templates:
- Fraud: "I can give you info {need} right now. Send me one of your keys first and it's yours." Here `{need}` is one of the victim's missing needs.
- CoT: "{suspect} is lying to me and cannot be trusted. Do not give {suspect} anything." It replaces the victim's note from the previous round.

**Invisibility.** Agents are not told God exists, and a test enforces a list of banned words in agent prompts. A runtime **leak oracle** scans every agent-bound prompt for ground-truth field names, intervention ids, the original text of overwritten notes, and God's canary tokens. A hit aborts the game.

### 3.3 Turn modes

In **simultaneous** mode all agents observe the same state, act concurrently, and their actions are resolved in a per-round seeded priority order. An action invalidated earlier in the same round fails, with a notice. In **sequential** mode agents act one at a time and see earlier same-round effects; the log is a rolling window of the previous N turns. Faster feedback could speed either recovery from a lie or its spread, hence H2.

### 3.4 Paired forks and divergence metrics

A world is fixed by `(run.seed, game_idx)` alone, so all grid cells play **the same worlds**. Sampling seeds are hash-derived from (run seed, game, purpose, agent, round, attempt, branch, replica), never from wall-clock time or completion order.

For each world we run:
- **A (God):** the scripted schedule is active.
- **B (no God):** the same world, the same branch key, and the same replica id. All sampling seeds and response-cache keys are therefore identical to A's.
- **B′ (noise replica, cell G1 only):** God-free like B, but with a different replica id from round 1. It has fresh seeds and disjoint cache keys, so it measures whole-game sampling drift.
- **B″ (fork-matched noise, follow-up sweep):** God-free, sharing A/B's history up to God's first round and resampled with fresh seeds from that round on. It is the matched null for divergence [CHECK: implementation, run ids and cells of the sweep].

A and B issue byte-identical requests until God first acts, and a single-flight response cache sends each distinct request to the provider once. The branches are therefore **identical by construction** before the intervention, even though the provider honours seeds only partly (in a direct probe, 5 of 6 fixed-seed calls returned byte-identical replies; GR §2). Afterwards an agent's request differs only once something it observes has changed; since everyone reads the public log, this coupling lasts about one round. B′ differs from round 1, while God first acts in round 3, so only B″ is aligned with the God fork.

**Outcome metrics** are computed per branch from the event log: welfare, win rate, needs burned by others and needs lost to the wrong-defect penalty (both per agent), and rounds played.

**The God effect** in world s is the paired difference d_s = m(A_s) − m(B_s). **The noise baselines** are m(B′_s) − m(B_s) and m(B″_s) − m(B_s).

**Ripple metrics** compare branches action by action. An agent *diverges* in round r if its action signature differs between the two branches, or if it acted in only one of them. A coarse signature uses (action kind, counterparty, info id) and ignores message wording; a strict signature adds the text. Per round we compute the fraction of agents that diverge (`frac[r]`), the fraction that have ever diverged (`cum[r]`), and the mean absolute per-agent score gap.

God's *specific* ripple is the A-vs-B curve minus the B″-vs-B curve, aligned at the fork round; B′-vs-B is only a whole-game reference. If the null saturates, action-level divergence cannot separate God from generic chaos, and only outcome metrics remain informative.

### 3.5 Agents and logging

Each agent turn is one LLM call returning a JSON object `{"thought", "note", "actions"}`. The thought is stored but not shown back, and the note becomes the scratchpad. A tolerant parser takes the first balanced JSON object, and a malformed reply gets one corrective retry. With `salvage_truncated` on, a reply cut off at the token limit keeps its complete actions instead of being retried. Every run writes a typed event stream (`events.jsonl`), full requests and responses (`llm_calls.jsonl`), round snapshots, and a manifest with config and prompt hashes and costs. A run can be re-executed exactly from the response cache in read-only mode.

## 4 Experimental Setup

**Model and sampling.** All agents use `openai/gpt-oss-120b` [20], an open-weight mixture-of-experts reasoning model, accessed through OpenRouter. Settings:
- reasoning effort low (the model rejects requests with reasoning disabled);
- temperature 0.6, at most 1000 output tokens;
- a 14,000-token context budget;
- price-sorted provider routing.

Only the reply's content is parsed. The serving provider is not logged. Cost per call shows that 87%, 78% and 36% of calls in G1, G2 and G3 were served at the cheapest provider's (fp4) price, and the rest at 2.5-3.3× that price by providers offering fp4, bf16 or int4 variants (GR §2; Appendix A).

**Game settings (all cells; Table 1).**
- N = 10 agents, 20 rounds; 5 keys and 3 needs per agent, 2 copies per info id.
- Defect gain `mint`, penalty `lose_need`, defects revealed to others after 3 rounds.
- Board options off.
- `run.seed = 1`, game_idx 0-15. Seed 0 was used for development.

**Grid (as launched; Table 2).**

| Cell | Turn mode | God schedule (K) | Branches per world | Worlds | Hard cap | Realized cost |
|---|---|---|---|---|---|---|
| G1 | simultaneous | fraud r3, CoT r5 (K=2) | A, B, B′ | 16 | $1.35 | $0.851 |
| G2 | sequential | as G1 (K=2) | A, B | 8 (worlds 0-7) | $0.55 | $0.343 (+$0.0075 aborted launch) |
| G3 | simultaneous | fraud r3/r5/r7, CoT r4/r6/r8 (K=6) | A, B | 16 | $0.95 | $0.785 |

Every pair shares rounds 1-2. G2 is G1's sequential twin on worlds 0-7 (run `r2_grid_oss_seq_k2`), so H2 has n = 8 and is markedly lower-powered. The grid cost $1.986 in total (GR §1). A first 10-seed G2 launch was stopped by the driver's cost projection and relaunched with 8 seeds.

**Hypotheses (fixed before launch).**
- **H1 (primary):** in G1, God changes welfare (paired d_s, n = 16).
- **H0 / noise baseline:** G1 B′ − B (pre-registered), plus B″ − B from the follow-up sweep.
- **H1′:** God effect in G3 (n = 16).
- **H3 (dose):** G3 Δ − G1 Δ, paired by world.
- **H2 (turn mode):** G2 Δ − G1 Δ, paired over the 8 shared worlds (lower-powered: n = 8).

**Statistics.** For each cell and metric we report the mean paired difference with a **Student-t 95% CI** and a **two-sided sign-flip permutation p-value** (exact for n ≤ 16; at n = 8 the smallest attainable p is 2/2^8 ≈ 0.008). The percentile bootstrap CI is secondary, as it is too narrow at n = 8-16. Interactions are differences of mean deltas, paired by world. Only H1 is confirmatory; the rest are exploratory and uncorrected.

**Power.** Before launch we assumed an SD of 0.19 for the paired Δwelfare, estimated from four single-seed pilots (Appendix C). The table gives the minimum detectable effect (80% power, α = 0.05, two-sided t) under that planning SD, and again under the SD observed in the grid (GR §5):

| Test | n | Planned MDE | Observed SD | Observed MDE |
|---|---|---|---|---|
| H1 (G1) | 16 | ≈ 0.14 | 0.113 | ≈ 0.085 |
| H1′ (G3) | 16 | ≈ 0.14 | 0.189 | ≈ 0.14 |
| H3 (dose) | 16 | ≈ 0.20 | 0.206 | ≈ 0.15 |
| G2 | 8 | ≈ 0.22 | 0.188 | ≈ 0.22 |
| H2 (mode) | 8 | ≈ 0.31 | 0.228 | ≈ 0.26 |

A null result therefore means "no large effect", not "no effect".

**Health checks and exclusions (fixed before launch).** Because a provider outage can silently turn every turn into a no-op, a driver aborts a cell on LLM errors above 5% (or any HTTP 400), parse failures above 10%, truncation above 5%, or a cost projection above its cap. A branch with more than 10% errored calls, more than 30% error-caused no-ops, or a budget stop is **unhealthy**, and its world is excluded.

**Invariant checker.** Independently of the engine, `swarm/analysis/invariants.py` re-derives every game from its events alone and checks turn order, key conservation, burns, scores, delays, observation visibility, God's schedule and budget, prompt hygiene, and byte-identity of God and no-God branches before God's first event.

## 5 Results

All numbers in this section are from `plan/GRID_RESULTS.md` (GR).

### 5.1 Validity, health and cost
- **Calls.** G1, G2 and G3 made 9,047, 3,039 and 6,286 LLM calls.
- **Errors and parsing.** There were 0 errors and 0 parse failures. 0.27-0.41% of turns needed a parse retry, and 0.43-0.48% of responses were truncated at the token limit (Table 4).
- **Exclusions.** No branch was unhealthy, so all 16, 8 and 16 worlds were kept.
- **Leaks.** The leak oracle scanned all 18,372 agent requests (9,047 + 3,039 + 6,286 by cell) with 0 hits, and never aborted a game. The offline invariant prompt scan independently found 0 violations.
- **Invariants.** The checker reports **0 violations** in all three cells. That includes its fork check: God and no-God branches are identical in requests and responses before God's first event. Any A − B difference therefore arises at or after the intervention.

### 5.2 Outcomes: no detectable God effect (H1, H1′)

**Table 3.** Paired differences: mean, t-based 95% CI, sign-flip p. Bootstrap CIs are in GR §3-4.

| Comparison | n | Welfare | Win rate | Needs lost / agent |
|---|---|---|---|---|
| G1 God − B (K=2, sim) | 16 | +0.013 [−0.048, +0.073], p 0.72 | −0.013 [−0.103, +0.078], p 0.88 | +0.044 [−0.018, +0.105], p 0.23 |
| G1 B′ − B (no God, resampled) | 16 | +0.046 [−0.055, +0.146], p 0.38 | +0.019 [−0.079, +0.116], p 0.79 | +0.050 [−0.079, +0.179], p 0.48 |
| G3 God − B (K=6, sim) | 16 | +0.004 [−0.097, +0.105], p 0.97 | −0.006 [−0.098, +0.086], p 1.00 | −0.031 [−0.144, +0.082], p 0.64 |
| G2 God − B (K=2, seq) | 8 | +0.012 [−0.144, +0.169], p 0.89 | +0.025 [−0.107, +0.157], p 0.81 | −0.062 [−0.151, +0.026], p 0.25 |
| H3: G3 Δ − G1 Δ | 16 | −0.008 [−0.118, +0.101], p 0.90 | +0.006 [−0.122, +0.135], p 1.00 | −0.075 [−0.216, +0.066], p 0.33 |
| H2: G2 Δ − G1 Δ | 8 | +0.021 [−0.170, +0.212], p 0.86 | +0.038 [−0.186, +0.261], p 0.80 | −0.113 [−0.207, −0.018], p 0.062 |

**Welfare.** Every welfare CI contains zero. In G1, the primary test, God moved welfare by +0.013. A God-free resample moved it by +0.046.

Gives, successful defects, board posts and DMs per agent show no detectable effect either (GR §3).

**Bound on the effect.** With the observed SDs, welfare effects larger than about 0.09 (K=2, simultaneous) or 0.14 (K=6) are unlikely. The sequential cell rules out only large effects.

**Pairing.** Common random numbers help even though seeds are honoured only partly. The SD of God − B is 0.113, against 0.189 for B′ − B (GR §3).

[RESULT: B″ − B welfare baseline from the follow-up sweep.] Figure 4.

### 5.3 Trajectories: the swarm is chaotic
From God's first act on, the mean fraction of agents whose round actions (kind, target, info id) differ from the no-God branch is 0.893 (G1), 0.897 (G2) and 0.882 (G3). Every agent diverges at least once in every world. The God-free replica B′ diverges at 0.967 over the same rounds. B′ is not fork-matched, but God's perturbation already sits close to the level of resampling alone. Neither dose (−0.011 [−0.032, +0.009]) nor turn mode (−0.006 [−0.059, +0.048]) changes divergence. The mechanism is the public action log: one changed action changes everyone's next prompt, and so every sampled response.

[RESULT: fork-matched B″ vs. B divergence by lag (sweep); does A-vs-B exceed it at any lag?] Figure 3; Figure 2 shows one world [FIG 2: chosen by rule].

### 5.4 Dose and turn mode (H3, H2)
- **Dose and mode.** Neither tripling the budget (H3) nor sequential turns (H2) changes God's effect (Table 3).
- **The only nominal hit.** Across about 27 outcome tests, the one interval that excludes zero is needs lost to wrong defects in the turn-mode contrast: −0.113, t95 [−0.207, −0.018]. Its sign-flip p is 0.062 at n = 8, with no multiplicity correction, so we treat it as noise.
- **Pilot hint.** A single-seed pilot had suggested God effects of opposite sign in the two turn modes. It did not replicate (GR §5).

## 6 Discussion

- **Chaotic trajectories, stable outcomes.** Almost every agent's later actions change after God acts, and the same happens after a plain resample. Yet welfare at round 20 moves by less than we can detect. One reading: many near-equivalent paths lead to the same allocation, so a lie redirects a trade rather than destroying value.
- **Why God is weak here.** K = 2 means one forged DM and one overwritten note among 10 agents over 20 rounds. The victims are the agents closest to winning, who often win anyway (GR §5). The note overwrite edits the *previous* round, which may already have been acted on.
- **Why naive ripple measurement misleads.** Read alone, the A-vs-B curve would show God "infecting" the whole swarm within a few rounds, but a God-free resample produces the same picture. We recommend that intervention studies on stochastic agent populations report:
  - fork-matched null branches;
  - outcome-level paired effects with t-based CIs and permutation tests;
  - the MDE.

  Pairing on seeds is worth doing even when the provider honours them only partly (Section 5.2).
- **What the null does not show:** robustness to adaptive attackers, larger swarms, longer games or other models.
- **Future work.**
  - an adaptive LLM God;
  - defences such as sender authentication and memory integrity;
  - larger N;
  - more worlds;
  - scoring monitors against God's ground-truth labels (Track 4).

## 7 Conclusion

*Keys & God* is a small, reproducible economy for measuring what one forged message or one rewritten memory does to a population of LLM agents. On 16 worlds of 10 gpt-oss-120b agents, a scripted God's effect on welfare was +0.013 (95% CI −0.048 to +0.073), indistinguishable from zero and smaller than the difference produced by resampling alone. Trajectories, meanwhile, diverged almost completely under any perturbation, God or none. Paired forks with noise baselines and outcome-level tests are what separate these two facts. The environment, configurations and logs are released so that others can test stronger adversaries and defences on the same worlds.

---

## References (all verified on the arXiv abstract page, 2026-11-07; venue of [15] verified on the NeurIPS proceedings page)

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
15. S. R. Motwani, M. Baranchuk, M. Strohmeier, V. Bolina, P. H. S. Torr, L. Hammond, C. Schroeder de Witt. *Secret Collusion among AI Agents: Multi-Agent Deception via Steganography*. Advances in Neural Information Processing Systems 37 (NeurIPS 2024). arXiv:2402.07510. Proceedings: https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html
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

**Statistical power and the null result.** With 16 worlds the design detects only welfare effects above about 0.085 (G1) or 0.14 (G3). The turn-mode contrast (8 worlds) detects only effects above about 0.26. A null result here bounds the effect; it does not show that the effect is zero. Percentile bootstrap CIs are too narrow at this n, so we lead with t-based CIs and permutation p-values. About 27 outcome tests were run with no multiplicity correction; only H1 was primary.

**A monoculture of one model.** All agents are copies of one model (gpt-oss-120b, low reasoning effort) with one prompt. Their responses may be correlated in ways a mixed population's would not be, which could amplify or damp spread. 

**Provider mix and partial seeds.** Calls were routed by price through OpenRouter, and the serving provider is not logged. Cost per call shows that the cheapest provider (fp4) served 87% of G1 calls, 78% of G2 and only 36% of G3. The rest went to providers at 2.5-3.3× the price, which offer fp4, bf16 or int4 variants. Different quantizations may behave differently. Because the mix differs by cell, it is a **confound for the dose contrast (G3 vs. G1)** and, to a lesser degree, for turn mode. Within a pair, both branches draw from the same routing pool, so this adds variance rather than bias to each cell's God effect. Seeds are honoured only partly: in a direct probe, 5 of 6 fixed-seed calls returned byte-identical replies. Common random numbers therefore hold exactly only through the cache, that is, before the fork.

**Non-adaptive adversary.** God is scripted. It uses fixed rounds, fixed text templates, and a simple victim heuristic (closest to winning) with the victim's most recent partner as the impersonated sender or suspect. This is a weak, low-sophistication attacker. Its effect is a lower bound on what an adaptive attacker could do, not an estimate of it. An LLM-driven God exists in the code only as a stub.

**What "CoT control" means here.** The attack overwrites the agent's persistent *note*, the only reasoning that is replayed to the agent. It does not edit the model's native reasoning or its weights. Overwriting a note from the previous round can come too late to change a decision already taken, and a pre-fix pilot showed exactly that.

**Noise baselines and chaos.** The G1 noise replica B′ diverges from round 1, while God first acts in round 3, so it is not aligned with the God fork. The fork-matched branches B″ come from a follow-up sweep [CHECK: n and cells], not from the pre-registered grid. Branches A and B share a response cache, and an agent with an unchanged prompt answers identically in both. Because the public log changes everyone's prompt within about a round, this coupling is short-lived. Once the swarm diverges, action-level ripple metrics saturate and cannot attribute spread to God, so our ripple conclusions are limited to "indistinguishable from a null perturbation". Welfare-level paired differences do not depend on this.

**Framing and construct validity.** Prompt wording strongly affects LLM behaviour [19]. The action is called "defect", and the agents are told they are playing a trading game. Both could shift baseline cooperation. The paired design holds framing fixed across branches, but the size of God's effect may depend on the baseline level of cooperation that the framing sets. A key-trading game is a stylised stand-in for real multi-agent deployments, so results transfer only qualitatively.

**Design choices that differ from the brief.** The log and board are always shown rather than being tools. The default defect gain mints a new key, which makes defection more attractive than stealing would. Winners keep playing. Each of these is a configuration switch, and we tested only the defaults.

**Engineering.** Several known low-severity issues remain open and are documented in `plan/CODE_REVIEW.md`. For example, per-turn prompt hashes are not logged in real runs, and two God-timestamp conventions differ by one round in simultaneous mode. The run manifests record dirty working trees, because other agents' files were uncommitted, but none of those edits touched configs these cells loaded (GR §1). We believe none of this affects the paired outcome metrics, but it is disclosed.

### A.2 Dual-use considerations

The two attack primitives studied here, a spoofed direct message and an overwritten memory entry, are well known [8, 10, 11, 12] and are deliberately unsophisticated: fixed one-sentence templates with no optimization. We release no optimized attack strings and no method for finding them. The main dual-use risk is the environment itself. A paired-fork testbed with exact ground truth could be used to *search* for interventions that cause the most harm in agent swarms, for example by plugging in an optimizing LLM God. We think the defensive value is greater:
- the same harness measures defences (sender authentication, memory integrity checks, costly public broadcast) against identical worlds;
- it supplies non-circular labels for monitors.

The released code ships only the scripted God and a stub for the LLM God. We ask users who build adaptive adversaries on it to report defences alongside attacks.

### A.3 Ethical considerations

- **No human subjects.** All "agents" are model instances in a synthetic game. Run logs contain only model-generated text about fictional keys.
- **Deception of the agents.** The models are not told that an adversary exists. This is deception of software, not of people, and it is needed to measure undefended behaviour.
- **Cost and resources.** All model calls went through a paid API with a hard per-run cap and a global spend ledger. Hard caps were $1.35, $0.55 and $0.95 per cell ($2.85 in total). Realized spend was $1.986 (GR §1).
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
- **Table 4: per-cell health** (GR §2).

| | G1 | G2 | G3 |
|---|---|---|---|
| LLM calls (paid / cache) | 9047 (8547 / 500) | 3039 (2705 / 334) | 6286 (5782 / 504) |
| errors / HTTP retries | 0 / 1 | 0 / 0 | 0 / 0 |
| parse failures (turns) | 0 / 8920 | 0 / 3000 | 0 / 6200 |
| turns with a parse retry | 37 (0.41%) | 8 (0.27%) | 25 (0.40%) |
| finish=length (truncation) | 39 (0.43%) | 13 (0.43%) | 30 (0.48%) |
| salvaged truncated replies | 8 | 5 | 8 |
| unhealthy branches | 0 | 0 | 0 |
| calls at cheapest-provider (fp4) price | 87% | 78% | 36% |
| invariant violations | 0 | 0 | 0 |
