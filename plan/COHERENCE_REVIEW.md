# COHERENCE_REVIEW: Iraj's original plan vs everything added since (Sat 2026-11-07, ~14:00 EST)

Analysis and writing only. No code changes and no LLM calls. Sources:
- the original PDF;
- plan/ARCHITECTURE.md and plan/ARCHITECTURE_v2.md;
- plan/CONTRACTS.md §9-§9d (master), plus §9e on branch `connect-edges` (`/home/iraj/projects/swarm_connect`, commit 40ec829, merged into `game-fixes`);
- GRID_PLAN/GRID_RESULTS, SWEEP_PLAN/SWEEP_RESULTS, SOCIAL_DYNAMICS, GAME_THEORY, GAME_THEORY_AUDIT and NETWORK_PLAN, with the driver logs at 13:38;
- paper/draft.md.

The game-fixes branch (`/home/iraj/projects/swarm_fixes`) has no fix code or plan file yet: its only commits past master are the connect merge and the audit. The fixes are therefore reviewed as the lead described them.

## 1. Original intent (from the PDF itself)

**The PDF was found and read.** It is `/home/iraj/.claude/channels/discord/inbox/1794020442701-1568460140103991296.pdf`, titled "Apart Research Sprint- GSU", 4 pages with the last one blank. The text was extracted with pypdf in a throwaway uv env, because poppler is not installed.

**The second PDF matches it.** `…1794021366791…pdf` ("Untitled 1") is identical word for word except for its title (checked by a word-level diff). ARCHITECTURE_v2's "word-for-word identical" claim is therefore **true**.

**Stated rules:**
- **Agents and keys.** Each agent has a 2-word ID and 5 keys `{ID:int, key:int}`. Keys are rivalrous: multiple copies exist, but each has one owner.
- **Goal.** Each agent needs 3 infos, and its goal is to get the keys for them. Partial credit is possible.
- **Tools, 1-2 per turn:** message an agent, view the log of last round's actions, view the board, write to the board, give a key (the recipient is notified), and defect.
- **Defect.** If the burned ID is one of the target's needs, the target can never get it and is told so, and the actor gains a key it needs. If the ID is wrong, the actor "loses ability to progress on one piece of info", or is delayed n turns. A defect is allowed only while the target has not won.
- **Win.** An agent wins with all 3 keys, "or however many keys it can use if burned". So the PDF itself sanctions winning after a need is burned.
- **Environment.** N is 20+. Tool use and thought are budgeted, and immediate replies are perhaps allowed. Turn order is either fixed or random each round.
- **End.** The game stops after 100+ rounds, or when everyone has won or is fully burned or has won.
- **God.** An adversarial **agent**, given a prompt and powers to "mess with the network".
  - Tools: Activity Check, Message Check (grep/csv) and Wait (sleep until N more turns).
  - Powers, with a budget of K **per game or per round**: Message Fraud and COT Control.

**Research intent (End Results + THINKING):**
- **RQ1, strategies.** Which strategies do the agents play?
- **RQ2, sharing.** Are agents *willing to share info*? In the PDF, "cooperation" means information sharing, not only key giving.
- **RQ3, outcomes.** Final score and how long the game takes, with qualitative and quantitative metrics.
- **RQ4, God dose and timing.** Give God *more power budget*, or let it react *earlier or later*, and see how that changes RQ1-RQ3.
- **THINKING:** "Watch tower" means monitoring. "Mind control" means CoT control. "Ripple effect" means how one intervention propagates.

**What God models:** a hidden network-level attacker with two levers.
- External: identity spoofing on the message channel.
- Internal: memory/CoT tampering.
- It has observation tools that only an *LLM* God would use.

**Nothing in the PDF defines** a team score, a network topology, winners leaving, scarcity or a held-key value. All of those are later additions.

## 2. Inventory of changes since the PDF

