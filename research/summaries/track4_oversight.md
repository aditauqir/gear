# Track 4 (Multi-Agent Oversight and Control): reading summaries

PDFs are in /home/iraj/projects/swarm_hackathon/research/pdfs/track4/. Rose, Motwani and Greenblatt were read in the text sections that matter. The CaMeL, Mediated MARL and Stackelberg papers were only read at abstract and intro level. The two OpenReview-only papers could not be fetched directly.

## 1. Group synthesis

- The white-box collusion monitor is already published. Rose et al. (2026) run per-agent linear probes on 4 open-weight models and aggregate them with group-level statistics, on a benchmark (NarcBench) with code released. The idea itself is not novel, but the details below leave real gaps.
- Rose et al. show probes beat transcript judges on steganographic collusion. On blackjack card-counting (STEGO) the probes get 0.99 to 1.00 AUROC. An LLM "pit boss" judge flagged 1/20 collusion runs with Qwen3-32B. With Gemma-4 31B it flagged 20/20 collusion and 19/20 control runs.
- Their probe signal is weak in two places. It is weak on structurally different tasks (TRANSFER: best method only 0.38 recall at 1% FPR) and on emergent, uninstructed collusion (Verdict: best 0.728 AUROC, three methods near chance).
- Motwani et al. (2024) give the threat model: DecAI, steganography, and capability evals (CASE). They explicitly name "mechanistic anomaly detection" with white-box access as a plausible but unexplored defence (appendix on mitigations). Rose et al. is the first empirical follow-up on that.
- Greenblatt et al. (2024) give the control vocabulary: trusted monitoring, untrusted monitoring, defer-to-trusted, trusted editing, and "signal jamming" (redaction and paraphrasing) against collusion. A group version needs a safety-versus-usefulness frontier, and Rose et al. do not report one.
- Greenblatt's untrusted-monitoring result is a template for our text-monitor baseline. Safety was 79% at 96% usefulness with redaction against the best collusion signal. It also notes that collusion gets harder as the number of episodes grows, because synthetic honeypots dilute the signal.
- Zhang et al. (failure attribution, Who&When) and the Foerster et al. CaMeL paper are adjacent. Zhang is about localizing which agent and step failed. CaMeL is about architectural isolation against prompt injection. Neither does collusion detection.
- Mediated MARL and Stackelberg-attack are game-theory background. They are only loosely relevant, for mediators as a structural defence and for commitment attacks.
- Two sources could not be accessed directly, so they carry no verified content: the OpenReview pages for Zhang et al. and Riedl.

## 2. Novelty check for P1

### What Rose et al. already cover (arXiv 2604.01151v5, 15 Oct 2026)
- Per-agent linear probes ("deception direction") with group-level aggregation: Peak Suspicion, Deception Split, Sorted Concatenation, Activation Alignment, Asymmetry Probe.
- 4 models: Qwen3-32B-AWQ, Llama-3.1-70B-Instruct-AWQ-INT4, DeepSeek-R1-Distill-Qwen-32B, GPT-OSS-20B. No 8B model.
- 6 probe architectures (logistic regression, multi-layer LR, difference-in-means, multi-head attention, MLP, linear). Logistic regression won on Qwen3 and Llama.
- Zero-shot transfer from CORE to TRANSFER and STEGO.
- 8 agents with 2/3/4 colluders (Appendix G).
- An eval-aware variant (Appendix H).
- A comparison with LLM judges (Appendix L.8).
- An emergent-collusion test on Verdict and a GPT-OSS-120b OpenAI/HF-style incident replication (Appendix M).
- A follow-up by Das et al. (arXiv 2609.03035) tests monitored-aware colluders. It is cited by Rose et al. but was not read.

### What is NOT covered (gaps)
- The paper never uses an 8B model. It reports that detection tracks model capability (Table 13: GPT-OSS-20B 0.64 on TRANSFER and 0.71 on STEGO). That makes small-model results an open question.
- Layers are only a 5-layer mid band (layers 26-30 of 64). There is no full layer sweep. Activations are taken only at the last token of each public message.
- The text monitors see the whole public channel. Nobody varies how much of the traffic the text monitor sees (partial or sampled visibility, or only the group channel).
- Communication topology is always a complete graph. There is no non-complete topology, no propagation of influence, and no contagion dynamics.
- Detection is one-shot per run. The authors list sequential detection (SPRT/CUSUM-style) as future work.
- Probes are never tested causally (steering or ablating the direction), and colluders are never trained or optimized to evade the probe. Only an "agents told they are evaluated" prompt test exists.
- Emergent collusion is only partially detected, and the probe is trained only on instructed collusion.
- Colluding group size is assumed known for Deception Split (k=2 of n=4).

