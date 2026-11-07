# General readings: summary

Access note: most sources were read via WebFetch (abs page plus, for 3 of them, a partial read of the arXiv HTML full text through a summarizing model, not verbatim). Numbers below are only those the fetches returned. Where I say "Relevance", that is my inference, not the paper's claim.

## 1. Group synthesis

- **Individual alignment is not enough.** Conitzer & Oesterheld give a Traveler's Dilemma example (agents almost perfectly aligned with humanity, yet the only equilibrium is q1 = q2 = 0). Tomašev et al. make the same point as "collective risks" from groups that each look safe. This supports framing our event as a group-level failure, not a single-model one.
- **Hammond et al. taxonomy** (reuse in the report): 3 failure modes (**miscoordination, conflict, collusion**) and 7 risk factors (**information asymmetries, network effects, selection pressures, destabilising dynamics, commitment problems, emergent agency, multi-agent security**). The Hugging Face event maps most naturally to collusion plus multi-agent security (swarm attacks, cascading security failures).
- **Network effects and security are the directly relevant sections.** Hammond: "minor changes in properties or connection patterns of agents in a network" can cause dramatic group-level change; instances are error propagation, network rewiring, homogeneity/correlated failures. Multi-agent security instances: swarm attacks, heterogeneous attacks, social engineering at scale, vulnerable AI agents, cascading security failures, undetectable threats. Supports P2.
- **Tomašev et al. give a defence-in-depth structure** (4 layers: market design, baseline agent safety, monitoring and oversight, regulatory mechanisms) and name monitoring ideas that fit P1 (interaction-graph analysis, circular-trade/price-fixing detection, attack/failure graphs from logs, sparse autoencoders and CoT monitoring).
- **Chan et al. give an infrastructure vocabulary** that fits a "what could have stopped it" discussion: attribution, interaction shaping, detection and remediation (agent IDs, agent channels, oversight layers, incident reporting, rollbacks).
- **ARIA Scaling Trust** frames multi-agent security as a funded research gap (nearly £50m; Arena, Tooling, Fundamental research tracks). Useful for motivation and for pitching adversarial multi-agent evaluation.
- **Cooperation cuts both ways.** Dafoe et al. and Conitzer & Oesterheld study how to get cooperation; Conitzer & Oesterheld's footnote notes the same questions apply to preventing unwanted cooperation (collusion). Hammond treats collusion as a failure mode.
- **Taxonomy terms to reuse:** collusion, miscoordination, conflict; network effects, error propagation, correlated failures, multi-agent security, swarm attack, cascading security failure; patchwork AGI hypothesis; collective risks; attribution / interaction shaping / detection and remediation; circuit breakers; tacit algorithmic collusion; Sybil attack; "problem of many hands".

---

## 2. Per paper

### Multi-Agent Risks from Advanced AI (Hammond et al., 2025)
- URL: https://arxiv.org/abs/2502.14143
- Access: abstract page plus first 100,000 of 469,565 characters of the HTML full text (the Collusion and Security body text and Appendix B were NOT read). Partial.
- **TL;DR**
  - Cooperative AI Foundation Technical Report #1; 44 authors; submitted 19 Feb 2025.
  - Structured taxonomy based on agent incentives plus contributing risk factors.
  - Each risk is illustrated with real-world examples and experimental evidence; mitigation directions given.
  - Also discusses safety, governance and ethics implications.
- **Key content**
  - Failure modes (3): miscoordination, conflict, collusion.
  - Risk factors (7): information asymmetries, network effects, selection pressures, destabilising dynamics, commitment problems, emergent agency, multi-agent security.
  - Collusion (Sec 2.3): arises where agents should not cooperate (e.g. markets); instances listed: markets (historical example) and steganography (existing literature). Directions: detecting and mitigating AI collusion, impacts on safety protocols. Sec 4.1: "Collusion in Adversarial Safety Schemes".
  - Network effects (Sec 3.2): error propagation, network rewiring, homogeneity and correlated failures. Case study App. B.2 "Transmission Through AI Networks Can Spread Falsities and Bias" (marked as a novel experiment by the authors).
  - Multi-agent security (Sec 3.7): directions are secure interaction protocols, monitoring and threat detection, multi-agent adversarial testing, sociotechnical defences. Case studies: heterogeneous attacks (existing literature); vulnerable AI agents (novel experiment); App. B.3 "Unprompted Adversarial Attacks on Overseer Agents".
  - No numbers seen in the portion read.
