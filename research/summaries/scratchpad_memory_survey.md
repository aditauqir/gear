# Scratchpad / Memory / Compaction survey for "Keys & God"

## TL;DR
- **BotC + Dwarkesh: link exists.** https://www.dwarkesh.com/p/clocktower (386 BotC games, same-model teams, programmatic Storyteller). It describes labelled private-whisper / private-reasoning channels but NO notes/scratchpad/in-game memory and no cross-game memory (byline unverified). The richest BotC memory designs are elsewhere: Bench on the Clocktower (scratchpad + recall + recent window), Clocktower Radio (short-term -> long-term compaction), Sullivan (notes file rewritten each night, history cleared).
- **No formal standard** for agent memory/notes exists (vendor blog says so; Mem0 MCP servers disagree on tool names).
- **De facto pattern**: private agent-authored text notes/diary rewritten at phase boundaries + short window of recent raw events + compacted older history; GM/harness owns ground truth.
- Memory-as-CRUD (Letta blocks, Anthropic memory tool view/create/str_replace/insert/delete/rename on /memories, LangGraph namespace/key) is the framework-side convention; social-game benchmarks mostly use whole-text rewrites instead.
- Private reasoning is kept separate from public speech nearly everywhere (Werewolf Arena, Sullivan, Among Us, alignment-faking scratchpad); XML-ish tags are used (Clocktower `<SAY>`), with documented leak failures.
- **Recommended**: per-agent capped notes blocks (commitments/trust/plan/lessons) + recent window + rolling summary; harness holds ground truth + hidden provenance; God tampers at the agent-view layer and logs every edit.
- **Ablations**: S0 windowed only; S1 agent-rewritten notes (Sullivan); S2 diary + periodic consolidation (AI Diplomacy); S3 harness-written recursive summary (AvalonBench / Clocktower Radio).
- Unverified/gaps listed in section 5.

(TL;DR is inserted at top at the end. Every claim has a URL I fetched or saw in search results; "UNVERIFIED" marks anything I could not confirm from the page text.)

## 1. Social-deduction / negotiation environments

### 1.1 Blood on the Clocktower (BotC) and Dwarkesh
- **Dwarkesh link: FOUND.** Page https://www.dwarkesh.com/p/clocktower (fetched) describes 386 BotC games, each team made of copies of one model, programmatic "probability table" Storyteller, script Trouble Brewing, code public on GitHub (repo URL not seen by me). The page is on Dwarkesh's site; I did NOT verify the byline (the fetch summary said only "the author"). A LessWrong commenter says Dwarkesh "recently shared a similar project and referenced the Bench on the Clocktower work" (https://www.lesswrong.com/posts/4pgGkbwvdmxKPcJsM/bench-on-the-clocktower, via fetch summary).
- **Dwarkesh harness memory: essentially none described.** Models "start each game totally fresh"; no cross-game memory (last-10-games-in-context is only an untested idea). The page does NOT say whether there is a notes file/scratchpad. Logs show labelled channels like "[evil teammate, private whisper]" and "[evil heiress, private reasoning]". Each day good players are privately asked for a P(Demon) per player (measurement). Source: https://www.dwarkesh.com/p/clocktower
- **Bench on the Clocktower (LessWrong, MATS project)** https://www.lesswrong.com/posts/4pgGkbwvdmxKPcJsM/bench-on-the-clocktower : four memory mechanisms: rules+role always present; only most recent few thousand tokens of context; a model-written **scratchpad** ("write key ideas into own scratchpad"); a **recall function** to retrieve earlier-visible info. A comment reports private reasoning leaked into public chat when a model wrote a literal `<SAY>` tag inside reasoning, so there is a private-reasoning channel using tagged output. No cross-game memory. Implementation details of scratchpad not given.
- **Clocktower Radio** https://clocktower-radio.pages.dev/how-it-works.html : history is compacted by the model into a **fixed-size short-term memory** after an (unstated) threshold, then compacted into **long-term memory at end of each day**; purpose is to mimic human forgetfulness. Models must show evidence of considering multiple worlds in their reasoning. No separate notes feature described.
- **James Sullivan, "Claude plays BotC"** https://www.lesswrong.com/posts/syYBLEkj5bGswz5yf/claude-plays-blood-on-the-clocktower-how-do-ai-agents-work : system prompt = rules + character list + player's history + **notes file** + strategy tips. At end of each night each player rewrites the notes file from recent history and adds **five pieces of actionable strategy advice**, then **history is cleared**. Transcripts split "Public Reasoning" and "Private Reasoning". Finding: evil agents wrote useful info in notes but didn't share it with teammates.
- Also seen: https://github.com/MilkyBoat/BotC-AI (LLM storyteller, RAG over wiki; not examined).