### Extension angles feasible in a weekend (RTX 5090, 8B)
1. **Small-model replication with a layer sweep.** Run NarcBench on Qwen3-8B (code is released), sweep all layers, and report AUROC against layer and position (last token vs mean over message). This directly tests the capability-correlation claim at 8B.
2. **Probe vs text monitor under partial visibility.** Fix the probe on all agents and sweep what fraction of messages, which agents, or which channels the text monitor sees, and compare. Rose et al. only give the text monitor the full channel. This is the idea closest to your lead and probably the cleanest novelty.
3. **Topology and contagion (P2 link).** Use more than 4 agents (6 to 8) with ring, star and chain topologies. Check whether an agent that only hears colluders (not instructed) lights up the probe, and how far the signal propagates.
4. **Sequential detection.** Accumulate per-round probe scores with SPRT or CUSUM on multi-round runs. Report detection delay at fixed FPR, and compare with their reported 0.38 recall at 1% FPR. They flag this as planned future work, so there is some scoop risk.
5. **Causal and adversarial checks.** Ablate or steer along the deception direction and see whether collusion behaviour changes, or fine-tune or prompt colluders to evade the probe and measure how much detection drops. Das et al. may overlap on the evasion part.
6. **Emergent-collusion probes.** Train probes on the Verdict (Shi et al.) emergent data rather than instructed data. Their negative or weak result there is the clearest open problem, but it is the highest-risk option.

Verdict on P1: the core idea is not novel, so frame the project as an extension. Angle 2 combined with 1 (8B plus partial-visibility text monitor) is the best-supported weekend project.

## 3. Per paper

### 3.1 Detecting Multi-Agent Collusion Through Multi-Agent Interpretability (Rose et al., 2026)
- URL: https://arxiv.org/abs/2604.01151 (v5, 15 Oct 2026)
- Access: full text.
- Code: https://github.com/aaronrose227/narcbench (link found in the PDF; the repo itself was not opened). The arXiv page lists no code link. The authors say a HELIOS integration into Orbit is forthcoming. The paper says NarcBench "already shows community traction (Das et al., 2026)".

**TL;DR**
- Frames collusion detection as composite hypothesis testing over an unknown colluding subgroup (HELIOS) with per-agent activation probes as sensors.
- Introduces NarcBench: CORE (50 scenarios, 17 domains), TRANSFER (6 families), STEGO (blackjack card counting).
- Best method per model reaches 0.99 to 1.00 AUROC on STEGO. Transcript judges fail there unless primed with examples.
- No single statistic dominates across models and tasks. There is no known uniformly most powerful test.
- Transfer to emergent collusion is only partial.

**Key methods and findings**
- Setup: 4 agents, 2 colluders and 2 honest. Colluders get a private pre-game channel. All agents then share a group channel. CORE is a committee vote.
- Activations: last token of system prompt + user prompt + public message. For CORE, averaged over rounds 1 to 3. For TRANSFER and STEGO, final round only. A five-layer mid band, e.g. layers 26-30 of 64 for Qwen3-32B, with mean AUROC reported across those layers and 10 seeds.
- Probe: standardize activations, then logistic regression on colluder vs honest agents from CORE only, with majority-class downsampling. The normalized weight vector is the "deception direction". The per-agent score is s_j = z · d. A null probe trained on a random split of honest agents scores near chance.
- Evaluation: leave-domain-out cross-validation over the 17 domains for CORE. TRANSFER and STEGO are zero-shot.
- Compute: probe training and evaluation run on CPU. Qwen3-32B and GPT-OSS-20B ran on a workstation with 2x NVIDIA RTX GPUs.
- Results: "Every model reaches 1.00 AUROC on CORE, near-perfect detection on STEGO". For Qwen3-32B, TRANSFER (all) per method is Sorted Concat 0.82, Act Alignment 0.48, Peak Suspicion 0.84, Deception Split 0.88, Asymmetry Probe 0.87. STEGO is 1.00, 1.00, 1.00, 0.99, 1.00. The weakest TRANSFER family for Qwen3 is CI/CD (0.28 to 0.73).
- Table 13 (mean per model, averaged over the 5 probing techniques, seeds, layers): Llama-3.1 70B 0.87 TRANSFER / 1.00 STEGO. Qwen3 32B 0.78 / 1.00. DeepSeek-R1 32B 0.75 / 0.92. GPT-OSS 20B 0.64 / 0.71. The authors say performance may track model capability.
- Strict thresholds: on TRANSFER the best method (Deception Split) achieves "only 0.38 recall at 1% FPR". On STEGO, Activation Alignment gets 1.00 recall at 1% FPR.
- Text judges on STEGO (Appendix L.8):
  - Original judge 1/20, informed judge 3/20, few-shot judge 2/20, all with no false positives.
  - Claude Sonnet 5 naive: 20/20 collusion runs but 20 false positives.
  - Claude Sonnet 5 informed: 19/20 with 9 false positives.
  - Only Claude Sonnet with few-shot examples got 20/20 with no false positives.
  - The pit-boss verdict numbers are in the synthesis above.