- **Relevance**
  - P1: collusion detection and steganography are named directions; "collusion in adversarial safety schemes" is about monitors being colluded with. Good citation for motivation.
  - P2: the strongest source: network effects and cascading security failures; B.2 experiment is a precedent for propagation across networks.
  - P3: "swarm attacks" and "heterogeneous attacks" are the closest named categories (my inference).
- **Reusable code/data:** none confirmed; not seen in the portion read. Check the full text appendix and the Cooperative AI Foundation site.

### Distributional AGI Safety (Tomašev, Franklin, Jacobs, Krier, Osindero, 2025)
- URL: https://arxiv.org/abs/2512.16856
- Access: abstract plus first 100,000 of 152,567 characters of the v2 HTML. Mostly full.
- **TL;DR**
  - Argues for the "patchwork AGI hypothesis": general capability may first emerge from coordinated sub-AGI agents.
  - Proposes managing collective risk, not only aligning individual agents.
  - Core proposal: "virtual agentic sandbox economies" (impermeable or semi-permeable) with market mechanisms, auditability, reputation, oversight.
  - v1 18 Dec 2025, v2 19 May 2026.
- **Key content**
  - 4 defence-in-depth layers with 10, 6, 5 and 6 components: market design (insulation, incentive alignment, transparency, circuit breakers, identity, reputation, smart contracts, roles and access controls, environmental safety, structural controls against runaway intelligence); baseline agent safety (adversarial robustness, interruptibility, containment, alignment, interpretability, defence against malicious prompts); monitoring and oversight (real-time systemic risk monitoring, independent human oversight, proto-AGI signature detection, red teaming, forensic tooling); regulatory mechanisms (liability, standards, insurance, anti-monopoly, international coordination, infrastructure governance).
  - Named threats include tacit algorithmic collusion, coordination failures, indirect prompt injection via "agent traps", best-of-N jailbreaking, capability exfiltration, Sybil attacks, Goodhart's Law, "problem of many hands", and the leakage problem (insulation vs utility).
  - Monitoring ideas: key risk indicators with hidden/dynamic thresholds; interaction-graph analysis for emerging "intelligence cores"; abrupt behavioural shifts; circular trades or price-fixing in transaction networks; task-complexity frontier and rate of novel inter-agent collaborations; attack/failure graphs from interaction logs; sparse autoencoders and chain-of-thought monitoring.
  - Numbers quoted in text: "95% redundant with existing data" (example fee scenario); most models' software-engineering time horizons "below 3 hours".
- **Relevance**
  - P1: lists SAE and CoT monitoring alongside interaction-graph monitoring; supports a comparison of internal vs text/graph monitors. The paper proposes, it does not test.
  - P2: interaction-graph and failure-graph monitoring; "intelligence cores"; Sybil attacks; circuit breakers/insulation as containment (topology interventions).
  - P3: "problem of many hands" and emergent capability from many sub-AGI agents is the conceptual basis for decomposed tasks.
- **Reusable code/data:** none seen.

### ARIA Scaling Trust (programme thesis)
- URL: https://aria.org.uk/opportunity-spaces/trust-everything-everywhere/scaling-trust/
- Access: full page text via WebFetch (summarized by the fetch model).
- **TL;DR**
  - Programme in ARIA's "Trust Everything, Everywhere" opportunity space; backed by "nearly £50m".
  - Aim: agents that can coordinate securely across digital and physical worlds; multi-agent security is a central concern.
  - Three tracks: Arena, Tooling, Fundamental research.
- **Key content**
  - Arena: platform for open competitions testing multi-agent coordination, with a "multi-million pound" prize pool.
  - Tooling: open-source coordination infrastructure. Rolling funding open for Tracks 2 and 3.
  - Fundamental research: move from empirical to theory-driven guarantees; new security primitives.
  - Planned outputs: open-source software, new roots of trust anchored in the physical world, new ways to assess multi-agent cyber-physical systems in adversarial settings.
  - Exploratory projects ran December 2025 to February 2026. Programme Director: Alex Obadia.