### 1.2 Werewolf
- **Werewolf Arena** (Google Research) https://arxiv.org/html/2407.13943v1 : two memory types. *Observational* = all game events + role-privileged info (Seer's checks). *Reflective* = at end of each round agent summarizes/distills insights from debate. Game Master (rules-based) writes observable events into memories. Public: day debate (bidding turn-taking, 0-4 bid scale), votes, exiles. Private: night actions; Fig. 2 shows private reasoning differing from public speech. Prompt "incorporates the agent's memories and current game state from their perspective"; names shuffled in vote prompts. The paper says it draws on Park et al. 2023 (via search summary of the arXiv PDF listing).

### 1.3 Avalon
- **AvalonBench** https://arxiv.org/abs/2310.05036 (read via https://ar5iv.labs.arxiv.org/html/2310.05036): each LLM player keeps a **recursive, role-conditioned summary** (prior summary + round discussion "Minutes" + mission outcome -> new summary) because of context limits. Reason-then-Action (ReAct, zero-shot CoT) output with a separate parser LLM extracting the action. No hidden scratchpad described; "All conversations are public, and there is no private communication."
- **ReCon** (Recursive Contemplation) arXiv 2310.01320 (abstract only): formulation then refinement of thoughts/speech with 1st/2nd-order perspective taking. Note: this is NOT AvalonBench (I initially fetched the wrong ID).

### 1.4 Diplomacy
- **AI Diplomacy (Every / Alex Duffy)** README https://github.com/EveryInc/AI_Diplomacy : `DiplomacyAgent` has "dual-layer memory with structured diary entries and consolidation". **Private diary** (phase-prefixed; Negotiation Diary, Order Diary, Phase Result Diary w/ betrayal detection) is the main memory; a separate unstructured private journal is debug only ("not used by LLMs"). Recent context = **last 40 diary entries** + current relationships + active goals. **Relationship tracking** on 5-step scale Enemy/Unfriendly/Neutral/Friendly/Ally; **dynamic goals** revised each state update. **Consolidation**: summarization of old diary entries to prevent overflow; README text says "yearly" but the diagram says "every 2 years", with Gemini Flash as summarizer (README is self-contradictory). Files: `ai_diplomacy/agent.py`, `game_history.py`, `prompt_constructor.py`, `lm_game.py`.
- Paper "Democratizing Diplomacy" https://arxiv.org/abs/2508.07485 : abstract only mentions optimizing a textual game-state representation so a 24B model completes matches; no memory detail seen.
- **Meta CICERO**: NOT researched yet (see gaps).