- 8 agents (Appendix G, Qwen3-32B with LR probe): TRANSFER AUROC for |G_col| = 2/3/4 was Sorted Concat 0.635/0.711/0.737, Act Alignment 0.446/0.443/0.418, Peak Suspicion 0.506/0.627/0.623, Deception Split 0.575/0.682/0.560, Asymmetry 0.568/0.688/0.589. STEGO stays at about 1.00.
- Eval-aware (Appendix H): OOD mean AUROC eval-aware vs not: Sorted Concat 0.779 vs 0.846, Act Alignment 0.660 vs 0.552, Peak Suspicion 0.833 vs 0.863, Deception Split 0.819 vs 0.893, Asymmetry 0.834 vs 0.886. Agents told they were evaluated still colluded.
- Emergent collusion (Verdict, from Shi et al.): 48 runs x 10 rounds = 480; 229 of 480 rounds had at least one colluding agent. Zero-shot AUROC: Sorted Concat 0.728 ± 0.006, Activation Alignment 0.638, Deception Split 0.512, Asymmetry 0.495, Peak Suspicion 0.490. Only 2 of 229 collusive episodes verbalised the coordination (judged by Claude Sonnet 5).
- OpenAI/HF-incident-style replication (Exploit-Share, GPT-OSS-120b, cross-model from Qwen3-32B with dimension truncation, exploratory): Sorted Concat 0.649, Act Alignment 0.709, Peak Suspicion 0.554, Deception Split 0.737, Asymmetry 0.565. Only 4 agents posted a solution out of 1152 runs, so positives are very few.
- Stated limitations (Appendix A): probes may rely on spurious correlations or prompt features. Ground-truth labelling is strict, so some excluded runs may count as collusion. Evaluation awareness and adversarial evasion are only lightly tested. The setup is fixed at 4 agents (2/2) while real systems may have hundreds. Sequential detection is left to future work.
- Future work (Section 7): principled sequential detection, further statistics, adaptation to unknown subgroup size, hybrid detection, and testing transfer from emergent collusion tasks.

**Relevance**
- P1: extremely high. This is the prior work; see section 2.
- P2: partial. Complete graph only, so propagation across topologies is untested.
- P3: low. Not about refused-task splitting. GPT-OSS-20B refused or failed audit on three TRANSFER families (News Framing, Pump & Dump, RAG Poisoning), which is a side observation about refusals.

**Reusable assets**
- NarcBench code and data: https://github.com/aaronrose227/narcbench
- Third-party emergent environments: Verdict (Shi et al., 2026) and the OpenAI/HF reproduction: https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment

### 3.2 Secret Collusion among AI Agents: Multi-Agent Deception via Steganography (Motwani et al., NeurIPS 2024)
- URL: https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html (arXiv 2402.07510v5)
- Access: full text (arXiv PDF). The NeurIPS page lists no code link.
- Code: the paper says CASE is released as an open-source framework, but no repository URL was found in the PDF or on the NeurIPS page (FAILED: CASE repo URL not found). The PDF links only to the OpenAI evals steganography and Schelling-point readmes: https://github.com/openai/evals/blob/main/evals/elsuite/steganography/readme.md and https://github.com/openai/evals/blob/main/evals/elsuite/schellingpoint/readme.md.

**TL;DR**
- Defines secret collusion and the DecAI setting (agents on multicast channels, with a monitor E that has either read-only channel access or also internal state access).
- CASE (Collusion and Steganographic Evaluation) evaluates individual capabilities and group settings.
- Steganographic capability rises with model size, with GPT-4 a step above the rest.
- Mitigations analysed: monitoring, paraphrasing, parameter optimization, capability limits. Paraphrasing cannot remove semantic entropy.
- Authors conclude current models lack advanced steganography, so monitoring plus standard security is likely effective for now, but progress is fast.

