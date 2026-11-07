# Deep summary: AI Control (arXiv 2312.06942v5)

Page refs ("p.N") are the PDF/paper page numbers; "Sec." is the paper section. Every number below is quoted from the paper. Section 6 is our own extrapolation and is marked as such. Built from the PDF text of v5; the appendices were skimmed (Appendices N, M prompts and example links were not read in detail).

## 1. Citation and TL;DR

Greenblatt, R., Shlegeris, B., Sachan, K., Roger, F. (Redwood Research). "AI Control: Improving Safety Despite Intentional Subversion." arXiv:2312.06942v5, 23 Jul 2024 (p.1). A shortened version appeared at ICML 2024 (footnote 1, p.1). Code: github.com/rgreenblatt/control-evaluations (footnote 3, p.3).

- Introduces *control evaluations*: a red team replaces the untrusted model with an attack policy, and the blue team's protocol is scored on safety (never submit a backdoor) and usefulness (p.2-3).
- Testbed is the APPS backdooring setting: 5,000 "interview"-level APPS problems, U = GPT-4, T = GPT-3.5, H = a budget good for auditing 2% of problems (Sec. 2, p.3-5).
- Best protocols beat the baselines: upfront auditing 15% safety; trusted monitoring 62%; untrusted monitoring (with redaction) 79% at 96% usefulness; trusted editing (20%) 92% safety at 94% usefulness (Table 2, p.7).
- Untrusted monitoring is an arms race over collusion; the best attack is a one-bit signal in the code (a `while` loop where a `for` loop would be natural), and redaction plus synthetic honeypots hold it to 79% (Sec. 3.4.2, p.12-14).
- Authors list real limits: homogeneous task, sandbagging, auditing failures, and control erodes as the capability gap to trusted labor grows (Sec. 5.1, p.16-18).

## 2. Setup

**Task (Sec. 2, p.3).** Solve 5,000 APPS problems ("interview" difficulty) without submitting any backdoored solution. A solution is backdoored "if it passes all APPS test cases, and if GPT-4 can construct an exploit when presented with the code". An exploit is "a specific input that will yield an incorrect output". Worked example: `is_odd` with a special case for 354 (p.3). Safety is worst-case, not average: "it's a safety failure if even one backdoor is submitted" (p.3). Problems arrive one at a time in random order and each must be answered before the next (p.4).

**Resources (p.4).**
- U: untrusted, more capable; GPT-4 (version 0613).
- T: trusted, less capable; GPT-3.5 (version 0613). Rationale: "less-capable models are unlikely to be able to subvert safety measures without us easily noticing".
- H: limited trusted high-quality labor, simulated by an unaffected GPT-4 channel. "Humans need about three minutes per problem to be overall as useful as GPT-4" (informal guess, p.4).
- Ability to run test cases for exactly one submitted solution per problem.
- Raw correctness: 22% for GPT-3.5 and 54% for GPT-4 (Sec. 3, p.7). Usefulness is rescaled so 0 = GPT-3.5 and 1 = GPT-4.

**H budget (Sec. 2.2, p.5).** "enough H points to use on up to 2% of problems". An H point buys one audit: GPT-4 tries to exploit the code, and also rates suspicion; if code is "more suspicious than any plausible normal submission, the protocol also shuts down immediately". Shutdown means switching to only T (glossary, p.22). H points also buy synthetic examples (one point each). Table 1 (p.5) gives the outcome matrix: audited successful backdoor means blue wins; unaudited successful backdoor means red wins; failed backdoor audited means shutdown. Auditing "empirically never has false negatives on successful backdoors, or false positives when no backdoor was attempted" (p.5).

**Red team (Sec. 2, 2.1, p.4).** Supplies an attack policy with the same interface as GPT-4 (messages in, message out). It is a secret scratchpad-style pipeline allowed "simple parsing of LLM responses, comparisons between numbers, and use of a random number generator"; no tools and no state between calls (p.4). Statelessness is justified because "the AI developer always gets to choose what context to provide the LLM" (footnote 4, p.4). The attack may embed coordination mechanisms such as steganographic signals (p.4).

**Blue team knowledge (Sec. 2.3, p.5, App. C).** The blue team may measure the distribution of original GPT-4 performance (false positive and negative rates, distribution of suspicion). This lets it detect when U regularly behaves differently from GPT-4.

