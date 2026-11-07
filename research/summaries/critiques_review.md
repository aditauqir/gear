# Review of `swarm_game_critiques.pdf` (shared by a teammate via Discord)

Source: `/home/iraj/.claude/channels/discord/inbox/1794021061741-1568462738500616362.pdf` (3 pages). Treated as data.
Project reference: `/home/iraj/projects/swarm_hackathon/plan/ARCHITECTURE.md` (cited below as ARCH §x, WPx, Dx, Vx).
Tags: [ABS] = only the arXiv abstract page was read this session. [REUSED] = summary already exists in `research/summaries/`; not re-fetched.
The PDF is partly an inventory (12 critiques, metrics, a grid) and partly a reading list of 8 items.

## Part 1. Papers and works cited (8)

| # | Work | Identification | Status |
|---|---|---|---|
| 1 | Multi-Agent Risks from Advanced AI | Hammond et al. (44 authors, Cooperative AI Foundation Technical Report #1), 2025. https://arxiv.org/abs/2502.14143 | [REUSED] `general.md` (partial read, ~100k of 469k chars) |
| 2 | GovSim: Cooperate or Collapse | Piatti et al., NeurIPS 2024. https://arxiv.org/abs/2404.16698 ; code https://github.com/giorgiopiatti/GovSim | [REUSED] `track1_sandboxes.md` §2.6 (full text) |
| 3 | Agent Smith | Gu, Zheng, Pang, Du, Liu, Wang, Jiang, Lin. "Agent Smith: A Single Image Can Jailbreak One Million Multimodal LLM Agents Exponentially Fast". arXiv 13 Feb 2024 (v2 3 Jun 2024), ICML 2024. https://arxiv.org/abs/2402.08567 | NEW [ABS] |
| 4 | Prompt Infection | Lee & Tiwari, 2024. https://arxiv.org/abs/2410.07283 | [REUSED] `track2_networks.md` §2.1 (full text) |
| 5 | "Security vs. collaboration trade-off (AAAI 2025)" | The PDF gives no title. Identified via web search and the arXiv abstract page as **Multi-Agent Security Tax: Trading Off Security and Collaboration Capabilities in Multi-Agent Systems**, Peigne-Lefebvre, Kniejski, Sondej, David, Hoelscher-Obermaier, Schroeder de Witt, Kran. arXiv 26 Feb 2025 (v2 4 Jun 2025). https://arxiv.org/abs/2502.19145 . The description matches (vaccination memories plus safety prompts). The identification is **probable, not confirmed from the PDF**, because the critique doc gives no title. | NEW [ABS] |
| 6 | Secret Collusion among AI Agents | Motwani et al., NeurIPS 2024. https://arxiv.org/abs/2402.07510 | [REUSED] `track4_oversight.md` §3.2 (full text) |
| 7 | Concordia | Google DeepMind. https://github.com/google-deepmind/concordia (`pip install gdm-concordia`) | [REUSED] `track1_sandboxes.md` §2.5 (README plus two source files; not run) |
| 8 | MAST: Why Do Multi-Agent LLM Systems Fail? | Cemri, Pan, Yang, Agrawal, Chopra, Tiwari, Keutzer, Parameswaran, Klein, Ramchandran, Zaharia, Gonzalez, Stoica. arXiv 17 Mar 2025 (v3 26 Oct 2025). The PDF says NeurIPS 2025, which I did not verify. https://arxiv.org/abs/2503.13657 | NEW [ABS] |

Check on the PDF's own claims against the sources:
- GovSim "best agent survived under 54% of the time": matches ("highest survival rate below 54%"; GPT-4o 53.3).
- Agent Smith "up to a million agents": matches the title and abstract.
- Prompt Infection "LLM Tagging plus existing defenses gave strong protection": consistent with our summary, but LLM Tagging alone cut success by only 5%, so "plus" matters.

## Part 2. Per-paper summaries and how each helps

### 2.1 Hammond et al. 2025, Multi-Agent Risks from Advanced AI [REUSED: `general.md`]
- **TL;DR**
  - A taxonomy of 3 failure modes (miscoordination, conflict, collusion) and 7 risk factors (information asymmetries, network effects, selection pressures, destabilising dynamics, commitment problems, emergent agency, multi-agent security).
  - Directions for multi-agent security: secure interaction protocols, monitoring and threat detection, multi-agent adversarial testing.
  - No numbers were seen in the portion read.
- **Helps us:** it gives a vocabulary for the report. Critique 3 (announcing needs) is an "information asymmetry" instance. Critique 5 (verification) is a "secure interaction protocol". The ripple effect is its "network effects". The keys game covers conflict, since burning is a conflict action.
- **On the critique point:** the PDF uses it only as framing. That is fair, and a citation is enough.

### 2.2 GovSim, Piatti et al. [REUSED: `track1_sandboxes.md` §2.6]
- **TL;DR**
  - A fishery/pasture/pollution commons dilemma. Agents discuss, then act each month.
  - "All but the most powerful LLM agents fail ... highest survival rate below 54%".
  - Communication matters, and universalization prompting helps. A greedy newcomer degrades outcomes.
- **Key numbers (temperature 0, 5 seeds, max 12 months):**
  - Survival rate / time: Llama-3-8B 0.0 / 1.0; Mistral-7B 0.0 / 1.0; Qwen-110B 20.0 / 4.5; GPT-4o 53.3 / 9.3.
  - Newcomer: survival 53.3 to 33.3, equality 94.4 to 71.7.
  - Universalization: +4 months survival (p<0.001).
  - No communication: overuse 22% higher (p<0.001).
- **Helps us:**
  - Small open models collapsed at once, which is direct evidence for our biggest risk (ARCH §1.2 risk 1, pilots V1 and V3).
  - Its metrics (survival time, efficiency, equality) match the critique's Gini and efficiency.
  - Its "no communication" ablation could be a cheap condition for us (`messaging: none`).
  - The newcomer perturbation is the template for a compromised insider (critique 6b).
  - Its prompts are reusable and would need citing in PREEXISTING.md. Its code stack (Hydra plus the `pathfinder` submodule) was judged not worth forking.
- **On the critique point:** the PDF calls it the "closest environment". True for the cooperation layer, but it has no adversary and no rivalrous inventory.

### 2.3 Agent Smith, Gu et al., ICML 2024 [ABS]
- **TL;DR**
  - Defines "infectious jailbreak": jailbreak one multimodal agent, and with no further intervention almost all agents become infected and behave harmfully.
  - Simulated up to one million LLaVA-1.5 agents using randomized pairwise chat.
  - An adversarial image placed in the memory of any one randomly chosen agent was enough to trigger it.
  - The authors derive a principle for judging whether a defense can provably restrain the spread, and say a practical defense meeting it is still open.
- **Key numbers:** the only figure in the abstract is "one million" agents. I did not read the full text, so I have no infection-rate curves from it.
- **Helps us:**
  - It is a precedent for "one memory write spreads". That is our CoT Control, an overwrite of stored notes, followed by the ripple.
  - It supports measuring spread under random pairwise contact. Our `messaging: all_to_all/ring/small_world` knob and the exposure graph in `analysis/ripple.py` are the analogue.
- **On the critique point:**
  - The PDF cites it as an attack template for "God". It is multimodal (an image in memory) and used 1M LLaVA agents, so only the memory-injection mechanism carries over.
  - Our "ripple" is strategic and economic, not a jailbreak, so spread may differ. Do not over-claim the analogy.

### 2.4 Prompt Infection, Lee & Tiwari [REUSED: `track2_networks.md` §2.1]
- **TL;DR**
  - A self-replicating injected prompt propagates agent to agent. Global vs local messaging was compared. Society populations of 10 to 50 agents were run.
- **Key numbers (from the reused summary):**
  - Global messaging: self-replicating beat non-replicating by 13.92% (GPT-4o) and 209% (GPT-3.5).
  - Local messaging: success about 20% lower than global.
  - Attack Ignored: GPT-4o 66% (self-replicating), GPT-3.5 9%.
  - Society full-infection time: 10 agents 47% of turns; 20 agents 31.5%; 50 agents about 21%.
  - Defenses: LLM Tagging alone cut success by 5%. Marking + LLM Tagging prevented all attacks.
- **Helps us:**
  - Its metrics (infected agents over time, time to full infection) go straight into `analysis/ripple.py`.
  - It supports the hub-vs-random question: population size and message scope changed spread.
  - Its "Attack Ignored" category suggests logging, per forged message, whether the victim ignored, questioned or complied (already planned in V4).
  - Its tagging defense is the same idea as our B3 signed-messages condition (a "[unverified sender]" tag).
  - Caution: weak models fall for attacks more (GPT-3.5 9% ignored vs GPT-4o 66%), so an 8B model may be very susceptible. That would be good for bite and bad for variance.
- **On the critique point:** critique 5 (verifiability as a variable) is well supported. Tagging helps only when combined with other defenses, so expect partial protection.

### 2.5 Multi-Agent Security Tax, Peigne-Lefebvre et al., AAAI 2025 [ABS; identification probable]
- **TL;DR**
  - An attacker compromises one agent, which corrupts the others ("infectious malicious prompts", spread over multiple hops).
  - Two "vaccination" defenses insert false memories of safely handling malicious input. Two generic safety-instruction prompts were also tested.
  - The defenses reduce the spread and execution of malicious instructions.
  - They also tend to weaken collaboration. The authors conclude there is a security vs collaborative-efficiency trade-off.
- **Key numbers:** the abstract has none. A third-party summary quoted "63%" and "19-34%", which I could not confirm in the abstract, so do not cite them.
- **Helps us:**
  - It gives a natural defense condition for the grid: a vaccination note, planted as a false memory, in agents' note windows. It is the mirror image of our CoT Control (the same memory channel, used defensively).
  - It predicts a cost: any defense that raises suspicion should lower give rates. That makes "welfare under attack AND welfare without attack" the right pair of measurements.
- **On the critique point:** the PDF's claim (reduced infection, different collaboration effects) is accurate. The paper also supports critique 6b (one compromised insider is the main threat model in the multi-agent security literature).

### 2.6 Secret Collusion among AI Agents, Motwani et al. [REUSED: `track4_oversight.md` §3.2]
- **TL;DR**
  - Defines secret collusion (the DecAI setting) with an overseer who either reads the channels only or also sees internal state. The CASE evaluation suite is introduced.
  - Steganographic capability rises with model size. Mitigations (monitoring, paraphrasing) have limits.
- **Key numbers:**
  - Group covertext steganography reconstruction: Llama 2 7B 9%, Mixtral 8x7B 16%, GPT-3.5 18%, GPT-4 26%.
  - Base64: GPT-4 92%, all other models 0%.
  - Authors conclude that current models lack advanced steganography.
- **Helps us:**
  - It argues that Qwen3-8B colluding covertly is unlikely, so we need not build a steganography detector. A plain-text watchtower is a fair default.
  - Its overseer taxonomy matches our visibility levels (channel-only vs internal state).
  - Our defect action is a collusion-adjacent behaviour only if agents form coalitions, which critique 12's LLM-judge labels (coalitions, retaliation) could pick up.
- **On the critique point:** it is filed under "Collusion", and the PDF gives no specific critique point for it. Weak relevance to the build; cite it in related work.

### 2.7 Concordia, Google DeepMind [REUSED: `track1_sandboxes.md` §2.5]
- **TL;DR**
  - A generative social simulation library with a Game Master entity that resolves actions. Apache-2.0, Python 3.12+.
  - The vLLM wrapper creates an in-process model and grabs 90% of GPU memory by default. A remote endpoint would need `BaseGPTModel` with an OpenAI client (untested).
- **Helps us:** it is an architectural precedent. Our rules engine plays the Game Master role and God sits beside it. It is not worth adopting: the learning cost is high and our custom engine already exists in the plan (ARCH §2). This agrees with the track-1 summary's recommendation of a custom harness; ARCH §2 builds one and does not mention Concordia.
- **On the critique point:** the PDF says Concordia is "a natural home for God". Partially valid: the Game Master concept fits God, but it would put the adversary inside the referee, which conflicts with our need for clean labels (ARCH §2.3 `God` protocol, `adversary/powers.py` is pure and separate).

### 2.8 MAST, Cemri et al. [ABS]
- **TL;DR**
  - MAST-Data: over 1,600 annotated traces from 7 multi-agent frameworks.
  - The taxonomy (MAST) was built from 150 traces, with expert agreement kappa 0.88.
  - 14 failure modes in 3 categories: system design issues, inter-agent misalignment, task verification.
  - An LLM-as-a-Judge annotator agrees well with human annotations. The dataset, taxonomy and annotator are released.
- **Key numbers:** as listed above (1,600+ traces, 7 frameworks, 150 traces, kappa 0.88, 14 modes, 3 groups). I did not read per-mode frequencies.
- **Helps us:**
  - It is a taxonomy to label our logs when agents misbehave. Its inter-agent misalignment category (e.g. ignoring other agents' input) maps onto our protocol failures from V1.
  - It is a method precedent for critique 12's "LLM judge labelling strategies": validate the judge against human labels on a small sample.
  - It also supports reporting failures in our own system (invalid actions, hallucinated keys) as findings rather than noise.
- **On the critique point:** the PDF calls it infrastructure. True, but its tasks are coding, math and general agent tasks, not games, so the categories need adapting. I could not check what the released annotator costs or needs to run on Qwen3-8B.

## Part 3. Synthesis: the 12 critiques against ARCHITECTURE.md

Verdicts: V = valid, P = partially valid (already handled in part, or only part is right), N = not valid.

| # | Critique | Verdict | Reason and concrete fix |
|---|---|---|---|
| 1 | Incentive to give may be zero | **V** | D4 makes needs disjoint from holdings and D3 scores only needed-and-held keys, so a held key has no value to its holder: giving is free and withholding has no motive. Fix: add a `held_key_value` knob (default 0.0; test 0.1 per key held at the end, or allow overlap between held and needed). Scarcity is already a knob (`copies_per_need`, WP1 `world.py`, V3). Make "copies per needed id" the reported variable. The tension also comes from time pressure and from the burn, not only from God. Check it in V3 by counting give rate with and without the knob. WP1 and WP0 (config). |
| 2 | Defect creates keys from nothing | **V** | D1 defaults to `defect_gain: mint`. That is the critique's "key printer". The PDF's `steal_from_target` alternative exists as a knob, but the default is the one that is exploitable. Fix: before building, compute by hand the expected value of burn vs trade (a 10-line script over `world.py`), and make the pilot V3 choose between `mint`, `steal_from_target` and `none`. Recommend `steal` or `none` as the default. ARCH §7 V3 already offers `defect_gain: none` as a collapse fix. Move that decision to the front. Owner WP1 and team lead (D1). |
| 3 | Announcing needs is dangerous | **P** | Valid, and the best story in the design. ARCH already measures a "need-disclosure rate" (§5 behaviour profile, §7 V3). It is not stated as a tradeoff, and there is no outcome link (was the discloser helped or burned?). Fix: in `analysis/metrics.py` (WP4) add disclosure-to-outcome joins per agent: disclosed (board or DM, to whom) vs received a give vs got burned within k rounds. Name it as RQ1b in §8.1. No game change needed. |
| 4 | "If wrong" is undefined | **P** | The rule is defined (ARCH §1.1 and D2: the defector names `{target, info_id}`; if the target does not need that id, the defector loses a random unmet need). What is not stated: how the defector learns needs. They are private unless disclosed (D5 hides message contents from the log). Fix: state in §1.1 that defecting requires a guess or a disclosure. Log `guess_correct`, `source_of_knowledge` (disclosed on the board / DM / none) in `Event.detail` for every defect event. WP1 `rules.py`, WP4. |
| 5 | Nothing can be verified | **P** | Already planned only for fraud: B3 and H4 (signed messages, "[unverified sender]" tag). Not planned: verifying inventory claims ("I have key 14"), a reputation board, or an honesty-rate metric. Fix: (a) add the honesty-rate metric (claims about holdings checked against state) to `metrics.py`. (b) Add an optional `ledger_visible` flag showing each agent's public holdings count, not contents, as a second defense. (c) Leave the reputation board for after the pilots. Prompt Infection (§2.4) predicts tagging alone gives partial protection. |
| 6 | God's threat model is mixed, no objective | **V** | God's objective is implicit in ARCH: the scripted God minimises welfare via fork comparison (H1). The tiering is right: fraud (external), CoT control (an "upper bound"), and a missing middle case, a compromised insider. Fix: (a) write God's objective as a sentence in §8.1: reduce mean welfare at end, with defection count and Gini as secondary readouts. (b) Report fraud and CoT control separately (already the plan: B1 vs B2). (c) Add one cheap insider block: one LLM or scripted agent told to push others to burn a named agent, run as B2b. It needs no new code, only a new `ScriptedAgent` policy and prompt (WP1/WP3). Agent Smith (§2.3) and Security Tax (§2.5) both use the single compromised-agent model. |
| 7 | Ripple needs targeting | **V** | ARCH §8.3 does not vary who is attacked. Fix: add a `victim_selector: random | hub` knob in `scripted_god.py` (WP3). Hubs are chosen by degree centrality in the exposure graph of the control fork's rounds 0 to r (WP4 `ripple.py`). Cost is one more cell per block, so apply it to one block (fraud K=3, round 3) at 3 seeds. Also gives the hub-vs-random result the PDF wants for the networks track. |
| 8 | Turn timing confounds | **N (already done)** | D7 already uses simultaneous rounds with a priority order, and immediate replies are an ablation (off by default, ARCH §1.3). Small gap: priority order must be reshuffled each round and logged. Verify that `rng.derive_seed(game_seed, "priority", round)` is recorded in `events.jsonl` or `snapshots.jsonl` (WP1). |
| 9 | 100 rounds won't fit context | **P** | Already handled: bounded observation, notes window of 5 (ARCH §2.3, D6), `max_rounds` 40. The critique's addition is right: memory format is part of the environment spec and an attack surface. D6 already says CoT control only matters while the note is in the window. Fix: state in the report that the memory window is a parameter of the God's effect size, and run one `notes_window` ablation (5 vs 10) if time. |
| 10 | Monoculture and framing | **P** | Monoculture is real: 20 copies of Qwen3-8B share weights and prompt. Persona variation is cheap: random "style" line per agent and a different risk attitude. Mixed models are not planned (ARCH serves only Qwen3-8B). Framing: the labels "defect" and "burn" are loaded. Fix: add `labels: loaded | neutral` to `prompts.py` (WP2) and run V3 under both. Report persona variation as an exploratory condition only. Caveat: GovSim shows universalization wording shifts outcomes by large amounts (+4 months survival), so framing effects can be big. |
| 11 | No baseline | **P** | ARCH has scripted agents (Cooperate/Defect/TitForTat/Random, WP1) and sanity check #3. Missing: efficiency = welfare / offline optimum. The max-flow in `world.py` already computes the optimum. Fix: expose it as `world.optimum` and add `efficiency` to `metrics.py`. Cheap (under an hour). |
| 12 | Cost and variance | **P** | Already planned: pilots (V1 to V6) before the grid, N=20 with max_rounds 40, 60-66 games, bounded observations. The critique's pilot at N=8, 30 rounds is cheaper, but the PDF's hackathon spec says 20+ agents, and ripple needs a large N. Keep V3 at N=10 first, then N=20. Variance: ARCH uses paired forks plus a B' noise replica, which is stronger than the critique's "several seeds". |

Metrics list in the critique: welfare, Gini, speed, honesty rate, defection rate, reciprocity network, God impact, LLM-judge strategies. ARCH has most. **Missing:** Gini, honesty rate, efficiency vs optimum, trust-network clustering and centrality (needed for critique 7), and the LLM strategy judge (optional, and MAST gives a validation recipe).

Experiment grid in the critique: 3 budgets x 2 timings x 2 targetings x 3 defenses = 36 cells before seeds. At 3 seeds that is 108 games, beyond the 60 to 66 in ARCH §8.3 (~8 to 10 games/hour [E]). Do not adopt it whole. Adopt a one-factor-at-a-time extension (hub vs random, one block).

## Part 4. Refinements (prioritized)

### Before the build starts (WP0 and WP1 are locked from Sat 03:00, so these go into config and rules first)
1. **Settle D1 (defect gain) with a hand EV calculation, and default to `steal_from_target` or `none`** (critiques 1 and 2; D1, WP1). If `mint` stays the default, defecting is a free key and the game likely collapses (the V3 "collapse" case). The cost is one config decision plus a 10-line script. Make `held_key_value` (default 0) a config field in WP0 so it does not need a schema change later.
2. **Log the information source for every defect** (`guess_correct`, `knew_from` in `Event.detail`; critiques 3 and 4; WP1 `rules.py`). It is nearly free now and impossible to recover from logs afterwards. It also feeds the disclosure-to-outcome analysis.
3. **Add `victim_selector: random | hub` and `labels: loaded | neutral` as config knobs** (critiques 7 and 10; WP0 config, WP2, WP3). Adding knobs later breaks the "frozen config" rule, so reserve the fields now, implement them later.
4. **State God's objective and the threat tiers in ARCH §8.1** (critique 6): welfare drop primary, defection count and Gini secondary. Tiers: external fraud, insider agent (new), CoT control as an upper bound.
5. **Add `world.optimum` and `efficiency`** (critique 11). The max-flow already exists in `world.py`.

### Can wait until after the pilots (V3 to V5)
6. Insider-agent block B2b (needs V4 to show the model is susceptible at all).
7. Hub-vs-random victim block (needs the DEMO exposure graph to define hubs).
8. Persona variation and neutral-label ablation (run in V3 only if the dynamics look degenerate or suspiciously cooperative).
9. Honesty-rate, Gini, and disclosure-to-outcome metrics in `metrics.py` (they run offline on finished traces, so they can be added any time before the write-up).
10. `ledger_visible` defense and vaccination-note defense (the latter from Security Tax). Both expand the defense axis, which ARCH §8.3 has as one condition (B3).
11. Strategy labelling with an LLM judge, validated on a small human-labelled sample (MAST recipe), only if time remains on Sunday.

### Do not adopt
- The full critique grid (see the arithmetic above).
- Concordia as the engine (see §2.7).
- A reputation board, until at least one defense shows an effect.

## Part 5. Pivot options if the pilots fail

| # | Trigger | Pivot | What carries over |
|---|---|---|---|
| A | **Agents cannot follow the rules.** V1 legal-action rate < 60% after the structured-output step, or V2 < 60% on rule questions after a rewrite (ARCH §7). GovSim's 0% survival for 7B/8B models is a warning that this can happen. | **Protocol-failure study with a mixed population.** Most agents are scripted (Cooperate/Defect/TitForTat/Random); a few are LLM agents. Measure how the LLM agents deviate and use MAST-style categories to label the failures. Report "what an 8B model can't do in a trading game", plus how a scripted-majority swarm resists God. | World generator, rules engine, scripted agents, parser goldens, V1 and V2 data, God and fork machinery (they act on scripted agents too), `analysis/` and `viz/`. |
| B | **Degenerate dynamics.** V3 welfare is outside [0.3, 0.85] under every setting of `copies_per_need`, `defect_gain` and penalty, i.e. always solved in under 5 rounds or always collapsed in round 3. | **Phase-diagram paper.** Make scarcity ratio (critique 1) and defect gain the independent variables and map the cooperation regimes (welfare, efficiency vs optimum, Gini) for LLM vs scripted populations. God becomes a secondary perturbation near the phase boundary, where it should have the most effect. | Everything in `game/`, `analysis/metrics.py`, scripted baselines, `viz/dose.py`. The grid becomes scarcity x defect-gain instead of K x timing. |
| C | **God has no bite.** V4: compliance < 20% and follow-through < 30%, or A-vs-B divergence does not exceed B'-vs-B even after stronger attacks. | **Robustness result plus detection.** Report "an 8B swarm is robust to forged DMs and note overwrites" with the dose-response as evidence, then shift to RQ1 behaviour (critiques 3 and 4: disclosure and burn dynamics) and watchtower detection of forged messages even when they fail. If a compromised insider (critique 6b) works where fraud does not, make that the headline. | `adversary/`, labels, fork noise-floor machinery, `monitors/` (labels exist whether or not the attack succeeds), `analysis/eval.py`. |
| D | **Ripple unmeasurable or monitors at chance.** B' is about equal to A (noise floor too high) or every log-grounded monitor has AUROC < 0.6 on both label kinds (V4/V5). | **Descriptive and exposure-based study.** Drop fork-based ripple. Use contact-based exposure (who talked to the victim) as the primary spread measure, plus the need-disclosure tradeoff (critique 3) and honesty rates (critique 5). Report monitor failure as a negative result, with the judge-weights-equal-agent-weights caveat from ARCH §9. | `analysis/ripple.py` (exposure part), `viz/network.py`, metrics, the 5 monitors and the sanitized-view test (a reusable monitor-evaluation harness is itself a deliverable). |

Ordering: A is checked first (Sat ~06:00), B at V3 (~09:30), C at V4 (~11:00), D at V5 (~12:00). A and B can happen together, and then the project is basically pivot B.

## Verification gaps (nothing here is invented, but be aware)
- Agent Smith, MAST and Security Tax were read from their arXiv abstract pages only. No per-result numbers from their full text are quoted.
- Security Tax identification is probable (the PDF cited only "AAAI 2025", vaccination memories, safety prompts). The "63%" and "19-34%" figures in a third-party summary were NOT confirmed and are not used.
- MAST's venue (NeurIPS 2025) comes from the PDF and was not checked.
- Hammond et al. was only partly read in `general.md` (about 100k of 469k characters).