- **Relevance:** motivation and funding landscape for all three projects; the "assess multi-agent systems in adversarial settings" output matches the hackathon theme. Not a technical source.
- **Reusable code/data:** none on the page as fetched.

### Open Problems in Cooperative AI (Dafoe, Hughes, Bachrach, Collins, McKee, Leibo, Larson, Graepel, 2020)
- URL: https://arxiv.org/abs/2012.08630
- Access: abstract only.
- **TL;DR**
  - Calls for a research field, "Cooperative AI", on building agents with cooperative capabilities, tools that foster cooperation among machine and human agents, and using AI research to gain insight into cooperation.
  - Draws on multi-agent systems, game theory, social choice, human-machine interaction, alignment, NLP.
  - Calls for unified theory and vocabulary, and links to natural, social and behavioural sciences.
- **Key content:** I did not read the body, so I cannot report its section taxonomy or any numbers.
- **Relevance:** background and citation only; defines the field that Hammond et al. build on.
- **Reusable code/data:** unknown (body not read).

### Infrastructure for AI Agents (Chan, Wei, Huang, Rajkumar, Perrier, Lazar, Hadfield, Anderljung, 2025)
- URL: https://arxiv.org/abs/2501.10114
- Access: abstract plus first 100,000 of 126,138 characters of v3 HTML. Mostly full. Accepted to TMLR.
- **TL;DR**
  - "Agent infrastructure": technical systems and shared protocols external to agents that mediate their interactions (compared to HTTPS for the internet).
  - Three functions: attribution, interaction shaping, detection and remediation.
- **Key content (exact terms)**
  - Attribution: identity binding, certification, agent IDs.
  - Interaction: agent channels (separating agent traffic, e.g. dedicated interfaces or IP blocks), oversight layers (monitoring plus intervention interfaces), inter-agent communication, commitment devices (escrow, assurance contracts, smart contracts, legal contracts).
  - Response: incident reporting, rollbacks.
  - No numbers seen.
- **Relevance**
  - P1: oversight layers and inter-agent communication rules are the places a monitor would sit.
  - P2: agent IDs, channels and rollbacks are the containment levers for a compromised node (my inference).
  - P3: attribution across sub-agents (agent IDs link to "sub-agent activity") bears on tracing who issued each benign-looking subtask.
- **Reusable code/data:** none seen.

### Foundations of Cooperative AI (Conitzer & Oesterheld, AAAI 2023)
- URL: https://ojs.aaai.org/index.php/AAAI/article/view/26791
- Access: the AAAI page returned an access-denied bot-protection notice (FAILED for that URL). Full text obtained instead from the author's PDF at https://www.cs.cmu.edu/~conitzer/FOCALAAAI23.pdf (9 pages, saved to `/home/iraj/projects/swarm_hackathon/research/pdfs/general/conitzer_oesterheld_foundations.pdf`); I read the abstract, intro, and start of the repeated-games section, and checked headings only for the rest. Partial.
- **TL;DR**
  - Research agenda for the game theory of highly advanced AI agents, focused on achieving cooperation.
  - Even if each agent is almost perfectly aligned, the only equilibrium of the game between agents can be terrible (Traveler's Dilemma example, qualities 0 to 7, epsilon = 4, only equilibrium q1 = q2 = 0).
  - Footnote: cooperation is not always desired, e.g. AI pricing algorithms colluding; some safety approaches rely on competition between AIs; the same questions can be asked from the "prevent cooperation" side.
  - Cites the 2010 flash crash (Dow Jones dropped by about 9% in a very short period).
- **Key content:** section headings found include "Cooperation in Repeated Games", "Cooperation between Copies", "Equilibrium Selection". The text mentions program equilibrium and similarity-based cooperation (Oesterheld et al. 2022, arXiv:2211.14468) in references. I did not read those sections.
- **Relevance:** P1/P2 theory background; "cooperation between copies" is relevant if agents are instances of the same model (inference). Mostly a framing citation.
- **Reusable code/data:** none.

---

## 3. Failed or partial

- AAAI OJS page: FAILED (bot-protection page); worked around with the author PDF.
- Hammond et al. Collusion and Security body text, appendices: not read (only first ~100k of 469k characters).
- Dafoe et al.: abstract only.
- Poppler not installed on this machine, so the Read tool could not render PDF pages; I extracted text with PyMuPDF instead.