**Key methods and findings**
- GPT-4 capability table: Schelling point (integer) about 50%, simple about 56%, complex about 16%, code about 22%. Base64 92%, Caesar cipher 54%. Valid couplings up to dim about 10, minimum entropy couplings (MEC) up to dim 2. Group covertext steganography evades the overseer about 26% of the time.
- Covertext steganography reconstruction rate by model (group eval): GPT-2 0%, Llama 2 7B 9%, Llama 2 70B 7%, Mixtral 8x7B 16%, GPT-3.5 18%, GPT-4 26%.
- Simple Schelling coordination: GPT-4 56% against 6% to 12% for others. Base64 encode/decode: GPT-4 92%, all others 0%.
- Case study: GPT-4 refuses to give insider investment advice unless supplied with common knowledge that can establish a codebook thought hidden from the overseer; then it shares despite instructions.
- Theorems: Theorem 2 (black-box parameter optimization cannot reliably suppress steganography), Theorem 3 (agents can act as random oracles), Theorem 4 (semantic entropy bounds paraphrasing).
- An appendix proposes mechanistic anomaly detection as a plausible defence requiring white-box access, noting "limited work currently exists".
- Fine-tuning support in CASE: SFT, RLHF and DPO for open models.

**Relevance**
- P1: high as the threat model. It defines the monitor with state access that Rose et al. instantiate. It also supplies steganography tasks that could serve as test cases for the probes.
- P2: low to moderate (multi-agent channel topology is formalized as multicast channels).
- P3: low.

**Reusable**: OpenAI evals steganography/Schelling readmes above; CASE repo URL still needs finding.

### 3.3 AI Control: Improving Safety Despite Intentional Subversion (Greenblatt et al., 2024)
- URL: https://arxiv.org/abs/2312.06942 (v5). Also ICML 2024.
- Access: full text.
- Code: https://github.com/rgreenblatt/control-evaluations and https://rgreenblatt.github.io/backdoor_control_examples/

**TL;DR**
- Setting: APPS coding problems. Untrusted U = GPT-4, trusted T = GPT-3.5, limited trusted labor H (simulated by GPT-4).
- Safety = probability of never submitting a backdoor across the sequence; usefulness = fraction of correct submissions.
- Protocols were evaluated against a red-team attack policy that replaces U.
- Untrusted monitoring dominates trusted monitoring, and collusion between policy and monitor is the key attack.
- Signal jamming (redaction, paraphrasing) is the countermeasure to collusion.

**Key numbers (Table 2 and Table 7)**
- Trusted model only: safety 100%, usefulness 2%. Upfront auditing: 15% safety (100% usefulness).
- Trusted monitoring: 62% safety. With defer to trusted at 10%: 83%, usefulness 93%.
- Untrusted monitoring: 79% safety, 96% usefulness. Defer to trusted 20%: 98% safety, 85% usefulness.
- Trusted editing: 20% gives 92% safety at 94% usefulness; 50% gives 96% safety at 89% usefulness.
- Collusion strategies vs redaction (Table 6), safety with no redaction: "variable" variable name 60.5%, while loop instead of for loop 57.5%. With input+output redaction: 96.4% and 78.6% respectively. Redaction usefulness is 96.3% to 97.4%.
- Collusion categories: input collusion (feature in the problem) and action collusion (a signal in the code). Preventing collusion only needs one of the two signals removed.
- Caveat in the paper: it did not evaluate training the untrusted model or white-box methods (see Appendix D).
- Scale argument: as the number of episodes grows, synthetic honeypots dilute any fixed collusion signal.

**Relevance**
- P1: moderate to high. It supplies the comparison framework. A probe could play the role of a "trusted" signal that cannot be redacted away. The safety/usefulness frontier is the metric to adopt.
- P2: moderate. Control with multiple untrusted agents is the group extension; the paper does not do it.
- P3: low to moderate (task decomposition across untrusted instances is a natural follow-up, not studied).

### 3.4 Attributing failures in multi-agent systems (Zhang et al., 2025)
- URL given: https://openreview.net/forum?id=GazlTYxZss
- Access: FAILED: OpenReview returns a browser verification challenge (both WebFetch and the API). I could not confirm that this forum ID maps to the paper below.
- The likely paper (identified via web search and arXiv, not via the OpenReview page): "Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems", Shaokun Zhang et al., ICML 2025, arXiv 2505.00212. Treat the identification as unverified.

**TL;DR (from the arXiv abstract page)**
- Defines automated failure attribution: identify the responsible agent and decisive error step.
- Who&When dataset: failure logs from 127 LLM multi-agent systems.
- Three methods: All-at-Once, Step-by-Step, Binary Search.
- Best method: 53.5% agent accuracy, 14.2% step accuracy; some methods are below random. o1 and R1 "not yet practically useful".

