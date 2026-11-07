# Track 2: Science of Agent Networks - reading summaries

Access status (updated): Prompt Infection and Jones et al. verified from the actual arXiv PDFs (text extracted with PyMuPDF; the "2 pages" reported by `file` was a misreport, the PDFs have 14 and 26 pages). Jørgensen: abstract only, and the match to the listed paper is uncertain. Tilli and Agrawal: FAILED.

## 1. Group synthesis

Based on two papers read in full (Prompt Infection; Jones et al. via arXiv mirror), one abstract (Jørgensen et al., uncertain match), and titles only for Tilli and Agrawal.

- Prompt Infection shows an injected prompt can self-replicate agent to agent in a multi-agent system (MAS). Self-replication helps most for scam, malware and content manipulation, less for data theft.
- Information-sharing mode matters: global messaging (shared history) spreads infection better than local messaging (~20% lower success locally).
- Model capability is not simply protective. GPT-4o ignored more attacks than GPT-3.5 but was still infected.
- The only defense evaluated (LLM Tagging, i.e. prefixing "[AGENT NAME]:") is weak alone and works mainly in combination with other defenses.
- Jones et al. show combining a refusing frontier model with a weak non-refusing model via task decomposition produces misuse neither achieves alone (e.g. 43% vs <3% on vulnerable code). This is the main prior work for P3.
- Tilli and Agrawal remain unread (titles only).

### Already done (don't replicate)
- Self-replicating prompt injection in a linear pipeline (document reader -> strategist -> summarizer -> editor -> writer), with global vs local messaging (Lee & Tiwari).
- Infection in a random-pairwise-dialogue "society" of 10-50 GPT-4o agents with memory retrieval (Lee & Tiwari).
- Prompt-level defenses: marking, delimiting, sandwich, instruction defense, LLM Tagging (Lee & Tiwari).
- Two-model task decomposition (weak model + refusing frontier model) for vulnerable code, explicit images, malicious scripts and manipulation (Jones et al.). Code: https://github.com/ejones313/multi-model-misuse
- Shutdown-resistance coordination (Agrawal et al. 2026): not read.

### Open gaps (from Prompt Infection only)
- Topology: only a linear pipeline and a random-pairwise society were tested. Star, ring, hierarchical, small-world and scale-free graphs were not, and no topology-vs-contagion-rate comparison was reported (P2).
- Only GPT-4o and GPT-3.5 Turbo were used, with no open-weight models (the authors say preliminary Claude tests showed similar vulnerabilities but full results were unavailable). This leaves room for white-box access, which is what P1 needs.
- Defenses were text/prompt-level only. No activation probes or white-box monitors were reported (P1).
- No partial-observability monitor evaluation was reported.
- Whether the attack was algorithmically optimized was not tested; the authors themselves flag that generated prompts may bypass the defenses.

## 2. Per paper

### 2.1 Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems
- URL: https://arxiv.org/abs/2410.07283 (Lee & Tiwari, arXiv 9 Oct 2024, cs.MA/AI/CR)
- Access: full text, verified against the arXiv PDF (v1, 14 pages).

**TL;DR**
- Self-replicating malicious prompts propagate across interconnected agents like a virus.
- MAS are highly susceptible even when agents don't share all communications.
- Attack types: content manipulation, malware spread, scams, availability attacks, data theft.
- Defense LLM Tagging helps only in combination with other defenses.

**Methods**
- Attack has four parts: Prompt Hijacking, Payload, Data (a shared note accumulating info), Self-Replication. A stealth variant has the last agent omit replication. The baseline is Non-Replicating Prompt Infection.
- Topologies: (a) linear pipeline with a tool-specific first agent (document reader) followed by strategist, summarizer, editor and writer agents, with global messaging (full histories) vs local messaging (partial histories from predecessors); (b) "society of agents" with random pairwise dialogues, 4 exchanges per turn, populations of 10, 20, 30, 40 and 50, memory retrieval following Park et al. 2023 (top K=3).
- Models: GPT-4o, GPT-3.5 Turbo; GPT-4o for society memory agents; OpenAI embeddings for relevancy.
- Data: 120 user instructions across email, PDF and web tools, giving 360 instruction/attack-phrase pairs; synthetic CSV user data for data theft.
- Metrics: attack success rate; failure categories (Attack Ignored, Mixed Action, Deformed Infection, No Action, Agent Error); number of infected agents over time; memory importance score (1-10).

