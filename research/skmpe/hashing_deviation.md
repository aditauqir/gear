# Hashing + deviation-from-median for agent oversight (research notes)

Method: web search only; nothing installed or run. "[seen]" = URL appeared in search results this session (page body mostly NOT read in full; summaries came from search snippets and 2 abstract fetches). "[fetched]" = abstract page fetched. "[unverified]" = from my background knowledge, no URL checked. Treat 2026 arXiv IDs as seen-in-search only.

## TL;DR
- "English to assembly hashing" is not an established term. Nearest literature: NL<->assembly retrieval/embedding (CLAP, ViC), not hashing. Treat it as a project-specific idea: embed English, embed low-level trace, compare in a shared or aligned space.
- Fuzzy hashes (ssdeep, TLSH, sdhash) are byte-level and designed for files/binaries; for short command/syscall traces, MinHash/SimHash over n-gram shingles is more appropriate and has better libraries.
- The "say vs do" idea has real precedent: AgentSight (eBPF; correlates LLM intent with kernel events) and TraceAegis (tool-call trace consistency). Neither does population-median comparison.
- CoT monitoring (Baker et al. 2025) shows reading CoT beats action-only monitoring, but optimizing against the monitor induces obfuscation. So use it as a measurement, not a training signal.
- Population-median deviation is cheap and standard: per-turn embeddings + medoid/robust-z (MAD) + Isolation Forest, and DTW/edit distance to a medoid trajectory. OnTrack and Trajectory Guard are the closest agent-monitoring prior art.
- Recommended 36h build: log tool calls + strace/eBPF syscalls in a sandbox; embed English turns with a small sentence-embedding model; shingle+MinHash the syscall/command sequence; score = say-do mismatch + distance from swarm medoid (MAD z-score); validate with injected misbehaving agents.
- Biggest pitfall: Qwen3-8B trajectories vary a lot run-to-run, so "median" must be computed per task/environment cohort, not globally; and syscall traces are dominated by noise (libc, loader) that must be filtered.

## 1. Fuzzy / similarity hashing for code, binaries, traces

| Method | Good at | Weak at | Tooling |
|---|---|---|---|
| ssdeep (CTPH) | Quick file similarity; edit-distance on digests | Short inputs; small edits can break it; easy to evade | `pip install ssdeep` needs native lib (`BUILD_LIB=1` to bundle); pure-Python `ppdeep` [seen] https://python-ssdeep.readthedocs.io/ , https://pypi.org/project/ppdeep/20250622/ |
| TLSH | Locality-sensitive digest with a real distance metric (diff score), good for malware/spam clustering; TLSH authors claim logarithmic search because of the metric property (vendor claim) | Needs min input length (~50 bytes; [unverified]); byte-level, not semantic | `pip install py-tlsh` (replaces python-tlsh); `tlsh.hash(data)`, `tlsh.diff(h1,h2)` [seen] https://pypi.org/project/py-tlsh/ , https://github.com/trendmicro/tlsh ; paper https://documents.trendmicro.com/assets/wp/wp-locality-sensitive-hash.pdf |
| sdhash | Feature-selection + Bloom filter digests, 0-100 score; strong in forensic comparisons (Roussev) | Slower, large digests; community ports only | [seen] https://github.com/sdhash/sdhash , Go port https://github.com/eciavatta/sdhash ; Roussev eval https://dfrws.org/presentation/an-evaluation-of-forensic-similarity-hashes/ |
| SimHash (Charikar 2002) | Bit fingerprint where Hamming distance approximates cosine similarity; near-dup detection; works on any weighted feature set including embeddings (random-hyperplane LSH) | Coarse; weight choices matter | Paper [seen] https://www.cs.princeton.edu/courses/archive/spr04/cos598B/bib/CharikarEstim.pdf ; Python lib not verified in search (implementing random-projection sign hashing in numpy is ~5 lines) |
| MinHash / LSH | Jaccard similarity over sets of shingles; ideal for n-gram sets of commands/syscalls/opcodes; scalable lookup | Ignores order beyond shingle size | `pip install datasketch` [seen] https://github.com/ekzhu/datasketch/ |
| Basic-block / CFG hashing | Cross-build matching of functions; BinDiff matches by normalized flow-graph signature (blocks, edges, calls) then block matching; Hashashin = LSH over basic blocks + Weisfeiler-Lehman graph hash (original) | Needs a disassembler/lifter; heavy for our time budget | BinDiff https://github.com/google/bindiff and manual https://www.zynamics.com/bindiff/manual ; Hashashin https://riverloopsecurity.com/projects/hashashin/ , https://riverloopsecurity.com/blog/2019/11/binary-hashing-intro/ (needs Binary Ninja) [seen] |
| Kam1n0 | Indexed assembly clone search at scale (Asm-Clone, Sym1n0, Asm2Vec modes) | Java server, heavy | https://gitee.com/dashengwong/Kam1n0-Community (mirror); upstream McGill-DMaS/Kam1n0-Community [seen via snippet, URL not verified] |
| asm2vec | PV-DM-style function embedding from assembly | Original code not located; noise from compiler opts | Unofficial impl https://github.com/lancern/asm2vec [seen] |
| SAFE | Self-attentive function embeddings, works on stripped binaries, multi-arch; cosine similarity | Needs radare2 + pretrained model | https://github.com/gadiluna/SAFE [seen] |
| Other binary embeddings | Survey-ish evaluation of pre-trained embeddings | n/a | https://arxiv.org/pdf/2502.08682 ; UniASM https://arxiv.org/html/2211.01144v4 [seen] |

