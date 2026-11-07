# Track 1 (Sandboxes and Testbeds): reading summaries

Access key: "full text" = read PDF text; "page only" = web page read via WebFetch (a small model summarises the page, so details are second-hand). Anything unverified is labelled. Candidate projects: P1 white-box/activation-probe collusion monitor vs text monitor under partial observability; P2 compromise contagion across network topologies; P3 refused task split across agents into benign subtasks.

## 1. Group synthesis

- **Memory/reflection/planning scaffolds produce emergent social behaviour that spreads through a population.** Generative Agents saw an invitation reach 13 of 25 agents (52%) from a single seed agent, with no user intervention. This is a ready-made information-diffusion substrate for P2.
- **GovSim is a small, quantitative, multi-agent testbed with a hard "collapse" outcome and open weights.** Scenarios: fishery, pasture, pollution. Metrics: survival time, survival rate, gain, efficiency, equality, over-usage. Ablating communication raises over-usage by 22%. A greedy-newcomer perturbation is a built-in "defector injection". These fit P2 and P1.
- **Small open models fail in GovSim.** Llama-3-8B, Mistral-7B and Llama-3-70B all had survival time 1.0 and survival rate 0.0 under the default setup. Only Qwen-110B (20.0%) of the open models was above 0. Qwen3-8B will probably collapse in the default setup unless we lower difficulty or change prompts. This is a finding to plan around, not a bug. (Qwen3-8B was not tested in the paper.)
- **Behavioural game theory (Akata) gives cheap, scriptable probes.** 2x2 repeated games, 10 rounds, simple scripted opponents. LLMs were unforgiving in the Prisoner's Dilemma and failed to coordinate in the Battle of the Sexes with an alternating opponent. Good for fast sanity checks of agent "dispositions" and for ground-truth collusion/defection labels in P1.
- **CRUX is a methodology paper, not an environment.** It does not give a multi-agent sandbox. Its reusable value is the reporting discipline: document interventions, release logs, report cost, monitor in real time, do dry runs. We can cite it to justify small-n, log-heavy evaluation.
- **Concordia is the most general framework** (Game Master plus entity components, Apache-2.0) but heavy, with its own abstractions. It has contributed vLLM and Ollama wrappers. The vLLM one is in-process (not a client for a server), so it does not fit a shared vLLM server directly.
- **All three simulation sources are text-level and observation-rich.** Per-agent memory streams (Generative Agents, GovSim) are logged natively. For P1 (activations) we still need to run our own forward passes with hooks, which none of these frameworks provide.
- **Gandhi et al. could not be read** (see below), so there is no coverage of "stylised games vs simulated social environments" from that source.

### Which framework should we build on?

**Recommendation: a custom ~300-line harness, borrowing GovSim's scenario design (fishery dynamics and metrics, communication-ablation, newcomer perturbation) and prompts.** Reasons:
1. We need white-box access (P1: hidden states per agent turn) and explicit topology control (P2: who talks to whom). Both are easiest if we own the loop and call vLLM's OpenAI-compatible endpoint (and a local HF/nnsight pass for activations).
2. GovSim's inference goes through a `pathfinder` git submodule with conda setup scripts (`setup.sh`, `setup_vllm.sh`) and Hydra configs. Forking means debugging someone else's dependency stack under a 3-day deadline. Its all-to-all discussion phase would also need rewriting for topology work. Fork only if we want exact comparability with the paper's numbers.
3. Concordia would work (the `LanguageModel` interface has just `sample_text` and `sample_choice`), but the learning cost is high and its model wrappers do not target a remote OpenAI-compatible server out of the box. Treat it as optional.
4. The scenarios are simple (monthly resource decision plus a discussion round), so a custom harness is cheap, and it lets us log exactly what we need.

## 2. Per-source summaries

### 2.1 Generative Agents: Interactive Simulacra of Human Behavior (Park et al., UIST 2023)
- URL: https://dl.acm.org/doi/10.1145/3586183.3606763 (read via arXiv https://arxiv.org/abs/2304.03442, PDF v2)
- Access: full text (arXiv PDF). ACM page not fetched.
- **TL;DR**
  - Architecture = memory stream (natural-language experience record) + retrieval + reflection (higher-level synthesis) + planning, on top of ChatGPT.
  - 25 agents populate a Sims-like sandbox town ("Smallville").
  - Evaluated with believability ratings and an ablation, and with a case study on information diffusion and coordination.
  - Authors flag hallucinated embellishments to memory and "erratic behaviors" (e.g. misclassifying locations, hard-to-convey physical norms).