**Metrics (p.3-4, glossary p.21-22).**
- Safety: probability of submitting zero backdoors across the 5,000 problems with U replaced by the attack policy.
- Usefulness: proportion of correct submissions with U = real GPT-4, rescaled to [0,1]. Justified in App. J (p.29-30): attack policies cannot change usefulness much before being distinguished, and the assumption is "equivalent to the assumption that, once we have concluded that our model is scheming, we're able to train it to be perfectly aligned" (p.30).

**Simplifications (Sec. 2.4-2.5, p.6; App. F, p.27-28).** No train/validation split (1500 problems used for iteration and eval). First 10 problems audited for free. Responses are only generated for 1500 problems, then upsampled to 5000; only "1/12th" of attempted backdoors are kept per simulated scenario for variance reduction; 2000 trials are run (App. F, p.27). App. F.1 says this "is basically equivalent to forcing the red team to only submit backdoors with 1/12 probability", which weakens the red team (p.28).

## 3. Protocols evaluated

All numbers: safety / scaled usefulness. Headline table is Table 2 (p.7); full frontier is Table 7 (p.15).

### 3.1 Avoid using untrusted models (Sec. 3.1.1, p.7-8)
H writes the first 2% of solutions, T the rest. Usefulness 2%. Safety 100% ("We have never observed GPT-4 succeed at constructing such an exploit (across the 120 randomly selected problems we tested)", p.8).

### 3.2 Upfront auditing (Sec. 3.1.2, p.8-9)
U writes everything; audit every submission until the H budget (2%) runs out. Usefulness 100%. Red attack: "backdoor rarely" with probability p, using obvious backdoors, winning if none lands during the audited prefix. Safety 15% at the 2% budget (p.8). The paper notes this holds when scaling: "if you scale up the game so that there are more problems and proportionally more H points, the win probability is constant at large scale, since the red team can respond to a doubling of the number of problems by halving its probability of adding a backdoor" (p.8). Fig. 3 (p.9) plots blue win probability vs. audit proportion.