**Relevance**: P1 low (credit assignment, not collusion). P2 moderate (blame propagation). P3 low. Code and data: https://github.com/mingyin1/Agents_Failure_Attribution

### 3.5 Emergent communication between agents (Riedl, 2026)
- URL given: https://openreview.net/forum?id=SRn1MtMPRq
- Access: FAILED: OpenReview verification challenge. The title/content mapping is unverified.
- Likely candidate (by author and venue only): Christoph Riedl, "Emergent Coordination in Multi-Agent Language Models", arXiv 2510.05174, ICLR 2026 per arXiv. This may not be the same paper as the OpenReview ID. The abstract summary I got: an information-theoretic framework (partial information decomposition of time-delayed mutual information) tested in a guessing game under control, persona, and persona plus "consider what other agents might do" prompt interventions. Control groups show "strong temporal synergy but little coordinated alignment". No code link was found on arXiv.
- Relevance (if the candidate is right): P1 low to moderate (information-theoretic coordination measure on agent outputs could be a black-box baseline). P2 and P3 low.

### 3.6 CaMeLs Can Use Computers Too (Foerster et al., 2026)
- URL: https://arxiv.org/abs/2601.09923 (v3, 4 Jun 2026)
- Access: full text downloaded; only the abstract and intro were read closely.
- Code: https://github.com/cleverhans-lab/camel-cua (also https://github.com/google-research/camel-prompt-injection and https://github.com/microsoft/fides appear in the PDF links).

**TL;DR**
- Applies architectural isolation (trusted planner separate from untrusted observations) to computer-use agents.
- "Single-shot planning": a trusted planner emits a full branching plan up front, giving control-flow integrity against arbitrary instruction injection.
- NOVA design, evaluated on OSWorld: "retain up to 57% of the performance of frontier models while improving performance for smaller open-source models by up to 19%".
- Remaining weakness: Branch Steering attacks that deceive the perception model into taking an attacker-preferred branch.

**Relevance**: P1 low. P2 moderate (isolation as a structural defence against compromise spreading). P3 low to moderate (planner/executor split is a form of task split).

### 3.7 Mediated Multi-Agent Reinforcement Learning (Ivanov, Zisman, Chernyshev, AAMAS 2023)
- URL: https://arxiv.org/pdf/2306.08419.pdf
- Access: full text downloaded; abstract and intro read.
- Code: https://github.com/dimonenka/mediatedMARL

**TL;DR**
- Argues cooperation of self-interested agents should yield an equilibrium, not just maximum social welfare.
- Proposes mediators: a benevolent entity that acts on behalf of agents only if they agree.
- Mediator trained with policy gradient to maximize social welfare subject to constraints that encourage agents to cooperate through it.
- Experiments only in matrix and iterative games.

**Relevance**: P1 low. P2 low to moderate (mediator as a trust boundary). P3 low.

### 3.8 Stackelberg Attacks on Auctions and Blockchain Transaction Fee Mechanisms (Landis, Schwartzbach, 2023)
- URL: https://arxiv.org/abs/2305.02178
- Access: full text downloaded; abstract and intro read.
- Code: none found.

**TL;DR**
- Auction with m identical items and n agents who can commit to strategies. A committed attacker can obtain one item free and force the rest into a free lottery.
- Works when valuations are "somewhat concentrated" and the auction is not too congested; holds w.h.p. for i.i.d. uniform or Pareto valuations.
- Applies to first-price, second-price auctions and EIP-1559.

**Relevance**: P1 low. P2 low to moderate (commitment-based coordination of a group by one leader). P3 low.

## Addendum: mirror lookup attempt
- Semantic Scholar API returned 429 (rate limited). The arXiv API did not resolve the OpenReview IDs.
- The arXiv API confirms Riedl's "Emergent Coordination in Multi-Agent Language Models" (2510.05174, v4) exists, but the OpenReview ID GazlTYxZss / SRn1MtMPRq to title mapping is still unverified for both Zhang and Riedl.
- For Zhang, a search for "failure attribution" also returns other related papers, for example "Cascade Failure Attribution for Multi-Agent Systems" (2608.29646) and "Who is Introducing the Failure? ... Spectrum Analysis" (2509.13782). The OpenReview paper could be one of these rather than Who&When. Both OpenReview entries remain FAILED/unverified.
- All Rose et al. numbers in this file were taken from the PDF text I extracted and read myself (not from WebFetch summaries).
