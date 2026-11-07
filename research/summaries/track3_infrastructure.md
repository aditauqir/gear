# Track 3: Agent Infrastructure, group summary

Access notes: arXiv PDFs and the PMLR PDF were curled to `/home/iraj/projects/swarm_hackathon/research/pdfs/track3/` and read as extracted text (WebFetch could not parse PDFs; pypdf was used). Items marked "(our inference)" are the summarizer's analysis, not claims from the papers.

## 1. Group synthesis

- Two layers recur: identity/provenance (who is this agent or text?) and commitment (can an agent bind itself so others can rely on it?). A2A and Chan et al. cover identity; Haupt, Sun, Ramirez and Tennenholtz cover commitment. Watermarking sits between them (provenance of content).
- A2A (Google blog) is a plumbing protocol: Agent Card, Tasks, Artifacts, Messages. The blog gives almost no security detail beyond "parity to OpenAPI's authentication schemes at launch". Trust properties are therefore mostly unspecified, which leaves room for attack-surface work (Agent Card spoofing, task hijacking). The specifics of such attacks are our inference; the blog does not discuss them.
- Chan et al. propose instance-level AI IDs (identifier + attributes) and explicitly list spoofing threats (tampering, ID spoofing, instance spoofing) and a "composite systems" and "decentralized operation" gap. Their mitigation is classic PKI, TLS and C2PA, not anything robust to agents that collude or run decentralised.
- Sun et al. (position paper, no experiments) argue commitment devices are only as credible as their mediator, and that mediators can be bribed or collude with agents. They also say identity verification is "impractical" against Sybil attacks on bots.
- Haupt et al. give the strongest empirical result: formal contracts (binding reward transfers) in Markov games, with proofs that sufficiently rich contracts make all SPE socially optimal, and a training method (MOCA) tested on 5 environments with 2/4/8 agents. This is a ready mechanism for "credible commitments" experiments.
- Ramirez et al. (Game Manipulators) show the dark side: binding contracts let a third party extort fees, and no-regret learners may not converge to the subgame-perfect outcome, so a static game-theoretic prediction can be wrong for learning agents.
- Tennenholtz program equilibrium (abstract inaccessible; secondary source only): mutual source-code inspection supports cooperation. This is relevant to verifiable commitment between LLM agents but is brittle (an extra space breaks CliqueBot-style matching).
- Watermarking (Kirchenbauer et al.) is a detection tool for LLM text with a published statistical test. It is robust to light paraphrase attacks but costs the attacker in quality. Its use as a covert channel or as a collusion detector is not studied in the paper (see per-source section; our inference).

## 2. Per source

---

### A2A: Agent2Agent protocol (Google, 2025)
- URL: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- Access: full text of the blog post (via WebFetch). Spec itself not read.

**TL;DR**
- Open protocol announced April 9, 2025 so agents from different vendors/frameworks can communicate and coordinate. Presented as complementing Anthropic's MCP.
- Built on HTTP, SSE and JSON-RPC.
- Concepts: client agent and remote agent; Agent Card (JSON capability advertisement); Task (lifecycle object); Artifact (task output); Messages with typed Parts.
- Security: "security by default" is a stated principle; the post only says auth/authorization have "parity to OpenAPI's authentication schemes at launch".

**Key details**
- More than 50 technology partners named (Atlassian, Box, Cohere, Intuit, LangChain, MongoDB, PayPal, Salesforce, SAP, ServiceNow, UKG, Workday) plus services partners (Accenture, BCG, Deloitte, KPMG, McKinsey, PwC, TCS, Wipro). Production-ready version planned for later in 2025.
- Supports long-running tasks (quick requests to multi-day research with humans in the loop).

**Relevance**
- P1: A2A messages are text/parts exchanged between agents, so a text monitor can sit at the protocol layer; partial observability can be modelled as the monitor seeing only some Parts or only Agent Cards/Task status (our inference).
- P2: A2A defines the edges along which a compromised agent could pass malicious Messages/Artifacts; the topology is determined by which agents discover each other via Agent Cards (our inference). The post itself says nothing about compromise.
- P3: Task decomposition and delegation across agents is the core use case, which is the mechanism a refused-task split would exploit (our inference).
- Watermarking: not mentioned in the post.