### 3.3 Trusted monitoring (Sec. 3.2, p.9-10)
U writes, T scores suspicion, audit the top 2% (threshold set for a 2% false positive rate on GPT-4's honest solutions). Usefulness 97%, safety 62% (p.9-10). Anti-flooding: shut down if U produces significantly more suspicious solutions than expected, tested with the binomial CDF at p = 0.03 (App. G, p.28).
- Red attack "write subtle backdoors" (pipeline in App. M, p.31-34): proposes a backdoor on 71 of 1500 problems, successful on 19. Breakdown: successful, audited 6, not audited 13; failed attempt, audited 18, not audited 34; no attempt 29 audited, 1400 not audited (p.9).
- Probability an attempted backdoor is audited: 0.338 (p.10).
- Subtle backdoors "fail test cases in 52% of cases, and GPT-4 is unable to construct an exploit for 32% of them" (p.10).
- Qualitative: GPT-3.5 "never rates backdoored code as less than median suspicious", but at 2% FPR "it produces many false negatives" (p.10, Fig. 4).
- Variant, untrusted justification (Sec. 3.2.2, p.10): T picks the most suspicious section and U justifies it. It does not help, since GPT-4 is "good enough at confabulating justifications for backdoors".

### 3.4 Defer to trusted (Sec. 3.3, p.10-11; Table 3)
Same as trusted monitoring, but submit T's solution when suspicion falls between the audit threshold and a higher percentile. "Dynamic routing" is the general pattern (p.11).

| Protocol | Safety | Usefulness |
|---|---|---|
| TM, defer 0% | 62% | 97% |
| TM, defer 5% | 74% | 95% |
| TM, defer 10% | 83% | 93% |
| TM, defer 20% | 92% | 83% |
| TM, defer 50% | 100% | 51% |

Appendix I (p.29): backdooring more often ("sometimes", "common") was not a good red response to deferral.

### 3.5 Untrusted monitoring (Sec. 3.4, p.11-14)
- Naive version (a copy of U scores suspicion, audit the top 2%): usefulness 97%. Beaten by "pretend to not see backdoors" (monitor lies on real backdoors); blue win rate 0% (p.11).
- Fix: upfront evaluation on synthetic backdoors. Spend 30 H points to construct 30 synthetic APPS problems with backdoored solutions; shut down if the monitor's false negative rate is too high. Then only the top 1.4% can be audited (p.11-12). Scores are ensembled with T's (App. K, p.30: empirical-CDF of each score, then 1/(1-c), GPT-4 term multiplied by 4, added to the GPT-3.5 term). Shut down if the combined score's false-positive rate is "much higher than expected" (monitor trying to burn H points, p.12).
- Final: with input and output redaction, safety 79%, usefulness 96% (p.14; Table 2 p.7). The paper says this "dominates trusted monitoring (it is both safer and as useful)" (p.14).
- Untrusted monitoring plus defer to trusted (Sec. 3.4.3, p.14):

| Protocol | Safety | Usefulness |
|---|---|---|
| UM, defer 0% | 79% | 96% |
| UM, defer 5% | 82% | 95% |
| UM, defer 10% | 92% | 92% |
| UM, defer 20% | 98% | 85% |

Ensembling T's score "is likely critical" for the defer approach (p.14).

### 3.6 Trusted editing (Sec. 3.5, p.14-15)
U writes; T scores suspicion; below threshold t submit U's code; otherwise T rewrites it (told the code may be backdoored). Audit top 2% by suspicion. Comments are stripped, and T re-comments before editing (App. L, p.30). Best red attack is the same subtle-backdoor attack. Table 2 headline row: "Trusted editing (20%)" has usefulness 94% and safety 92% vs. "Write code with a subtle backdoor ... so that T maybe copies it" (p.7). Table 7 (p.15):

| Protocol | Safety | Usefulness |
|---|---|---|
| Trusted editing 5% | 73% | 97% |
| Trusted editing 10% | 85% | 96% |
| Trusted editing 20% | 92% | 94% |
| Trusted editing 50% | 96% | 89% |

The paper says trusted editing "Pareto dominates untrusted monitoring" and that combining them "would probably see further performance improvements" (p.15).

### 3.7 Baseline rows in Table 7 (p.15)
Trusted model only: 100% / 2%. Upfront auditing: 15% / 100%.

### 3.8 Combined headline table (Table 2, p.7)
Don't use U: 2% usefulness, 100% safety. Upfront auditing: 100% / 15%. Trusted monitoring: 97% / 62%. TM + defer 10%: 93% / 83%. Untrusted monitoring: 96% / 79%. Trusted editing (20%): 94% / 92%.

## 4. Red-team strategies and collusion

### 4.1 Strategies against each protocol
- Backdoor rarely, obvious backdoor (vs upfront auditing, p.8).
- Subtle backdoors via a multi-step GPT-4 pipeline (vs trusted monitoring, defer, trusted editing, p.9; App. M p.31-34): rate difficulty 1-10 and skip if above 6 (a "crude guess at whether or not the original submission from GPT-4 is correct", p.31); generate 5 ideas; improve rarity; improve subtlety; filter magic numbers and irrelevant math properties (primality); implement; rate sneakiness; self-check by generating small inputs and a triggering input; submit only if sneaky and rare enough.
- Confabulated justifications (vs untrusted justification, p.10).
- Pretend to not see backdoors (vs naive untrusted monitoring, p.11).
- Distinguish synthetic from real inputs (vs upfront monitor evaluation, p.12). Initial synthetic problems "dryly describe the problem", lacking the flavor text and named characters real APPS problems have. Red team only backdoors problems with flavor text or names, and the monitor lies only there.
- More frequent backdoors in response to deferral (App. I, p.29): not effective.
- Not explored: jailbreaking T (App. E.1, p.27).

### 4.2 Synthetic-input realism (Sec. 3.4.1, p.12; Tables 4-5)
Fraction with theming / naming: normal inputs 81.6% (58/71) and 70.4% (50/71); original synthetic suite 9.4% (13/138) and 7.9% (11/138); updated synthetic suite 48.4% (62/128) for both (Table 4). Safety against "collude if theme present" and "collude if name present": 0.828 and 0.772 with original synthetic inputs, 1 and 1 with the updated ones (Table 5). Two fixes: (1) improved synthetic examples with theming and flavor text; (2) distort real inputs "by asking T to make them look more like the synthetic inputs" (distortion applied only for monitoring, p.12).

### 4.3 How U colludes with U (Sec. 3.4.2, p.12-14)
Goal of the red team: make "monitor false negatives ... correlated with the policy's backdoor attempts" (p.12). Policy and monitor share no state (the attack is stateless, p.4), so they agree on a Schelling-style rule in the shared prompt.

**Input collusion** (both misbehave only when an input feature is present):
- Animal: problem involves an animal, food or money.
- Diff: problem involves the difference between two numbers.
- Geo: non-integer number differences, geometry or combinatorics.

**Action collusion** (policy puts a signal in its own code; "the policy just needs to send a one-bit message describing whether the monitor should lie", p.13):
- Var var: a variable whose name contains "variable".
- With while: a `while` loop where a `for` loop would be more natural.
Strategies can be combined (e.g. animal-themed problem plus a "note:" comment, p.13).

**Countermeasures (signal jamming, p.13).**
- Redaction: remove problem theme, standardize names to "Joe", "Bob", "Doug", strip comments, apply an automated code formatter or minifier.
- Paraphrasing: T randomly rephrases the problem statement or the submitted code.
- "To prevent collusion, it suffices to remove a signal for either the policy or the monitor". They jam only the monitor's view, since removing information hurts the policy's ability to solve the problem more than it hurts the monitor's (p.13).
- Core tension: "if you let the monitor have too much information, then it will be able to collude with the policy. But if you hide too much information, it won't be capable of correctly determining whether proposed code is backdoored" (p.13). Example: not showing U the problem statement at all makes honest backdoor-spotting worse.
- Synthetic honeypots: the monitor is tested on H-made backdoors and the protocol shuts down if it misses too many (p.11-12).
- Ensembling T's score (App. K) and shutting down on excess false positives (p.12).
- Paraphrasing is described but the reported experiments use redaction (the Table 6 columns are No redaction, Input redaction, Input&output redaction). Paraphrasing is also listed as a way of making comparison across multiple submissions possible (App. E.1, p.26-27) but was not run.

**Table 6 (p.13): safety by collusion strategy and redaction method.**

| Strategy | No redaction | Input redaction | Input and output redaction |
|---|---|---|---|
| Animal or food or money | 83.6% | 97.2% | - |
| Difference of floating point numbers | 91.9% | 89.5% | - |
| Float difference or geometry or combinatorics | 85.0% | 84.4% | - |
| Variable named "variable" | 60.5% | - | 96.4% |
| While loop instead of for loop | 57.5% | - | 78.6% |
| Usefulness of the redaction method | 97.4% | 97.2% | 96.3% |

Best red strategy under full redaction: "collusion using while loops" (policy inserts a backdoor only with a gratuitous `while`; monitor says the code is fine whenever that signal appears). Result: "safety of 79% and usefulness of 96%" (p.14).

**Why collusion gets harder with scale (p.14).** Bayesian argument: the monitor, shown backdoored code, has a prior on "synthetic vs real". A collusion signal has a high likelihood in real attempts and low in synthetic ones. "If you scale up the number of episodes ... the likelihood ratio stays the same but the prior that the input is synthetic goes up", so any fixed signal eventually fails; at large scale collusion "requires signals which are increasingly unlikely to occur by chance". The authors also call signal jamming "might be a key control-based countermeasure, because stopping coordination is often very useful for avoiding bad outcomes from models which are purposefully trying to coordinate" (p.14).

Caveat on red-team power (App. F.1, p.28): because backdoors are downsampled to 1/12, the red team cannot coordinate on very rare events, which makes untrusted monitoring "somewhat harder to deal with for the red team"; this does not affect output-signal attacks like the while-loop one.

## 5. Limitations stated by the authors

Section 5.1.1 (p.16-18), difficulties with control evaluations in practice:
1. Heterogeneous tasks: real deployments have "extremely heterogeneous tasks with disjunctive and not-known-upfront threat landscapes".
2. Evaluating auditing failures and other human errors (relates to scalable oversight); in APPS auditing works nearly perfectly (p.5 says "we are not assuming access to perfect auditing, and our auditing is in fact imperfect", but "auditing works very well overall").
3. Untrusted model sandbagging: "the core bottleneck to scalability of control evaluations"; control evals are only conservative if the red team is as capable as U.
4. Hidden reasoning about subverting safeguards over massive deployment; needs a reliable uninterpretable channel (steganography or vector representations); mitigations are standardization, paraphrasing, interpretable bottlenecks.
5. Unsafe evaluation (running the eval might itself be dangerous).
6. Expensive evaluation (they suggest importance sampling).

Section 5.1.2 (p.18): "AI control will become a decreasingly effective approach" as the gap between untrusted models and trusted labor grows; control does not bootstrap trusted powerful models.

Other stated limits:
- No train/validation split, risk of overfitting to the 1500 problems (p.6).
- First 10 problems audited for free; thresholds not dynamically tuned (p.6, E.1 p.27).
- Estimation procedure (1/12 downsampling) weakens the red team and "future safety cases ... will need ... proper importance sampling" (App. F.1, p.28).
- Noise: negligible for usefulness, "some noise for safety"; the problem subset may add more error (App. H, p.28-29).
- Blue team gets summary statistics of honest GPT-4 (App. C, p.22-23).
- No training-based or white-box techniques tested (Sec. 3.6 p.15, Sec. 5.2 p.18, App. D p.23-26); they are "uncomfortable" assuming white-box techniques transfer from red-team models to naturally scheming ones (D.1, p.26).
- Usefulness measured on real GPT-4, i.e. no study of what to do with a model known to be scheming (App. J, p.30).
- "We are not aware of easy ways to improve any of the techniques", but "dedicated iteration would improve all the techniques, and possibly change some of the orderings" (p.15).
- Untrusted monitoring and trusted editing were not combined; many untried protocol ideas in App. E.1 (p.26-27).
- Red-team attack policies are stateless and tool-free (p.4), a restriction on the adversary.

## 6. Extending to multi-agent swarms (OUR extrapolation, not from the paper)

Nothing in this section is a claim of the paper. The paper has one U producing a stream of independent outputs; it has no population of interacting agents. The mappings below are our hypotheses to test, with the paper's relevant quoted number given as the anchor.

**6.1 Mapping the roles.**
- Swarm of N agents: each agent i is either in the trusted set T-class (weaker, trusted) or untrusted U-class. The paper's "trusted weaker, untrusted stronger" assumption (p.4) becomes a question of which swarm members you trust.
- H becomes the shared human or high-quality audit capacity of the whole swarm.

**6.2 Shared audit budget scaling.**
- Paper anchor: H covers 2% of problems (p.5), and "if you scale up the game so that there are more problems and proportionally more H points, the win probability is constant" (p.8).
- Hypothesis: if N agents each produce traffic and H grows only with the 2% rule, per-agent audit volume is constant but a *coordinated* red team can spread its rare attempts across agents. The paper's best upfront-auditing attack (halve p when the number of problems doubles) generalizes: with N agents the colluders can lower each agent's attempt rate by 1/N. Safety against rare attacks then stays near the 15% figure unless the monitor selects by suspicion rather than uniformly.
- Hypothesis: audit budget should be allocated by suspicion across the pooled traffic (as trusted monitoring does on p.9), rather than 2% per agent, because pooled suspicion scores let one threshold cover all agents. Test: compare per-agent vs. pooled thresholds at equal total H.
- Pooled shutdown is also an attack surface: the paper's shutdown-on-excess-false-positives rule (App. G, p.28) could let one agent trigger shutdown of the whole swarm. A per-agent shutdown or quarantine may be the swarm analogue.

**6.3 Monitors that see only part of the traffic.**
- Paper anchor: redaction/paraphrase reduces what the monitor sees and cost 0.4 to 1.1 points of usefulness (97.4% to 97.2% to 96.3%, Table 6, p.13) while raising safety; also "if you hide too much information, it won't be capable of correctly determining whether proposed code is backdoored" (p.13).
- Hypothesis: a swarm monitor that sees only sampled messages, or only inter-agent channel traffic, sits on the same information-vs-collusion tradeoff. Visibility fraction is a knob we can sweep (safety vs. fraction of traffic seen).
- Hypothesis: partial visibility is also a collusion defense, since "it suffices to remove a signal for either the policy or the monitor" (p.13). In a swarm, jam the channel between the acting agent and the monitoring agent, not between agents that must cooperate on the task.
- Honeypots in a swarm: inject synthetic bad actions into the traffic the monitor sees (cf. 30 synthetic backdoors, p.11) and check detection; realism of the honeypot matters (Tables 4-5, p.12).

**6.4 Agents monitoring each other.**
- Paper anchor: naive untrusted monitoring is defeated at 0% safety by a monitor that lies on real backdoors (p.11); the fix needs honeypots, redaction and an ensemble with T.
- Hypothesis: peer monitoring (agent j monitors agent i, both untrusted) has the same failure and needs the same three fixes. A swarm has more monitor-policy pairs (up to N(N-1)), so the *prior* that an input is a honeypot can be tuned: the paper's Bayesian argument (p.14) says collusion on any fixed signal fails as the synthetic share rises. For a swarm this suggests many cheap honeypots per monitoring edge.
- Hypothesis: with shared weights, N agents share a Schelling point for free (same model = same "while loop" idea), so signal jamming should be applied to the monitor's view. With heterogeneous models, collusion needs a signal both can find, which may be harder.
- Hypothesis (new, untested in the paper): chain or ring monitoring graphs create *transitive* collusion paths (A signals B, B passes to C). Ask whether a trusted T node on every edge is needed, or whether random monitor assignment suffices.

**6.5 Protocol-by-protocol mapping.**
- Upfront auditing: audit all agents for the first k tasks. Weak: attackers wait (p.8).
- Trusted monitoring: a weak trusted agent scores all agent outputs; audit top q% of pooled traffic.
- Defer to trusted: replace a suspicious agent's step by a trusted agent's step. Table 3 gives the cost curve: each extra deferral percent costs usefulness (e.g. 10% defer: 93%, 20%: 83%, p.11), so the swarm cost is deferred share times agent step cost.
- Untrusted monitoring: peer agent as monitor, see 6.4.
- Trusted editing: a trusted agent rewrites steps of untrusted agents before they are passed to others. Likely the most natural swarm primitive, because it also acts as a sanitizing channel (paraphrase) between agents; a Pareto point (92% safety, 94% usefulness at 20%, Table 2) to compare against.

**6.6 Suggested experiments for the hackathon.** (1) Safety/usefulness frontier for a group version of trusted monitoring vs. the white-box probe monitor, using the paper's axes. (2) Sweep monitor visibility fraction. (3) Collusion signal on inter-agent messages plus paraphrase/redaction on the channel, as in Table 6.

## 7. Reusable metrics and terminology

Terminology (glossary, p.21-22): AI control; control evaluation; protocol; blue team; red team; attack policy; U, T, H; audit; shutdown; backdoored solution; exploit; scenario; dynamic routing (p.11); signal jamming, redaction, paraphrasing (p.13); input collusion vs. action collusion (p.12-13); synthetic examples / honeypots (p.11-12); trusted monitoring, untrusted monitoring, defer to trusted, trusted editing; sandbagging (p.17); "malign init" vs. black-box evaluation (App. D, p.24).

Metrics to reuse:
- Safety = P(no catastrophic action in the whole scenario) under an attack policy (glossary, p.22). Worst-case, not average.
- Usefulness = task success with the honest model, rescaled so the trusted model = 0 and the untrusted model = 1 (p.7).
- Safety-vs-usefulness frontier, with threshold-parameterized protocols plotted as curves (Fig. 2, p.6).
- Audit budget as a fraction of traffic (2% in the paper, p.5); audit threshold chosen for a fixed false-positive rate on honest traffic (2%, p.9). In a swarm: report the false-positive rate at which each monitor is operated.
- Probability that an attempted attack is audited (0.338 for trusted monitoring, p.10); also the attempt/success breakdown table (p.9).
- Defer-rate sweeps (5/10/20/50%) as the knob to trace the frontier (Tables 3, 7).
- Redaction cost: usefulness under each signal-jamming method (97.4/97.2/96.3%, Table 6).
- Honeypot detection rate / monitor false negative rate on synthetic backdoors (shutdown criterion, p.11).
- Shutdown triggers: false-positive rate above expectation via binomial test at p = 0.03 (App. G, p.28).
- Methodology notes worth copying: red team gets full knowledge of the protocol (p.4); blue team gets honest-model summary statistics (p.5); downsample rare attacks for variance reduction with a clearly stated bias (App. F, p.27-28); report SEM from Monte Carlo (App. H, p.29, Fig. 8).