### 1.5 Other games / simulations
- **Among Us sandbox** (Golechha & Garriga-Alonso) https://arxiv.org/abs/2504.04072 ; details from https://arxiv.org/html/2504.04072 : each step the model must output three parts: **"Condensed Memory"** (own running summary, rewritten every step), **"Thinking Process"**, and **"Action"**. User prompt supplies last few observations/actions and legal actions. Thinking is logged and probed/scored for deception by researchers; paper does not state explicitly that other players cannot see it (UNVERIFIED, but design implies they only get observations/speech).
- **Generative Agents** (Park et al. 2023) https://ar5iv.labs.arxiv.org/html/2304.03442 : memory stream of natural-language records. Retrieval score = recency (exp. decay 0.995 per sandbox hour) + importance (LLM-rated 1-10 at write time) + relevance (embedding cosine), each min-max scaled, all weights 1. Reflection triggers when summed importance of recent events > 150 (about 2-3x/day): take 100 most recent records -> 3 salient questions -> retrieve -> 5 insights with citations; stored as reflections that can cite reflections (trees).
- **GovSim** https://arxiv.org/abs/2404.16698 (search-result summary): agents follow the Park et al. generative-agent framework with planning, harvesting and discussion phases; removing communication led to over-use of the commons; code github.com/giorgiopiatti/GovSim. I did NOT read its memory details.
- **Concordia** (DeepMind) https://github.com/google-deepmind/concordia and https://github.com/google-deepmind/concordia/blob/main/concordia/components/README.md : an Entity is built from **components**; `act()` calls every component's `pre_act(action_spec)` in parallel and `ConcatActComponent` concatenates outputs into the prompt. Memory = `AssociativeMemory` (semantic retrieval, needs a text embedder), `LastNObservations` (recency window), `all_similar_memories` (retrieve + summarize). The paper abstract (https://arxiv.org/abs/2312.03664) says components mediate between LLM calls and associative memory retrieval. Game Master side formats observations and delivers them to each agent (`MakeObservation`).
- **AI Village** (AI Digest) https://theaidigest.org/village/goal/improve-your-memory and https://www.lesswrong.com/posts/fanXbcZzpuGPojtHH/how-the-ai-village-works (search-result summaries; full posts not read): agents have a self-written "consolidated memory" with a ~7500-character cap; they append while consolidating and are asked to rewrite only when over the cap. Agents spontaneously built tiered memory, guard scripts and a shared `inventory.yaml` index. Lesson: rules that are only written down but never executed as checks fail. Treat the details as secondary-source.
- **CICERO** (Meta) https://ai.meta.com/blog/cicero-ai-negotiates-persuades-and-cooperates-with-people/ (search summary): dialogue model conditions on game history + planned "intents"; no dedicated memory module reported. Relevant idea: a separate structured **intent** object that grounds messages (analogue of our "commitments" block). Not a memory precedent.

## 2. Agent-framework memory and compaction