Status values: **v1** = in the paper's current results; **built** = implemented but not in any analysed result; **running**; **planned**.

| # | Change | Purpose | Status | Verdict | Why |
|---|---|---|---|---|---|
| 1 | View log/board folded into every observation; `grep_log` tool | Save calls; a deviation the paper states | v1 | **Keep** | Already disclosed in paper §3.1. |
| 2 | N=10, 20 rounds (PDF: 20+, 100+) | Cost | v1 | **Keep** | Disclosed. The N=40 network cells partly answer the PDF's N. |
| 3 | Qwen3-8B → gpt-oss-120b via OpenRouter | Throughput and quality | v1 | **Keep** | Disclosed. The provider mix is a known confound. |
| 4 | **Scripted God** (closest-to-winning victim, fixed templates). The LLM God was never run quantitatively | Exact labels, controlled K | v1 | **Keep, but flag drift** | The PDF's God is an *agent* with observation tools. Every result uses a template script, and God's tools are unused. |
| 5 | D1 mint, D2 lose_need (lowest-id open need), D3 win/partial credit, D4 feasible worlds with needs disjoint from holdings | Resolve PDF ambiguities | v1 | **Keep for v1** | PDF-consistent. D4 is what makes giving free (§3). |
| 6 | D7 sequential/simultaneous; D12 victim_then_delayed defects; D8 scratchpad as the CoT target; D14 God undisclosed; D15 key ids visible | Lead decisions | v1 | **Keep** | |
| 7 | Paired forks A/B, noise B′ (from r1) and B″ (fork-matched) | Measure ripple counterfactually | v1 | **Keep** (core contribution) | It is the PDF's "ripple effect" done properly. |
| 8 | Board knobs (CONTRACTS §9b): disabled, delayed (k=2) | Channel-structure test | v1 (sweep) | **Keep** | Board-off is the paper's one robust effect. |
| 9 | Board knobs: `post_costs_turn`, `anonymous`, `post_skip_rounds` | Board economics | built, demo only | **Defer** | Not run. The audit shows turn costs tax the *helper*, not the poster (audit #6). |
| 10 | `winner_policy: sit_out`, winners leave (§9c, Iraj's request) | Stop post-win self-harm; "winners are out" | built, never analysed | **Drop from experiments** (keep the knob) | Sim: strands 13.4% of needs even with perfect cooperators, makes D strictly dominant, enables gift- and burn-ejection, and games never end early. |
| 11 | Social network (§9d): ER3 `contacts` / `known_ids`, neighbour-scoped board, local log | Track 2: does topology matter; gossip | **running** (N=40, worlds 0-3) | **Keep, in this paper** | Directly serves RQ2 (sharing info). Interim: B 4% vs A 52% wins at r7, with no relays, no gossip and no name spread. |
| 12 | `reasoning_effort: high` variant of B (`net40_er3_contacts_high_sim`, 2 worlds, ≤ r10) | Is the collapse a reasoning limit? | running | **Keep as exploratory** | Changes the model's behaviour and max_tokens, so it is not a game-rule comparison. Footnote only. |
| 13 | `connect(target)` dynamic edges at 2-3 turns' cost (§9e) | Let agents rewire | built (branch) | **Defer** | Audit: useless without knowing who holds what (K = C = 0.153 under board-only info), and a cost of 2 vs 3 makes no difference. It only becomes meaningful together with #17. |
| 14 | Fix: `lock_and_stay` winners (score locked at the win, agent stays, can give and relay) | Removes self-harm (22% of need slots given away) without stranding | planned | **Keep (v2)** | PDF-consistent: winners stay and cannot be targeted. |
| 15 | Fix: voluntary `leave` | Alternative to sit_out | planned | **Drop** | Redundant with #14. Combined with #19 it is a "lock my bonus and take keys out" exit that brings stranding back. |
| 16 | Fix: wrong defect = `lose_held_need`, penalty stated in the prompt | Remove the free-lottery defect (p\*=0 late in the game) | planned | **Keep (v2)** | Still the PDF's "lose ability to progress on one info". Needs a fallback when nothing is held. |
| 17 | Fix: initial **holdings-only** snapshot on networks | Fix information starvation | planned | **Defer** (or one cell, last) | It short-circuits RQ2 (the information no longer has to diffuse). It probably raises "take from the holder" wrong defects, and in known_ids it may teach names (§3). |
| 18 | Fix: `contact_share` score (own + α·mean of contacts' scores) | Reward forwarding and relaying | planned | **Keep, but change its form** | As specified it rewards only the *last hop*. Prefer a global team share or relay credit (§3), and label it an incentive test. |
| 19 | Fix: `held_key_bonus` (ε per held key) | Make giving costly, i.e. a real dilemma | planned | **Keep (v2)** | No generator change, so v2 can replay G1's exact worlds. |
| 20 | Fix: `scarce_fraction` (demand > supply on some infos) | Real rivalry | planned | **Defer** | It breaks D4 (lead-confirmed), changes the generator (no world pairing with v1), makes the welfare ceiling < 1 and world-dependent, and adds noise. |
| 21 | Fix: God target `max_betweenness` | Bigger God effect on networks | planned | **Defer** | There is no God arm on networks. LLMs don't relay, so bridges carry nothing. The audit's −19% models "victim never gives", which is far stronger than the template note "don't give X". |

## 3. Contradictions and rule interactions

1. **Winner policies conflict.**
   - The options are `continue` (v1), `sit_out` (built), `lock_and_stay` (planned) and voluntary `leave` (planned).
   - **They must be one enum.**
   - Voluntary leave is meaningless under sit_out and redundant under lock_and_stay. With held_key_bonus it becomes "exit with your keys", which brings back the stranding that killed sit_out.
   - Under sit_out, the scripted God's closest-to-winning victim has often already left, so powers fail unspent and the *effective K* falls. The dose is not comparable across winner policies.
   - **Choose lock_and_stay for v2. Keep sit_out as a documented knob with its simulation result.**
2. **post_skip_rounds and connect skips.**
   - Both write `delayed_until_round = max(..)`, as does `wrong_defect_penalty: delay`.
   - They cannot stack within one turn (connect takes the whole turn), so there is no double-count bug.
   - Each is a tax on help to others: receiving is passive, so a skipped agent loses nothing privately.
   - Under sit_out, a skipping agent can be gift-ejected before it hands out its spares.
   - **Do not combine them in any v2 cell.** If kept, describe them as "friction on helping".
3. **`contact_share` and what "cooperation" means.**
   - **It does not reward the hops it is meant to fix.**
     - Holder i → relay j → needer k, with d(i,k)=2: j is rewarded (k is j's contact), but **i is not**, because k is not i's contact.
     - For the 52% of needs that are ≥3 hops away, the first hops get no incentive at all.
     - It mostly re-rewards one-hop gives, which LLMs already make for free.
   - **It changes the meaning of the measure.** With α>0, giving and forwarding are self-interested, so the give rate and gossip counts no longer measure *willingness* to share (RQ2). They measure **response to an incentive**.
   - **Recommendation:**
     - Use a **global team share** (own + α·mean of all scores; simple to state, rewards every hop) or explicit relay credit.
     - Report it as "does the swarm forward when forwarding pays?", next to the unrewarded B baseline.
4. **Scarcity, held_key_bonus and the God effect.**
   - Under v1, God's forged DM asks for "one of your keys". Spares are free, so complying costs nothing (GAME_THEORY A2.6). The null is therefore partly built in.
   - With held_key_bonus, complying costs ε (0.05), which is still tiny.
   - With scarcity, a misdirected contested key really costs a need, so God bites harder.
   - **But** scarcity also forces defects in *both* branches. That raises the SD of the paired Δ, so the MDE rises too.
   - **A v2 God effect, if found, is a God × rules interaction.** It needs its own A/B/B″ under v2 rules and must never be read as "God now matters" against v1.
5. **The holdings snapshot vs defect accuracy.**
   - A correct defect requires knowing the target's **needs**. A holdings-only snapshot does not reveal needs, so it should not raise accuracy.
   - It may *lower* accuracy: 41% of wrong defects already targeted an agent that **held** X ("defect = take from the holder", GAME_THEORY B3). A snapshot that says "Y holds X" invites exactly that mistake.
   - Under lose_held_need, the cost of that mistake is larger.
   - The snapshot is true only at t0 (gives move keys).
   - In known_ids, if names in the snapshot count as "learned", C collapses into "complete graph with a local board", and the name-diffusion question disappears.
   - **If it is ever run:**
     - report wrong defects split by "target shown as holder of X";
     - state whether snapshot names are learnable;
     - pair it with connect, because connect is only useful once holders are known (audit §4).
6. **God targeting vs the paired-fork design.**
   - Any deterministic target rule is fork-safe: A and B share state up to F, so the target is identical.
   - **But the rule must be held fixed across the cells being compared.**
     - `max_betweenness` is degenerate on the complete graph (all ties), so complete-vs-ER God contrasts would mix topology with targeting.
     - Under connect, betweenness changes over time. The rule must specify that it is computed on the live graph at God's round.
   - **God's powers are topology-dependent.**
     - In contacts mode a forged DM must follow an edge.
     - In known_ids a forged DM **teaches** the shown sender's name, i.e. God *helps* diffusion.
   - So "God effect by topology" is not one treatment.
7. **The network and neighbours-only board vs the board-removal finding.**
   - **Same thesis.** The paper's robust result is "removing the global board breaks the economy" (N=10, −0.173). The network cells are a stronger, *graded* version of that ("limit broadcast reach"), so they strengthen the "channels, not liars" thesis.
   - **Not the same experiment, for four reasons:**
     - **N differs.** N=10 vs N=40 changes the game itself: bilateral swap partners fall from 82% to 27% (audit §1).
     - **B bundles three changes.** Its board scope, DM/give restriction and local log all change together. C isolates the board/name side only.
     - **The horizon differs.** A plays 20 rounds and B/C play 30, and `max_rounds` is printed in every prompt ("Round r of R"). The planned "matched rounds ≤ 20" comparison therefore has a horizon confound.
     - **Context differs.** At N=40, A's prompts reach the 14k-token cap by round 9, so agents in A see truncated history and agents in B/C do not.
   - The collapse in B is largely **predicted by geometry**: the audit's all-cooperator ceiling without forwarding is 0.153. The LLM finding is therefore "LLMs forward approximately nothing", which is RQ2. The paper should report B and C against the audit ceilings (0.153 without forwarding, 1.0 with flooding), not only against A.
8. **The PDF's "win by being burned" vs proposed win fixes.** The audit's "win = 1.0" would contradict the PDF. lock_and_stay alone keeps the PDF's definition and removes self-harm. **Do not change the win definition.**

## 4. Measurement rules (what must be held fixed)

1. **Welfare** is always the **mean needs-score**, (held open needs)/3, at game end.
   - It never includes held_key_bonus, contact_share or team terms.
   - Each agent's *objective* (payoff) is reported separately.
   - Under scarcity, also report welfare / (max-flow ceiling of the world).
2. **Win** is sticky "ever won", as in v1.
   - Under lock_and_stay the final score equals the score at the win, so win rate and welfare converge **by rule**.
   - The v1-vs-v2 gap between them is a rule effect, not a behaviour effect.
3. **The God effect** is defined only within one rule set:
   - A − B (common random numbers) and A − B″ (fork at God's first act, all agents resampled, as in v1);
   - victim-only resampling, if added, is a *new* control and is not comparable to v1's B″;
   - the God target rule, the templates and the schedule semantics are held fixed;
   - the primary per cell is one test, stated before launch.
4. **Hold fixed within any comparison:**
   - the worlds (`run.seed 1`, game_idx; the generator unchanged);
   - N, `max_rounds` (it is in the prompt), turn mode and order;
   - the model, reasoning effort, max_tokens, temperature and context budget;
   - the board scope;
   - the provider policy. Pin PrimeIntellect with `allow_fallbacks: false`, or at least report the fallback share per branch.
5. **No pooling** across v1/v2, across N=10/N=40, or across topologies.
   - Cross-rule contrasts are noGod vs noGod on the same worlds with different agent seeds, exactly like board-off. They are labelled "game-design effects".
6. **Divergence** is not comparable across topologies. Local logs cut the coupling between agents, so divergence falls by construction on ER graphs. Report it only against a same-topology B″.
7. **The power floor.** At N=10 one need-slot is 1/30 = 0.033 welfare, and G1's MDE is 0.085 (≈ 2.5 need-slots).
   - The per-forgery victim effect (−0.108 score, GAME_THEORY B8) is ≈ −0.011 welfare, 8× below the MDE.
   - **Every God cell must also report agent-level paired outcomes** (victim score, compliance, self-harm gives), not only welfare.

## 5. Recommended v1/v2 split and experiment list

**v1 (the paper's current results, frozen):** everything in GRID_RESULTS and SWEEP_RESULTS, plus the board-off replication and the SOCIAL_DYNAMICS behaviour. The rules are as now: `continue`, mint, lowest-id lose_need, feasible worlds and the scripted God.
- **The running N=40 network cells A/B/C also stay on v1 rules.** That keeps them interpretable against the paper and the audit ceilings.

**One v2 rule set ("costly giving").** It is v1 (G1 config) with three changes, and every other knob stays at G1's value:
- **lock_and_stay.** Needs are locked at the win. The agent stays and can give, relay and message. It cannot be defect-targeted (PDF) and cannot lose needs.
- **lose_held_need on a wrong defect.** If the agent holds no open need, it falls back to the lowest-id open need. The prompt states the penalty and that a correct defect mints the named key.
- **held_key_bonus ε = 0.05 per key held at game end.** It counts for everyone, winners included, and is not locked. The prompt shows it in the score line.

Excluded from v2: sit_out, voluntary leave, scarcity, the snapshot, connect, max_betweenness, the board economics knobs, and contact_share (a network-only incentive; see E3).
- **Why this set:** the generator is unchanged, so v2 replays G1's **exact 16 worlds**. Every change is PDF-consistent, and together they create one real private cost (holding vs giving) without breaking feasibility.

**Experiments, in priority order.** Costs come from the measured ≈ $0.018-0.025 per N=10×20-round branch and NETWORK_PLAN's per-world N=40 figures; all are [E].

| # | Cell | Rules | Question (PDF RQ) | Design | Code needed | Cost [E] |
|---|---|---|---|---|---|---|
| E0 | Network A/B/C finish, plus offline analysis against the audit ceilings (relays, gossip, name S-curve) | v1 | RQ2, Track 2 | running, worlds 0-3 | none | already capped (≈ $1.8 more) |
| E1 | **Per-round God budget** (PDF "K per round"): message fraud every round r3-r20, K = 1/round (18 acts), G1 templates | v1 | RQ4 dose. Extends K ∈ {1,2,4,6} to the PDF's per-round scope. Predicted ≈ 18 × −0.011 ≈ −0.2 if additive, so detectable | G1 worlds 0-15 × A, B, B″@r3 | config only (schedule entries) | $1.0-1.2 |
| E2 | Offline watchtower and a structural bound ($0) | v1 | THINKING "watch tower"; why the null | rule-based detectors scored on the existing 72 forged DMs and 72 overwrites; the §4.7 bound written into the paper | analysis script | $0 |
| E3 | **Forwarding incentive on B**: global team share α = 0.3, or relay credit (not contact_share as specified) | v1 + one score term | RQ2: do agents forward when it pays? | worlds 0-3, 30 rounds, paired with B | yes (fixes branch) | $0.5-0.7 |
| E4 | v2 costly giving: noGod + God (G1 schedule) | v2 | RQ1/RQ2 (is there a dilemma now: hoarding, reciprocity?) and RQ4 (does God bite once keys have value?) | G1 worlds 0-15 × A, B, B″@r3 | yes (#14, #16, #19) | $1.0-1.2 |
| E5 (if money and time) | v2 board-off noGod | v2 | Does the paper's main effect survive a rule change? | worlds 0-15 | as E4 | ≈ $0.25 |
| E6 (stretch) | LLM God, qualitative | v1 | The PDF's actual God (an agent using activity/message checks) | 4-8 worlds × A, B | must pass a smoke | $0.3-0.5 |

- **Total for E1-E5:** ≈ $2.8-3.4.
- **Ledger:** $8.80 now, plus ≈ $1.8 for E0, gives ≈ $13.6 worst case, below the $20 global cap.
- **Deadline gating** (Sunday 18:00):
  - E1 needs no code and should launch as soon as E0 frees concurrency.
  - E3 and E4 run only if their code and tests are merged by **Sat ~22:00**, so they can finish overnight.
  - Freeze all runs by Sun ~10:00. Anything not launched by then becomes future work.

**Future work** (named in the paper, not run): sit_out (cite its simulated stranding), voluntary leave, scarcity, the holdings snapshot + connect as a pair, max_betweenness God on networks (only once relaying exists), the board economics knobs, victim-only B″ and the BA/WS topologies.

**Best single story for the paper.**
- **Core claim:** "Channels, not liars."
  - v1 shows that a scripted liar is lost in noise while the global board is load-bearing.
  - E1 tests whether the null holds at the PDF's per-round dose.
  - E0 (and E3) extend the channel result to network reach: sparse contacts collapse because LLMs do not forward, even when forwarding is the only route, and E3 tests whether paying for it changes that.
- **The game theory explains the null:** spares are free, so a forged "send me a key" costs nothing. E4 is the one test of whether that explanation is right.
- **Required wording fix in the draft:** the v1 game is a **coordination game with a risky sabotage action, not a social dilemma**. Giving is free and demand never exceeds supply (audit §1), so "mixed-motive" in the abstract and intro should be qualified.

## 6. Open questions for Iraj

1. **The God question.** Should it be "can this liar hurt at all" (E1, v1 rules, PDF per-round budget) or "does it hurt once keys are worth something" (E4, v2)? E1 is recommended first: no code, and directly comparable.
2. **Winner policy.** sit_out was your request. Will you accept lock_and_stay as the v2 meaning of "winners are done", with sit_out reported as designed but flawed (13% of needs stranded)?
3. **held_key_bonus.** Is ε = 0.05 right, and does the bonus lock at the win or count at game end? The recommendation is game end for everyone.
4. **contact_share.** Will you switch to a global team share or relay credit, since contact_share does not reward the first hops? Should agents be told it is a "team score"? The framing itself may change behaviour.
5. **Scarcity.** Will you confirm it stays out of this paper? It overturns the confirmed D4 (all worlds feasible).
6. **The network section.** Will you accept it as descriptive (n=4 worlds, horizon confound A 20 vs B/C 30), reported against the audit ceilings?
7. **LLM God.** Run E6 as a qualitative stretch, or name it as future work? Note that every current result uses a template God, not the PDF's agent.
8. **Deadline.** Is "Sunday 6pm" EST, or 18:00 AoE (Mon 06:00 UTC, as ARCHITECTURE reads it)? This sets the code-merge cutoff for E3 and E4.