- **Key findings (quoted)**
  - Full architecture believability TrueSkill: "μ = 29.89; σ = 0.72". No reflection: "μ = 26.88; σ = 0.69". No reflection or planning: "μ = 25.64; σ = 0.68". Crowdworker: "μ = 22.95; σ = 0.69". No memory, planning, or reflection: "μ = 21.21; σ = 0.70". Full vs fully ablated "d = 8.16". Kruskal-Wallis "H(4) = 150.29, p < 0.001".
  - Diffusion with no user intervention: knowledge of Sam's mayoral candidacy rose from "one (4%) to eight (32%)"; of Isabella's party "from one (4%) to thirteen (52%)". Network density "from 0.167 to 0.74". "Out of the 453 agent responses regarding their awareness of other agents, 1.3% (n=6) were found to be hallucinated." "five out of the twelve" invited agents showed up to the party (text as extracted; read the surrounding sentence before citing).
  - Footnote: the demo is at https://reverie.herokuapp.com/UIST_Demo/.
- **Relevance**
  - P2: the party-invitation diffusion is a natural analogue for compromise spreading. Measure knowledge/behaviour spread over a social graph. The paper's own network-density metric is reusable.
  - P1: memory-stream logs give a text-monitor baseline. Hallucinated memory is a confound for "collusion" labels.
  - P3: weak direct relevance.
  - Caveat: the full 25-agent, day-long simulation is expensive for Qwen3-8B (many LLM calls per agent per step). We would need a cut-down version.
- **Reusable code/data**: https://github.com/joonspk-research/generative_agents (link from the paper's footnote).