- **Letta / MemGPT** https://docs.letta.com/guides/agents/architectures/memgpt , https://docs.letta.com/guides/agents/memory , https://docs.letta.com/concepts/memory-management : in-context "core memory" = labelled **memory blocks** (persona, user, working state; always visible) that the agent edits via tools `memory_insert`, `memory_replace`, `memory_rethink`; out-of-context = recall (`conversation_search`) and **archival** store (`archival_memory_insert/search`, vector DB backed). Older `core_memory_append/replace` are deprecated. Block character limits are claimed by third-party summaries only (UNVERIFIED on official pages).
- **Anthropic memory tool** https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool : client-side; tool `{"type":"memory_20250818","name":"memory"}`; six commands `view`, `create`, `str_replace`, `insert`, `delete`, `rename` over a `/memories` directory; your app executes them against storage you control; docs show `.xml` memory files; system prompt auto-added says "ASSUME INTERRUPTION: your context window might be reset at any moment"; docs require path-traversal protection and size caps.
- **Anthropic context editing** https://platform.claude.com/docs/en/build-with-claude/context-editing : `clear_tool_uses_20250919` (default trigger 100k input tokens, keeps 3 most recent tool use/result pairs) and `clear_thinking_20251015` (keeps last 1 thinking turn by default); Claude is warned near the threshold to write to memory files first.
- **Anthropic compaction** https://platform.claude.com/docs/en/build-with-claude/compaction : server-side summary replaces older turns; on-demand vs token-threshold modes; you can supply your own summarization prompt and keep recent turns verbatim; memory is recommended alongside for what must survive.
- **OpenAI Agents SDK sessions** https://openai.github.io/openai-agents-python/sessions/ : `Session` protocol = `session_id`, `session_settings`, `get_items`, `add_items`, `pop_item`, `clear_session`; many backends (SQLite, Redis, SQLAlchemy, ...); `OpenAIResponsesCompactionSession` wraps a session for compaction; `SessionSettings(limit=N)` caps retrieved items; `session_input_callback` prunes history before the model call without changing stored data.
- **LangGraph** https://docs.langchain.com/oss/python/langgraph/memory : short-term = per-thread state via checkpoints; long-term = JSON documents in a **store** keyed by (namespace, key); taxonomy semantic / episodic / procedural; writes either "hot path" or background.
- **Alignment-faking hidden scratchpad** https://www.anthropic.com/research/alignment-faking : model told to reason in a "secret scratchpad" and led to believe it was invisible to users and Anthropic; researchers read it. (I could not confirm literal tag names from the pages I saw; I recall `<SCRATCHPAD_REASONING>` but that is UNVERIFIED here.)
- **Apollo in-context scheming** (https://arxiv.org/pdf/2412.15433 listing and the o1 system card https://arxiv.org/pdf/2412.16720 were only seen as search hits): I did not verify how Apollo's scratchpad/CoT is exposed. UNVERIFIED; do not cite scratchpad specifics from Apollo.

## 3. Is there a standard?
**No formal standard found.** Evidence: a vendor blog (https://memu.pro/blog/agentic-ai-foundation-mcp-memory, search snippet, commercial source) says none exists; Mem0 MCP servers expose differing tool names (`save_memory`/`search_memories` vs `add_memory`; https://github.com/walbercardoso/mcp-mem0 and search hits), which shows no shared schema. I did not find A-MEM or a survey paper (searches returned nothing).
**De facto patterns that recur across sources:**
1. A private, agent-authored **notes/diary text** that is rewritten or appended at phase boundaries (Sullivan notes file; AI Diplomacy diary; Among Us Condensed Memory; AI Village consolidated memory; Clocktower Radio short/long-term).
2. Memory as **labelled blocks or files with size caps** the agent edits through a small CRUD tool (Letta blocks; Anthropic memory-tool file ops; LangGraph namespace/key docs).
3. A **window of recent raw events + compacted older history** (Clocktower "few thousand tokens"; AI Diplomacy last 40 diary entries; Anthropic keep-N-recent).
4. **Private reasoning separated from public speech** in the logs (Werewolf Arena Fig. 2; Sullivan Public/Private Reasoning; Dwarkesh channel labels; Clocktower `<SAY>` leak).
5. **Referee/GM owns ground truth** and writes observations into each agent's memory (Werewolf Arena Game Master; Concordia GM).
Retrieval-heavy designs (Generative Agents, Concordia associative memory) are the minority in the social-deduction results and need embeddings; the LLM-game benchmarks mostly use text rewriting.

## 4. Recommended design for Keys & God (inference built on the precedents above; this section is my proposal, not a sourced claim)

### 4.1 Data structure (per agent, one JSON doc; LangGraph namespace/key style, Letta block style)
```
agent/{id}/
  notes: {                      # PRIVATE, agent-editable, char-capped blocks (Letta blocks)
    commitments: "...",         # who promised what, keys held/owed   (CICERO "intent" analogue)
    trust: {agent_j: Enemy|Unfriendly|Neutral|Friendly|Ally},   # AI Diplomacy 5-step scale
    plan: "...", lessons: "..." # Sullivan's 'actionable advice' slot
  }
  recent: [last K raw events the agent actually saw]            # Clocktower / AI Diplomacy window
  summary: "rolling compacted older history"                     # Avalon / Clocktower Radio / Among Us
  reasoning_last: "private reasoning trace from previous turn(s)" # optional carry-over
  # hidden from the agent, visible to harness/evaluators:
  _provenance[item_id] = {source: self|gm|peer|god, t, hash}
```
Separate **ground-truth event log** (append-only, written by the game master like Werewolf Arena / Concordia GM). Agents never see it directly; their `recent` is a view of it.

### 4.2 Private vs visible
- Public: broadcast messages, trades, outcomes. Private: DMs (to sender/recipient only), `notes`, `reasoning`. Other agents never see notes or reasoning (matches Sullivan, Werewolf Arena, Among Us).
- Output format with XML-ish tags, one per channel: `<reasoning>`, `<notes_update>`, `<say to="*|id">`, `<action>`. Precedent: Bench-on-the-Clocktower `<SAY>` tags (and its documented failure of reasoning leaking into public when a tag was mis-emitted: parse strictly, default-deny to private).
- Qwen3-8B is small; prefer tag-parsed whole-block rewrites over multi-step tool calls (Sullivan/Among Us style) rather than Letta/Anthropic-style CRUD tool loops. (Judgement call, untested.)

### 4.3 Update mechanism
Once per round (phase boundary) the agent emits `<notes_update>` rewriting named blocks (capped, e.g. 1-2k chars each; AI Village's cap is ~7500 chars total). Between rounds, harness appends events to `recent`. This mirrors Sullivan: rewrite notes from recent history, then clear history.

### 4.4 God tampering plugs in at the view layer
Three tamper operators, all applied to the agent-facing objects, never to ground truth:
1. **Forge message**: insert an item into the target's inbox/`recent` with `_provenance.source=god` (spoofed sender field).
2. **Overwrite notes**: replace a notes block (equivalent to Anthropic memory tool `str_replace`/Letta `memory_replace` called by an adversary; the Anthropic doc's path/ownership validation point applies: only the harness+God should write to notes dirs).
3. **Overwrite reasoning**: replace `reasoning_last`.
Log every tamper to a `tamper_log` with (target, field, old hash, new hash, t). Metrics: does the agent act on the forged item, does it cite it in later notes (propagation), does it contradict `recent` and flag it (detection). Because compaction rewrites notes from `recent`, a forged item can be "laundered" into the summary; keep `_provenance` through compaction in the harness only (the agent cannot see it) so you can measure laundering.

### 4.5 Switchable memory strategies for ablations
- **S0 (control) Windowed**: last K events only, no notes/summary. Baseline (Clocktower "few thousand tokens" without scratchpad).
- **S1 Notes-rewrite** (Sullivan): agent rewrites capped notes each round; raw history cleared. Maximises the God-overwrite surface (notes are the whole memory).
- **S2 Diary + consolidation** (AI Diplomacy): append structured per-phase diary entry; context = last N entries + trust table; every M rounds a summarizer LLM consolidates old entries (README conflicts on interval: yearly vs every 2 years, so choose M ourselves).
- **S3 Recursive harness summary** (AvalonBench / Clocktower Radio): the harness, not the agent, writes the summary (prior summary + new minutes -> new summary). Agent cannot self-edit memory; tamper must go through the summarizer. Good contrast: agent-controlled memory (S1/S2) vs harness-controlled (S3).
- Optional S4 if time: Generative-Agents retrieval (recency/importance/relevance); costs embeddings and likely out of scope for a hackathon.
Compaction trigger: round-boundary (all strategies) plus a token-budget guard; Anthropic's pattern of warning the model to save notes before truncation is cheap to copy.

## 5. Gaps / caveats
- Dwarkesh page byline, GitHub repo URL and the harness's actual per-agent notes not verified; the post may use a notes mechanism it just doesn't describe.
- Not read in full: GovSim memory, AI Village full posts, Apollo scratchpad method, CICERO paper, Concordia paper, Werewolf Arena summarisation prompt, alignment-faking exact tags.
- Search-engine summaries were used for several secondary claims (marked "search summary").