**Findings (all numbers checked against the PDF; they match the earlier extraction)**
- Global messaging: self-replicating beat non-replicating by 13.92% for GPT-4o and 209% for GPT-3.5 (scam, malware, content manipulation).
- Data theft: non-replicating beat self-replicating by 8.48% on average as agent count grew.
- Local messaging: self-replicating success about 20% lower than global; non-replicating rarely compromised more than two agents.
- Note an internal inconsistency in the paper: RQ2 text says "GPT-3.5 is more capable of resisting prompt infections than GPT-4o" while the failure analysis says GPT-4o ignores more attacks (and is more dangerous once compromised). Treat the Attack Ignored figures as the reliable ones.
- Attack Ignored: GPT-4o 66% (self-rep) / 54% (non-rep); GPT-3.5 9% / 20%.
- Society full-infection time as a share of total turns: 10 agents turn 4.7 (~47%); 20 agents turn 6.3 (~31.5%); 30 ~23.3%; 40 ~24.2%; 50 ~21.4%.
- Importance score averaged over 100 runs: GPT-4o 1.94 without manipulation vs 10.00 with; GPT-3.5 1.00 vs 9.84. Without manipulation the infection died after K=3 turns.
- Defenses: LLM Tagging alone reduced success by only 5%; marking alone still allowed 76%; delimiting and sandwiching allowed nearly all; Marking + LLM Tagging prevented all attacks; Instruction Defense + LLM Tagging gave 3%; Sandwich + LLM Tagging gave 16%.

**Relevance**
- P2: the closest prior work. It supplies the contagion metrics (infected-agents-over-time, time-to-full-infection) and shows population size and messaging mode matter. Gap: no systematic topology sweep.
- P1: provides a text-level attack and defenses to compare against. No white-box monitor exists here.
- P3: not directly relevant (injection, not task decomposition).

**Limitations (from paper)**: GPT family only; basic architectures; handcrafted attacks; attack prompts are often visible, offering detection opportunities. Also: infection spread in the society follows logistic growth; with importance-score manipulation the infection persists, without it it dies out after K=3 turns.

**Reusable code/data**: no code or repository link in the PDF (only third-party links to CrewAI and MetaGPT). The full infection prompt is in Appendix A of the paper.

### 2.2 Adversaries Can Misuse Combinations of Safe Models (Jones, Dragan, Steinhardt)
- URL: https://arxiv.org/abs/2406.14595 (arXiv v2, 1 Jul 2024, cs.CR; UC Berkeley). Marked "Preprint. Under review."
- Match caveat: the lead suggested this arXiv ID. Title and authors are confirmed from the PDF, but I could not open the OpenReview forum GCkhEPE1FG, so I cannot confirm it is the same submission as the "Jones et al., 2025" listed.
- Access: full text (26 pages, arXiv PDF). Downloaded to `/home/iraj/projects/swarm_hackathon/research/pdfs/track2/jones.pdf`.

**TL;DR**
- Individually safe models can be misused in combination, with no jailbreak: a weak, non-refusing model decomposes a task, a frontier model solves benign subtasks, and the weak model uses the solutions in-context.
- Two decomposition methods: manual (human-identified) and automated (weak model proposes related benign tasks).
- Misuse success scales with the quality of both the weak and the strong model.

**Methods**
- Threat model: at each turn the adversary selects a model and prompt and receives the output; it wins if the final output satisfies the malicious condition.
- Frontier models: DALL-E 3 and three Claude 3 variants (Haiku, Sonnet, Opus). Weak models: six open-source models including Llama 2 7B/13B/70B-chat, Mistral 7B and Mixtral 8x7B (Stable Diffusion v1.5 for images).
- Tasks: vulnerable code, explicit images, malicious python scripts, manipulative tweets (simulated manipulation experiment with one or two users).
- Evaluator for code: GPT-4 (gpt-4-0125-preview).
- Metric: task success rate; refusal rates are also reported. No network topology is involved: this is sequential two-model composition.