Relevance note: for this project the "low-level" artefact is mostly a *sequence of syscalls / commands / basic-block IDs from a sandboxed run*, not a binary. Binary-similarity tools (BinDiff, SAFE, asm2vec) fingerprint *code that could run*; trace fingerprints (MinHash on k-shingles, TLSH over a serialized trace string) fingerprint *what did run*. Only use the former if the agent compiles/drops binaries and you want to identify them.

## 2. Semantic hashing / embeddings of reasoning and turns, CoT monitoring

- Embedding + LSH recipe: encode each turn with a sentence-embedding model, then SimHash via random hyperplanes (sign of projection) for a compact fingerprint, or use FAISS/annoy for nearest-neighbour. Standard technique; Charikar link above covers the theory. Specific library choices are [unverified] (sentence-transformers, faiss-cpu).
- Trajectory Guard (arXiv 2601.00516, Advani, Jan 2026): Siamese recurrent autoencoder over step embeddings (fine-tuned all-MiniLM-L6-v2); notes that averaging step embeddings hides anomalous steps; says standard unsupervised methods on pre-trained embeddings reach F1 <= 0.69 [seen] https://arxiv.org/html/2601.00516 . Lesson: keep per-step embeddings, don't average.
- Baker et al. 2025, "Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation", arXiv 2503.11926 [seen] https://arxiv.org/abs/2503.11926 . Findings (abstract-level): CoT monitoring (even a weaker GPT-4o monitoring o3-mini) is far more effective than monitoring actions/outputs alone for reward hacking in agentic coding; training against the monitor leads to obfuscated reward hacking. The specific recall numbers (~95% vs ~60%) came from a secondary summary, not verified.
- Korbak et al. 2025, "Chain of Thought Monitorability: A New and Fragile Opportunity for AI Safety", arXiv 2507.11473 (position paper) [seen] https://arxiv.org/abs/2507.11473 .
- Faithfulness: Turpin et al., "Language Models Don't Always Say What They Think", arXiv 2305.04388 [seen] https://arxiv.org/abs/2305.04388 ; Anthropic "Measuring Faithfulness in Chain-of-Thought Reasoning" (Lanham et al.; arXiv ID not verified) discussed at https://www.alignmentforum.org/posts/BKvJNzALpxS3LafEs . Implication: English reasoning may not reflect the real cause of an action, which is exactly why a low-level trace channel is a useful second witness.
- Pitfall: Qwen3-8B "thinking" traces are long and repetitive; fingerprint per turn / per tool-call-intent sentence, not per whole trace.

## 3. Linking English intent to executed actions ("say vs do")