**Reusable code/data**
- Spec and samples: github.com/google/A2A, google.github.io/A2A (links as given in the post; not verified by us).

---

### IDs for AI Systems (Chan et al., 2024)
- URL: https://arxiv.org/abs/2406.12137 (read v3, 28 Oct 2024, via PDF)
- Access: full text.
- Authors include Alan Chan, Noam Kolt, Peter Wills, Usman Anwar, Christian Schroeder de Witt, Nitarshan Rajkumar, Lewis Hammond, David Krueger, Lennart Heim, Markus Anderljung.

**TL;DR**
- Proposes IDs ascribed to instances of AI systems (e.g., a particular chat session). "An AI ID is a container for 1) an identifier and 2) attributes."
- Attribute categories: behaviour, properties, context, relationships to other instances or systems. Relationship links (ancestor/descendant instances) are argued to help investigate misuse such as spawned influence-campaign instances.
- Verifiability needs: received ID equals created ID; claimed author is the real author; ID corresponds to the instance; party trusts author. Threats: tampering, ID spoofing, instance spoofing. Suggested tools: TLS, digital signatures with a trusted third party, C2PA-style binding to outputs.
- Authors "recommend limited experimentation"; IDs seem most warranted where AI systems make financial transactions or contact real humans.

**Key details**
- Footnote: "AI systems could potentially use IDs to establish trust before interacting with each other", analogous to a TLS handshake.
- Composite systems should get new IDs linked to constituents; fine-tuned systems get a different system identifier linked to the original; regenerated outputs create new instances.
- Limitations section: misuse of IDs if verifiability fails (agent masquerading as another's agent); decentralised/self-run agents not covered; IDs can be lent; privacy risks; they note concerns "mirror similar concerns about the reliability of watermarks".
- Table 1 states watermarks "do not contain information about particular AI systems" but that both watermarks and C2PA "could embed IDs".

**Relevance**
- P1: IDs with relationship attributes could provide ground-truth structure for a collusion monitor (which instances share a parent/deployer). Not evaluated in the paper (our inference).
- P2: Instance spoofing / ID lending is the identity-layer analogue of a compromised node impersonating a trusted one (our inference). The paper has no contagion analysis.
- P3: Ancestor/descendant linking is the paper's own answer to one agent spawning many sub-instances, which is the structure of a split task; IDs are weak where the user runs their own composite system (Section 6.1 notes a user-run system C integrating deployer instances A and B "would evade detection by deployers").
- Watermarking: the paper treats watermarks as a possible carrier for IDs on outputs, not as a collusion tool.

**Reusable code/data**: none (conceptual paper). No repository found in the text.

---

### A Watermark for Large Language Models (Kirchenbauer et al., ICML 2023)
- URL: https://proceedings.mlr.press/v202/kirchenbauer23a.html (PMLR vol. 202, pp. 17061-17084; authors Kirchenbauer, Geiping, Wen, Katz, Miers, Goldstein)
- Access: full text (PMLR PDF).

**TL;DR**
- Soft watermark: before each token, hash the previous token to seed a PRNG, split vocab into a green list (fraction gamma) and red list, and add bias delta to green logits. Detection counts green tokens and runs a one-proportion z-test; no model access required.
- Public mode lets third parties run detection; private mode uses a secret key behind an API.
- Quality tradeoff measured by perplexity on OPT-1.3B; low-entropy text is hard to watermark.
- Code: https://www.github.com/jwkirchenbauer/lm-watermarking.

**Key numbers (quoted from the paper)**
- z-score for the soft watermark: z = (|s|_G - gamma*T) / sqrt(T*gamma*(1-gamma)). Threshold z = 4 gives false-positive rate "3 x 10^-5".
- Under 8-beam search with delta = 2, "an average z-score greater than 5 is achieved for as few as 35 tokens."
- Empirical error: "All soft watermarks at delta = 2.0 incur at most 1.6% (8/500) type-II error at z = 4. No type-II errors occurred for the hardest watermarks with delta = 5.0 and gamma = 0.25." Sequences of T = 200 +/- 5 tokens, about 500 each; a maximum of one type-I error per run.
- ROC examples: delta 2.0, gamma 0.5 AUC 0.998 (PPL 6.2); delta 1.0, gamma 0.5 AUC 0.985 (PPL 5.4); delta 10.0 gives AUC 1.000 with PPL 11.6.
- Attack (T5 span replacement, black-box): unattacked AUC 0.998 / PPL 6.3; epsilon 0.1 AUC 0.988 / PPL 13.1; epsilon 0.3 AUC 0.954 / PPL 21.2; epsilon 0.5 AUC 0.838 / PPL 28.4; epsilon 0.7 AUC 0.696 / PPL 33.9. Removal "costs the attacker an average of ~15 points of perplexity" at epsilon 0.3.

**Relevance**
- Covert channel (our inference; not studied in the paper): the green/red partition is keyed by a hash seed, so two colluding agents sharing the key could in principle embed and read a low-bandwidth signal in otherwise normal text. The paper itself notes watermarking is "a special case of steganography". Bits per token would be limited since each token only shifts probabilities and low-entropy spans carry little. Worth a small test if we pick P1.
- Detecting collusion (our inference): a watermark could tag text from a specific model or agent, so a monitor can check provenance. It cannot tell intent. Private-key mode means a colluding pair's own watermark would be invisible to a monitor without the key.
- P1: gives a cheap text-level statistical test to contrast with activation probes; shows partial observability concretely (detection depends on text length and entropy).
- P2/P3: provenance tag could mark which hop altered a message; weak against paraphrase at higher budgets (see attack numbers above).

**Reusable code/data**: https://www.github.com/jwkirchenbauer/lm-watermarking (as stated in the paper).

---

### Cooperative AI via Decentralized Commitment Devices (Sun et al., NeurIPS 2023)
- URL: https://arxiv.org/abs/2311.07815 (v1, 14 Nov 2023)
- Access: full text. Authors: Xinyuan Sun, Davide Crapis, Matt Stephenson, Barnabe Monnot, Thomas Thiery, Jonathan Passerat-Palmbach.

**TL;DR**
- Position paper with no experiments: uses blockchain/MEV (Maximal Extractable Value) examples to argue that commitment devices assumed in cooperative AI have security problems.
- Mediators who see agents' strategies can front/back-run them, extracting value. The paper says some mediators "can simulate other agents an infinite number of times", creating payoff asymmetry.
- Centralised mediators invite collusion, and "relying on identity verification to mitigate this issue is impractical, as agents and bots are more susceptible to Sybil attacks than human agents."
- Two routes to integrity: cryptographic proofs (SNARKs; the paper says current methods support models of MobileNet or GPT2 size "with a 10-20X inference time overhead on CPU") or optimistic monitor-and-penalise. They note a "$20 million loss" incident from payoff asymmetry in commitments.
- Calls for empirical testing frameworks ("crypto-economic commitments sandbox") for multi-agent coordination.

**Key details**
- Agents learning from opponents' parameters (LOLA/COLA) need verifiable proof of those parameters; a mediator could take bribes to misreport.
- Appendix B discusses a Stop Light game with correlated equilibrium, and notes a naive Program Equilibrium in Matching Pennies lets one program exploit the other.

**Relevance**
- P1: motivates monitors that don't rely on self-reports; mediator-collusion is a concrete collusion threat model (our inference on fit).
- P2: Sybil and bribed-mediator argument is a contagion/trust-topology issue in its own right (our inference).
- P3: not addressed.
- Watermarking: not mentioned.

**Reusable code/data**: none (no code or datasets in paper).

---

### Game Manipulators: the Strategic Implications of Binding Contracts (Ramirez, Kolumbus, Nagel, Wolpert, Jost, 2023)
- URL: https://arxiv.org/abs/2311.10586 (v2, 8 Dec 2023)
- Access: full text.

**TL;DR**
- A "game manipulator" (possibly external to the game) makes binding offers: pay a fee or the manipulator distorts the payoff matrix by rewarding/punishing an action. All commitments are binding and common knowledge.
- Analyses a 2x2 asymmetric game across scenarios: one player offers to the co-player (Sec. 5), an external manipulator (Sec. 6), counteroffer (Sec. 7), second manipulator (Sec. 8).
- Learning dynamics: multiplicative weights update (shown with eta = 0.5 for both players) and replicator dynamics.
- Main finding: no-regret agents avoid dominated strategies but may not reach the subgame perfect equilibrium. In Sections 5 and 6 players converge to the Decline equilibrium (T, L) whereas the SPE is the Accept equilibrium (B, R). The paper concludes a manipulator "would actually" do better "refraining from offering a contract" in that case.
- In Sections 7 (Row counter-offers) and 8 (second manipulator), MWUA and replicator dynamics "converge to the subgame perfect equilibrium"; Row's counter-offer neutralises M1's threat, and in Sec. 8 M1 is "forced to pay M2 a fee" to retain its profit.

**Relevance**
- P1: a commitment/extortion threat model for monitors (our inference).
- P2: second-manipulator results show how offers propagate along a chain of agents; thin link to contagion (our inference).
- P3: not addressed.
- Watermarking: not mentioned.

**Reusable code/data**: no repository link found in the text.

---

### Formal Contracts Mitigate Social Dilemmas in MARL (Haupt, Christoffersen, Damani, Hadfield-Menell)
- URL: https://arxiv.org/abs/2208.10469 (read v4, 29 Jan 2024)
- Access: full text.

**TL;DR**
- Augments a Markov game so agents can voluntarily agree to binding reward transfers under pre-specified conditions. Contracts are proposed by agents and any single agent can veto.
- Theory: with a sufficiently rich contract space, all subgame-perfect equilibria of Fully Observable Markov Games are socially optimal; richer contract spaces yield higher welfare in general (even under partial observability); but too rich a space can hurt learning (exploration-exploitation tradeoff).
- Method: Multi-Objective Contract Augmentation Learning (MOCA).
- Prisoner's Dilemma example: a defector fined 1.5 makes (C,C) dominant, payoffs -1 each versus -2 each without the contract.

**Key details**
- Baselines: Joint Training, Separate Training, Gifting, Vanilla Contracting. PPO via ray rllib; 2, 4, 8 agents; static games 1M env steps, dynamic games 10M env steps.
- Environments: Prisoner's Dilemma, Public Goods, Harvest, Cleanup, Emergency Merge.
- Qualitative results: contracting reaches joint optimality in Prisoner's Dilemma for 2, 4, 8 agents; in Cleanup/Harvest vanilla contracting can fail and MOCA "all cases attains at least the level of social welfare as joint training, and often far exceeds it", except 2-agent Harvest and 2-agent Cleanup where the dilemma is weak. In Public Goods with more agents joint training outperforms MOCA. (Exact welfare numbers are in figures only; not extracted.)

**Relevance**
- P1: contracts change incentives, not observations, so a monitor must infer contract-induced coordination; also a source of "legitimate" coordination that a collusion detector must not flag (our inference).
- P2/P3: not addressed directly. The contract layer could be a vector for malicious proposals (our inference).
- Watermarking: not mentioned.

**Reusable code/data**: https://github.com/Algorithmic-Alignment-Lab/contracts (replication code as stated in paper; we have not run it). Environments Harvest and Cleanup are from Hughes et al. (2018).

---

### Program Equilibrium (Tennenholtz, Games and Economic Behavior 49(2), 363-373, 2004)
- URL: https://www.sciencedirect.com/science/article/pii/S0899825604000314
- Access: FAILED: ScienceDirect returned HTTP 403; abstract and full text not accessed. Content below is from secondary sources only (Wikipedia "Program equilibrium" page via WebFetch, and a citation in Sun et al. which cites it as Tennenholtz, M.: Program equilibrium. Games and Economic Behavior 49(2), 363-373 (2004)).

**TL;DR (secondary description, unverified against the paper)**
- Players submit programs that can read each other's source code.
- Core construction: a program that cooperates iff the opponent's program is identical to its own; if both submit it, they cooperate in the Prisoner's Dilemma and this is an equilibrium. Fragile to trivial source differences.
- Folk-theorem-style claim (per Wikipedia): payoff pairs are achievable in a program equilibrium exactly when they are feasible and individually rational.
- Later work mentioned there: FairBot (Lobian proof-based), epsilon-grounded simulation.
- Sun et al. note that a naive program equilibrium in Matching Pennies lets the column program exploit the row program, and that a changed interpretation of a signal can defeat mutual inspection.

**Relevance**
- P1/P3: source-code inspection is not available between LLM agents, so verification would need activation or behavioural evidence (our inference).
- P2: not applicable.
- Watermarking: not mentioned.

**Reusable code/data**: none identified.