**Findings (quoted from the PDF)**
- Claude 3 Opus + Llama 2 70B: "success rate of 43% when generating vulnerable code, while neither individual model exceeds 3%".
- Explicit images: Stable Diffusion alone and DALL-E alone below 2% accuracy on one task, but "the combination gets 30% accuracy" (see Table 2 for the other tasks).
- Malicious python scripts: Mixtral 8x7B alone 11%, no other single model reaches 4%, and "combinations of models achieve up to 22%". Claude 3 Sonnet and Opus refuse at least 96% of the time; weak models refuse less than 1%.
- Opus+Haiku 13% vs Haiku+Haiku 10% and Mixtral+Haiku 17% on the script task (Table 3 discussion).
- Manipulation: combining helps in every setting (see Table 6; one reported jump is from 5% improvement to 33% for a pair of users).

**Relevance**
- P3: the key prior art. Our P3 (a refused task split across agents into benign subtasks) must differ from or extend this. Possible differentiators: multi-agent networks with per-agent monitors, role specialization emerging in a swarm, white-box detection (P1) of the decomposition, or measuring how topology affects task-split success. Two-model composition is already done.
- P1: they only measure refusals and success, not monitors. A monitor that sees the combined sub-requests across agents is the open question; verify the paper's own discussion section before claiming this gap.
- P2: not about contagion.

**Reusable code/data**: https://github.com/ejones313/multi-model-misuse (stated in the paper's footnote).

### 2.3 Coordination to resist modification or shutdown (Agrawal et al., 2026)
- URL: https://dl.acm.org/doi/abs/10.65109/HQQZ1937
- Access: FAILED: ACM returned HTTP 403 via WebFetch and a Cloudflare challenge via curl. Searches via the arXiv API (all:/au: queries) and OpenAlex found no match. Semantic Scholar returned HTTP 429 (rate limited), so it is untested.
- Related, not the same paper (title-only arXiv hits, unread): "Incomplete Tasks Induce Shutdown Resistance in Some Frontier LLMs" (arXiv 2509.14260).

### 2.4 From individual cooperation properties to system outcomes (Tilli, 2026)
- URL: https://openreview.net/forum?id=00KtDBoKnO
- Access: FAILED: OpenReview challenge on forum, PDF and API; arXiv and OpenAlex title searches found no match; Semantic Scholar rate-limited (429).
- Possibly related, unverified: "Inter-Agent Influence: Evaluating Persuasion, Deception, and Coercion in Multi-Agent Systems" lists Cecilia Elena Tilli among authors (arXiv). Not confirmed to be this paper or related.

### 2.5 Defining collective agency (Jørgensen et al., 2025)
- URL: https://openreview.net/forum?id=NacA6YRBNX
- Access: FAILED for the OpenReview page. A probable arXiv counterpart was found, abstract only: "Causal Foundations of Collective Agency" (Jørgensen, Weichwald, Hammond), https://arxiv.org/abs/2605.00248, published 2026-04-30, CLeaR 2026. The title differs from the listed one and the year is 2026 rather than 2025, so the match is UNCONFIRMED.
- If it is the same work, the abstract says: they ascribe collective agency to a group when treating its joint actions as rational and goal-directed predicts its behavior, formalized with causal games and causal abstraction. They apply it to a multi-agent incentives puzzle in actor-critic models and to quantifying collective agency of voting mechanisms. No experiments with LLM agents are mentioned in the abstract.
- Relevance: theory for when a swarm counts as a collective agent; may give a metric for P2/P1 but unread beyond the abstract.

## Next steps
- A human with a browser should open the Tilli, Agrawal and OpenReview Jones/Jørgensen links and paste abstracts or PDFs into `/home/iraj/projects/swarm_hackathon/research/pdfs/track2/`, or try Google Scholar / Semantic Scholar / arXiv mirrors by title.