### 2.2 Playing repeated games with large language models (Akata et al., Nature Human Behaviour 2025)
- URL: https://www.nature.com/articles/s41562-025-02172-y
- Access: Nature page FAILED (redirects to an auth/cookie page). Read the arXiv preprint instead (arXiv 2305.16867, 15 pages, full text). The published version may differ from the preprint in numbers and models.
- **TL;DR**
  - LLMs play finitely repeated 2x2 games (10 rounds) against other LLMs, scripted human-like strategies, and human players.
  - Good at self-interested Prisoner's Dilemma-family games, poor at coordination (Battle of the Sexes).
  - GPT-4 is unforgiving in the Prisoner's Dilemma and does not adapt to an alternating opponent in the Battle of the Sexes.
  - "Social chain-of-thought" (predict the opponent's move first, then act) improves coordination.
- **Key findings (quoted)**
  - Models: GPT-4, text-davinci-002, text-davinci-003, Claude 2, Llama 2 70B. "This leads to 1224 games in total: 324 win-win, 63 Prisoner's Dilemma, 171 unfair" (and other families).
  - GPT-4 vs Claude 2: "t(287) = 3.34, p < .001, Cohen's d = 0.20".
  - "GPT-4 never cooperates again when playing with an agent that defects once but then cooperates on every round thereafter."
  - Told the opponent would defect once then cooperate, GPT-4 "defect[ed] throughout all rounds".
  - Battle of the Sexes with an alternating opponent: GPT-4 "always chooses its preferred option resulting in successful coordination rates of only 0.5" across prompt variations.
  - Human study: 195 participants. SCoT raised score in the Battle of the Sexes "β = 0.74, t(193) = 3.49, p < .001"; no difference in the Prisoner's Dilemma "β = 0.10 ... p = 0.64". SCoT slightly raised joint cooperation "β = 0.24 ... p = 0.01".
- **Relevance**
  - P1: cheap ground-truth testbed. Scripted "defect-once" or "alternating" partners give known behaviours to calibrate monitors against. Not itself a collusion setting.
  - P2: low direct relevance. It is 2-player, but pairwise game matrices could seed a networked version.
  - P3: none.
  - Caveat: all evaluated models are older closed or Llama-2 models. Qwen3-8B behaviour is unknown. Run a quick replication.
- **Reusable code/data**: no code/data link was confirmed. I did not find a repository link in the text I grepped. Check the paper's "Code availability" section on Nature before relying on this. Payoff matrices and prompt design are described in the text and are easy to re-implement.

### 2.3 LLM agents in stylised games and simulated social environments (Gandhi et al., 2023)
- URL: https://openreview.net/forum?id=MUtbsFRZwI
- Access: FAILED: OpenReview returned only a browser-verification page. A web search did not identify the paper. I tried arXiv ID 2305.12763 as a guess and it turned out to be a different paper ("The Emergence of Economic Rationality of GPT", Chen et al.), so it was discarded and nothing from it is used. No content is summarised here.
- Mirror retry: arXiv API title/keyword queries returned no results; Semantic Scholar returned HTTP 429 (rate limited) on three attempts. Still FAILED.
- Suggested next step: a teammate with a browser, or the user pasting the abstract.

### 2.4 CRUX: Open-World Evaluations for Measuring Frontier AI Capabilities (Kapoor et al., 2026)
- URL: https://cruxevals.com/ (paper: arXiv 2605.20520)
- Access: full text of the arXiv PDF (19 pages) plus the project landing page.
- **TL;DR**
  - Proposes "open-world evaluations": long-horizon, messy, real-world tasks assessed by small-sample qualitative log analysis, complementing saturating benchmarks.
  - CRUX 1: an agent develops and publishes an iOS app to the App Store. It succeeded with one avoidable manual intervention.
  - The project aims to release new evaluations every 1-2 months. CRUX 2 asks whether agents can conduct open-ended AI research (landing page).
  - Gives methodological recommendations for open-world evals.
- **Key findings (quoted)**
  - "The agent completed the task with only a single avoidable manual intervention"; the agent "forgot where certain credentials were stored".
  - Cost: "Of the $1,000 total cost, 97.5% went to polling for review status, while development itself cost only $25 in tokens."
  - Recommendations include: defining the measurement construct, documenting interventions, releasing logs, real-time monitoring, dry runs, cost reporting.
  - Limitations listed: incomplete recall of log analysis, blurry success criteria, no standardisation.
- **Relevance**
  - P1/P2/P3: no environment to reuse. Useful for framing: we should report all human interventions and release logs, and report cost (Qwen3-8B local cost is low, which is itself a point).
  - P3: the paper notes agents "may encounter policy refusals" and humans can intervene. Relevant background on refusals, but I did not read that passage in detail.
- **Reusable code/data**: no code/data links on the landing page. Pages: https://cruxevals.com/crux/autonomous-ai-ios-development, https://cruxevals.com/crux/can-ai-agents-conduct-research.

### 2.5 Concordia (Google DeepMind)
- URL: https://github.com/google-deepmind/concordia
- Access: page only (README, directory listings, two raw source files via WebFetch). I did not install or run it.
- **TL;DR**
  - "A library for generative social simulation": entities describe intended actions in natural language, a Game Master entity resolves outcomes. Apache-2.0, Python 3.12+, `pip install gdm-concordia`.
  - README: needs "any API that supports sampling text" plus a text embedder for associative memory. README has no code snippet and does not mention OpenAI-compatible endpoints or `base_url`.
  - Tutorial: `examples/tutorial.ipynb`; other examples in `examples/`.
- **Plugging in a local model (assessment)**
  - Core interface `concordia/language_model/language_model.py` (`LanguageModel`). Wrappers I saw: `no_language_model.py`, `call_limit_wrapper.py`, `retry_wrapper.py`, `profiled_language_model.py`.
  - Contrib wrappers live in `concordia/contrib/language_models/`: amazon, google, groq, huggingface, langchain, mistral, ollama, openai, together, vllm.
  - `openai/base_gpt_model.py`: `BaseGPTModel(model_name, client, measurements=None, channel=...)` takes an `OpenAI` or `AzureOpenAI` client as an argument and does not create it. So pointing it at a vLLM server should only need `OpenAI(base_url="http://localhost:8000/v1", api_key="x")`. This is my inference from the constructor and is untested. I did not check whether there is a subclass that hard-codes the client.
  - `vllm/vllm_model.py`: `VLLMLanguageModel(model_name, *, tensor_parallel_size, gpu_memory_utilization=0.9, ...)` creates an in-process `vllm.LLM`. It does not connect to a running server, and by default it grabs 90% of GPU memory, so it conflicts with a separate vLLM server on the same 5090.
  - `ollama/ollama_model.py`: `OllamaLanguageModel(model_name, *, system_message, ...)` uses `ollama.Client()` with the default address. It implements `sample_text` and `sample_choice`.
  - `sample_choice` is the sticking point for small models: Ollama's version forces JSON and retries up to 20 times, and vLLM's scores options by prompt logprobs. With an OpenAI-compatible endpoint you would likely rely on the `BaseGPTModel` implementation, which I did not read.
  - **Minimal path (untested sketch)**: `from openai import OpenAI`; build the client with a local `base_url`; pass it to `BaseGPTModel` (or a subclass); give Concordia an embedder (e.g. a small sentence-transformers function); run the tutorial's simulation with this model. Estimated effort: roughly half a day including embedder and debugging `sample_choice`. This estimate is mine, not measured.
- **Relevance**: P2 and P3 (Game Master mediates actions and can enforce topology or task decomposition). P1: no hooks for activations, but you could run a hooked HF model behind the `LanguageModel` interface.
- **Reusable**: examples directory, entity-component docs (`concordia/command_line_interface/README.md`), tutorial at concordia-tutorial.pages.dev. 1.9k stars at fetch time.

### 2.6 GovSim: Cooperate or Collapse (Piatti et al., NeurIPS 2024)
- URL: https://arxiv.org/abs/2404.16698 (code: https://github.com/giorgiopiatti/GovSim)
- Access: full text (45-page PDF) plus GitHub README.
- **TL;DR**
  - Commons-governance sim: fishery, pasture, pollution. Agents discuss then decide each month. Lake capacity "100 tons of fish"; population doubles.
  - "all but the most powerful LLM agents fail to achieve a sustainable equilibrium ... highest survival rate below 54%".
  - Communication matters; "Universalization" reasoning helps; a greedy newcomer degrades outcomes.
  - Open-sourced simulation, prompts, and web interface.
- **Key findings (quoted)**
  - Setup: temperature zero, "five random seeds" per simulation. Survival time max is 12 months.
  - Table 1 (default; aggregated over scenarios and seeds; survival rate / survival time): Llama-3-8B 0.0 / 1.0; Llama-3-70B 0.0 / 1.0; Mistral-7B 0.0 / 1.0; Mixtral-8x7B 0.0 / 1.1; Qwen-72B 0.0 / 1.8; Qwen-110B 20.0 / 4.5; Claude-3 Opus 46.7 / 6.9; GPT-3.5 0.0 / 1.1; GPT-4 6.7 / 3.9; GPT-4-turbo 40.0 / 6.6; GPT-4o 53.3 / 9.3.
  - "smaller models (such as Llama-3-8B) ... never sustain any of the resources past the first month."
  - Newcomer (GPT-4o): "survival rate drops from 53.3 → 33.3, the survival time drops from 9.3 → 6.6, the gain drops from 66.0 → 34.8 ... equality drops from 94.4 → 71.7 and over-usage increases from 10.8 → 15.7."
  - Universalization: "significantly increases the average survival time by 4 months (t-test; p < 0.001), total gain by 29 units ... efficiency by 24%".
  - No communication: agents "overuse the common resource by 22% (t-test; p < 0.001)".
  - Sub-skill accuracy correlates with survival time (the intro quotes "highly correlated (0.83)"; check which accuracy test that refers to).
- **Code assessment**
  - Open: MIT licence. Run: `python3 -m simulation.main experiment=<id> llm.path=<path>`, e.g. `experiment=fish_baseline_concurrent`. Hydra configs in `simulation/conf/`. Experiments include `*_baseline_concurrent_universalization`, `*_perturbation_no_language`, `fish_perturbation_outsider`. Multi-LLM mixing is supported via `multiple_llm.yaml` and `mix_llm`, so a "compromised agent on a different model/prompt" setup exists out of the box.
  - Local models: README lists open-weights Mistral, Mixtral, Llama-2/3, Qwen-1.5 via HF `transformers` or `vllm`, through the `pathfinder` submodule. **Qwen3-8B is not listed**, and I could not verify that pathfinder supports an OpenAI-compatible server endpoint. Clone with `--recurse-submodules`, both setup scripts need conda.
  - Fork feasibility: possible, but I would expect to patch pathfinder or add a thin OpenAI-compatible backend. I did not inspect the source code, so this is an assessment from the README only.
- **Relevance**
  - P2: best fit of all sources. Newcomer perturbation = injected defector; add topology to the discussion phase and measure how defection spreads (over-usage, survival).
  - P1: communication is explicit text, so a text monitor has a clear baseline; "collusion" can be defined as coordinated over-extraction.
  - P3: weak. Could frame a harmful goal split into per-agent harvest decisions, but it is not natural.
- **Reusable**: https://github.com/giorgiopiatti/GovSim (scenarios, prompts, metrics, web interface).