- "English to assembly hashing": no paper found under this phrase. Closest, all embedding/retrieval rather than hashing:
  - CLAP, arXiv 2402.16928: contrastive binary code <-> natural-language explanation embeddings [seen] https://arxiv.org/pdf/2402.16928
  - ViC "Virtual Compiler Is All You Need For Assembly Code Search", arXiv 2408.06385 (ACL 2024): NL query -> assembly function retrieval; code https://github.com/zeyugao/VirtualCompiler [seen]
  - Redmond et al., arXiv 1812.09652 (cross-architecture instruction embeddings) [seen]
  Interpretation for us: the practical analogue is to bring both sides into one comparable space (e.g. have an LLM *summarize the executed trace back into English*, then compare to the agent's stated intent), rather than hashing English into assembly directly. This is my suggestion, not an established method.
- AgentSight, arXiv 2508.02736 (Zheng et al.): eBPF "boundary tracing" intercepts TLS LLM traffic (intent) and kernel events (effects), correlates them in real time, and uses a secondary observer LLM; reports <3% overhead; detects prompt injection, reasoning loops, multi-agent bottlenecks. Code https://github.com/agent-sight/agentsight (URL from search summary) [seen] https://arxiv.org/abs/2508.02736 . Closest existing "say vs do" system.
- TraceAegis, arXiv 2510.11203: tool-invocation provenance trace; structural check + semantic consistency check at gateway level (not syscalls) [seen] https://arxiv.org/pdf/2510.11203
- FALAT, arXiv 2606.00765: failure attribution; its abstract does not clearly claim a reasoning-vs-action consistency check [fetched] https://arxiv.org/abs/2606.00765 . Don't cite it as a say-do detector.
- Syscall-level agent monitoring is mostly practitioner material (Sysdig blog, eBPF tracers, ZeroClaw syscall-anomaly doc: baseline-profile unknown syscalls, denied-spike and flood windows) [seen] https://sysdig.com/blog/ai-coding-agents-are-running-on-your-machines-do-you-know-what-theyre-doing . I found no academic paper fingerprinting agent syscall sequences; this looks like a gap (not proven).

## 4. Deviation from the median

Principles (standard methods; library docs not all fetched):
- Medoid trajectory: choose the trajectory minimizing summed distance to others (robust to outliers, unlike a mean). Distances: normalized Levenshtein on action-token sequences; DTW on sequences of step embeddings; Jaccard on shingle sets (MinHash). tslearn supports DTW k-means with DBA barycenters [seen] https://tslearn.readthedocs.io/en/stable/gen_modules/clustering/tslearn.clustering.TimeSeriesKMeans.html ; it has no k-medoids per the search, so compute the medoid yourself from a pairwise distance matrix (N is small).
- MAD threshold: score_i = d(traj_i, medoid); robust z = 0.6745*(score_i - median)/MAD; flag |z| > ~3.5 (Iglewicz-Hoaglin rule of thumb, [unverified]).
- Isolation Forest (scikit-learn `IsolationForest`) / PyOD (ECOD, etc.) on fixed-length features (embedding PCA components, syscall n-gram counts, say-do mismatch score) [unverified on docs; widely used].
- Cohorting: compute medians per task/prompt, otherwise task differences swamp behavior differences.
Agent-monitoring prior art:
- OnTrack, arXiv 2610.12375 (Barazandeh et al.): streaming monitor, compares each step against recorded successful runs via structure-aware optimal transport; on SWE-bench (first 8 steps) +0.057 AUROC over content-similarity baselines; abort policy saved ~18% compute (5/6 correct aborts). No code link found [fetched] https://arxiv.org/abs/2610.12375
- Trajectory Guard (above): supervised-ish, needs training data.
- Detecting Silent Failures in Multi-Agentic AI Trajectories, arXiv 2511.04032: trajectory-level anomaly detection (XGBoost, SVDD; datasets of 4,275 and 894 trajectories) [seen] https://arxiv.org/abs/2511.04032v1
- SentinelAgent, arXiv 2505.24201: execution-graph anomaly detection at node/edge/path levels with an oversight agent [seen] https://arxiv.org/html/2505.24201v1
- MAStitch (AAMAS 2026): per-agent local vs global analyzer [seen] https://ifaamas.org/Proceedings/aamas2026/pdfs/BMJZ4532.pdf (only snippet read)
- I did not find a tool that scores each agent against the swarm *median* explicitly; the population-median framing appears to be open.

## 5. Recommended ~36h pipeline (1x RTX 5090, Qwen3-8B agents)

Model: Qwen3-8B (Apache 2.0; arXiv 2505.09388) [seen] https://arxiv.org/abs/2505.09388 . Serve with vLLM (teammate infra-vllm); 8B fits easily, leaving VRAM for several concurrent agents and a small embedder.

1. Harness (hours 0-8): run N agents (e.g. 20-50) x K tasks inside throwaway containers/VMs. Log per turn: assistant text (reasoning + stated intent), tool call JSON, tool result. Capture low level: `strace -f -ttt -e trace=process,file,network` on the command (simplest), or bpftrace/eBPF if root in a real VM; AgentSight is a reference design. Do all of this inside the sandbox only.
2. Canonicalize (8-12): syscall trace -> drop loader/libc noise, normalize paths/PIDs/fds/IPs (`/tmp/xyz123` -> `/tmp/*`), keep (syscall, path-class) tokens. Commands -> `argv[0]` + flag skeleton.
3. Fingerprint (12-20):
   - English: per-turn embedding (`sentence-transformers`, e.g. all-MiniLM-L6-v2 as used in Trajectory Guard; or a small BGE/E5 model [unverified choice]); optional SimHash 64-bit via random hyperplanes for cheap dedupe/index.
   - Low level: k-shingles (k=3-5) of canonical tokens -> `datasketch` MinHash (128 perms); also TLSH (`py-tlsh`) of the serialized trace for a second, independent metric (only if trace >= min length).
4. Say-do check (16-26): (a) LLM-judge: give a judge (Qwen3-8B itself or a separate model) the stated intent and an English rendering of the executed trace for that turn; output consistent/inconsistent + reason. (b) Embedding check: embed the English rendering of the executed action and cosine-compare to the stated-intent embedding. Calibrate on seeded cases (agent told to do X but a scripted wrapper does Y). Baker et al. suggest CoT-aware monitors beat action-only ones, so keep both views.
5. Deviation scoring (24-32): per task cohort, pairwise distance matrix over trajectories (normalized edit distance on tool-name sequences; DTW over step embeddings via `tslearn` or `dtaidistance` [unverified]; 1-Jaccard from MinHash). Medoid = argmin row sum. Score = distance to medoid, robust z via MAD; also per-turn z against the cohort's turn-embedding median at the same step index. Add IsolationForest (`scikit-learn`) on [syscall n-gram TF-IDF SVD, embedding PCA, say-do score] as a cross-check.
6. Validation (30-36): inject known-bad agents (system prompt that adds a hidden side goal like reading ~/.ssh or curl to an unlisted host, reward-hacking variants). Report precision/recall at top-k flagged, comparing four detectors: English-only, low-level-only, say-do, and combined. Make a dashboard of the trajectories in embedding space with outliers highlighted.

Pip shortlist: `datasketch`, `py-tlsh`, `sentence-transformers`, `scikit-learn`, `tslearn` or `dtaidistance`, `rapidfuzz` (fast Levenshtein, [unverified]), `numpy`, `pandas`, `vllm`. Skip ssdeep initially (native build pain).

Pitfalls:
- Non-determinism: temperature>0 makes honest runs differ; use cohort size >= ~15 per task and a fixed seed set; check the false-positive rate on a clean run before the injected one.
- Median of what? Different tasks have different "normal"; cohort per task.
- Trace noise: unfiltered strace is dominated by startup syscalls and timestamps/PIDs; normalization quality decides everything.
- Fuzzy byte hashes (ssdeep/TLSH) behave poorly on short strings; TLSH has a minimum input length ([unverified] ~50 bytes).
- Mean-pooled embeddings hide a single bad step (Trajectory Guard); score per step and take max/top-k.
- Thinking-mode CoT of Qwen3 may be unfaithful (Turpin; Lanham) so don't treat a consistent say-do result as proof of safety; also don't train against the monitor (Baker et al. obfuscation finding).
- LLM judge fed attacker-controlled text (tool output, file contents) is prompt-injectable; delimit and treat as data.
- Syscall tracing with ptrace slows agents and can be evaded by static binaries doing raw syscalls only if tracing isn't at kernel level; eBPF is more robust but needs privileges.
- Three 2026 arXiv IDs (2601.00516, 2606.00765, 2610.12375) are recent; I could only read abstracts/snippets, so re-verify before citing in the write-up.
