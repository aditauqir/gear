# GAME_THEORY_AUDIT: an independent audit of the Keys & God rules as they stand now

Written Sat 2026-11-07. Analysis only: no LLM calls, no changes to game code or configs.
- **Script:** `swarm/analysis/game_theory_audit.py`. Run it with
  `PYTHONNOUSERSITE=1 /home/iraj/miniconda3/envs/swarm/bin/python -m swarm.analysis.game_theory_audit --worlds 30 --procs 16 --out plan/figs`.
  About 1 minute on 16 processes, deterministic.
- **Numbers:** `plan/figs/game_theory_audit.json`. **Figures:** `plan/figs/gt_audit_distance.png` and `plan/figs/gt_audit_sim.png`.
- **What the script uses:**
  - the real world generator (`game/world.py`) and the real graph builder (`game/network.py`);
  - world seeds from `runner.spec.world_seed`, so game_idx 0-5 of `configs/net40_*` are exactly the live worlds. The ER edge lists match `runs/net40_er3_contacts_sim/games/*/meta.json` for all 6 worlds;
  - real transitions: every action goes through `game.resolve.resolve_turn` → `rules.apply`, with simultaneous turns and a reshuffled priority order.
- **What the script models itself:** information. Every agent posts its open needs and keys truthfully each turn; INFO_MODES sets how far and how fast that spreads. This is an idealised upper bound on what LLMs know, not the LLM observation pipeline.
- **Scope of the simulation:** N=40, 30 worlds, 30 rounds. All three topologies run 30 rounds; the live A cell now runs 20. There is also an N=10 block on `grid_oss_sim_k2` to check GAME_THEORY.md.
- **Branch `connect-edges`:** its worktree (`/home/iraj/projects/swarm_connect`) has no commits or diffs past master yet, so `connect` is modelled as described in the brief. It adds an edge to the target and costs the connector 2 or 3 rounds.

**Policies:**
- **C:** gives a key it does not need to a believed needer. In contacts mode it also relays keys toward needers further away.
- **Cn:** C that never relays.
- **H:** hoarder.
- **D:** C plus a defect whenever it believes an addressable non-winner shares one of D's unheld needs.
- **B:** C plus one blind defect per turn on its own unheld need.
- **S:** swapper. It gives only to an agent that holds one of its needs or has given to it before.
- **K:** C plus `connect` to the nearest believed holder of a missing need.

**Information modes:**
- **oracle:** everyone sees the true current state.
- **board:** truthful posts every turn, seen one round later. This is the global board on the complete graph and the neighbour board on ER.
- **gossip2:** posts are forwarded once, so they reach 2 hops, with 1 round of lag per hop.
- **gossipAll:** perfect flooding.

In known_ids mode, every agent named in a forwarded post becomes addressable, and known pairs can talk directly.

## Headline

1. **There is no dilemma in the core game.** A key you hold is never one of your own needs, so giving it costs you nothing. Keys are never worth anything to the holder. All-cooperate reaches welfare 1.000 in 3-5 rounds. Every world has zero scarcity: in 3,000 generated N=40 worlds, no info has more demand than supply. Defecting is never *needed* in the default game.
2. **`sit_out` fixes winners giving away needed keys, but it causes a new loss of the same size.**
   - Keys leave with the winners. Even with perfect cooperators and perfect information, **13.4% of all need slots become permanently unsolvable**, and welfare drops from 1.00 to 0.84.
   - Under sit_out, defection becomes **strictly** profitable: one D among cooperators scores 0.98, against 0.82 for a cooperator.
3. **The ER3 contacts network is information-starved.**
   - **84%** of needs have their nearest holder 2 or more hops away, and 52% are 3 or more hops away.
   - **60%** of agents have *no* need held by a neighbour.
   - Without relays and forwarded requests, the ceiling is welfare **0.15**.
   - Forwarding and relaying help other agents, never the agent who does them. LLMs do not gossip (SOCIAL_DYNAMICS: 0 rumour chains in 19k messages).
   - So B and C measure altruistic information forwarding, which the game gives no reason to do. B is the ER3 contacts cell, C the ER3 known_ids cell.
4. **The penalty for a wrong defect is regressive.** `lose_need` takes your *lowest-id* open need. If that need is unheld and you will not get it anyway, a wrong defect costs nothing: late in the game it is a free lottery ticket.
5. **Turn costs fall on others, not on the agent who pays them.** This covers `post_costs_turn`, `post_skip_rounds` and `connect`'s 2-3 turns. Receiving keys is passive, so an agent's own action slots have almost no private value. Making them cost something taxes the agent's *help to others*, not the agent itself.

---

## 1. The game as a payoff model (re-derived from the code)

**Parameters** (base and net40): k=5 keys, m=3 needs, 2 copies of each info, 2 actions per turn.
- **N=40:** 100 infos, 200 copies, 120 need slots.
- **Demand per info:** over 30 worlds and 3,000 infos, 0 (16.7%), 1 (46.6%) or 2 (36.7%).
- **Never scarce:** demand is never above supply. The generator reserves a distinct copy for every need, so it is structurally impossible.
- **Junk keys:** only 120 of the 200 copies are useful to anyone, so 40% of the keys are worth nothing.
- **Contested needs:** **61%** of need slots sit on infos with demand = supply = 2. They have zero slack: lose one copy and one need is unsolvable.
- **Bilateral swap partners:** the holder of my need also needs one of my keys for **82% of needs at N=10, but only 27% at N=40.**

**Payoffs.** Score_i = (held open needs) / 3, and welfare = mean score. Nothing in an agent's payoff depends on anyone else's score.

| action | actor | others | notes |
|---|---|---|---|
| give a key you don't need | 0 | +1/3 if the receiver needed it | the action slot is the only cost |
| relay (give a key you hold in transit) | 0 | +1/3 at the end of the chain | uses a slot; no private benefit |
| correct defect on X (X is the target's open need, target has not won) | gains a minted X: worth +1/3 only if X is the actor's own unheld need and it would not have arrived anyway | target loses X for good | mint *adds* a copy: supply inflation |
| wrong defect | loses its **first open need, held or not** | none | free if that need is unheld and hopeless |
| post, message | 0 | information | cheap talk; never verified |

**Is giving really costless? Yes.**
- Initial keys are never your own needs (D4), and a key you hold does not score.
- The only private use of a spare key is **leverage**: "I give X only if you give Y". Because giving is free, the threat to withhold is costless and therefore credible, and hostage-taking is weakly dominant for any agent that expects reciprocity.
- At N=40 hostage-taking mostly deadlocks: only 27% of needs have a bilateral partner. All-S welfare is **0.27** at N=40, against **0.77** at N=10 (complete graph, board). **Growing N quietly turns a bargaining game into a pure coordination game.**

**Is there any reason to hoard?** No private reason. One hoarder among cooperators scores 1.000, exactly the same as a cooperator: free-riding is free. The hoarder costs the others 2% of welfare.

**Is welfare = mean score aligned with individual incentives?** Only weakly.
- **Weakly aligned:** every pro-social act (give, relay, forward, post offers) is privately *neutral*, and the only privately positive act (a defect that is correct and timely) is socially −1 need.
- **Misaligned:** the agent is told to "win", and a win can be created by *losing* needs (§2). Under sit_out a win is also a forced exit.

## 2. The defect EV, exactly (mint + lose_need)

Actor a names its own unheld need X against target t. Let:
- p = P(t really has X open and has not won);
- q = P(a would have got X anyway);
- h = P(a's first open need is currently held);
- q' = P(that first need, if unheld, would have been filled).

EV (in needs) = p·(1−q) − (1−p)·[h + (1−h)·q'], so break-even p\* = L/(G+L), with G = 1−q and L = h+(1−h)q'.

| situation | p\* | EV of a blind guess (p ≈ 0.016) |
|---|---|---|
| everyone cooperates (q=q'=1), h=1/3 | **1.00**: never +EV unless certain, and then exactly 0 | −0.98 |
| LLM-like play (q=q'=0.63, GAME_THEORY.md B3), h=1/3 | 0.67 | −0.74 |
| far need in ER3 contacts, no gossip (q=q'=0.1) | 0.31 | −0.39 |
| last round, first open need unheld (q=q'=h=0) | **0.00**: wrong guesses are free | **+0.016** |

**Blind accuracy from the generator.**
- A uniformly random agent shares a given need 1.6% of the time; a random neighbour, 1.4%.
- The co-needer of a need is a graph neighbour only **4.6%** of the time.
- This matches the 1.9% uninformed LLM accuracy in GAME_THEORY.md.

**Is defect ever strictly needed?**
- **Under `continue`: no.** Every world is solvable by gives alone, and a defect is noise, or an attack that God can trigger.
- **Under `sit_out`, or with stranded copies: yes.**
  - Mint is the only way to create a copy of a key whose copies have left the game.
  - When *both* co-needers of X can no longer reach a copy, a correct defect is even a **Pareto improvement**: the victim loses a need it could never fill, and the actor gains one.

**Simulation (N=40, complete graph, board).**
- **All-D:** welfare 0.661, against 1.000 for all-C. All-B: 0.226.
- **Under `continue`:** one D among cooperators ties a cooperator at 1.000, so D is weakly dominant.
- **Under `sit_out`:** that D scores **0.983 against 0.817** for C, so D is strictly dominant.
- **Among other D agents:** D 0.650 vs C 0.608.

## 3. Score, win and termination

**Win vs score.**
- A win needs only the *open* needs, and burned or lost needs are not open.
- So a burn by someone else, or your own wrong defect that hits your lowest-id open need while it is your only missing need, *creates* a win at 2/3.
- GAME_THEORY.md measured 13% of LLM wins arriving this way.

**`sit_out` locks the score at the win.** This removes the self-harm, because a winner can no longer give away needed keys. But:

- **Keys leave with the winner, and the winner cannot control when it wins.**
  - Receiving your last key cannot be refused.
  - In simultaneous mode, a give that resolves earlier in the round voids your whole chosen turn (`actor_left`), including the gives of your spares.
  - "Give before you win" is good advice that an agent cannot reliably follow.
- **Measured cost.** With perfect cooperators and full information:
  - welfare drops from 1.000 to **0.838** at N=40, and to 0.840 at N=10;
  - **13.4%** of need slots end up with every remaining copy held by departed agents (`stranded_with_departed`).
  - Contested infos have zero slack, so each stranded copy is one permanently dead need.
- **Network effects compound it** (ER3 contacts, full flooding): welfare 1.000 → **0.670**.
  - 20% of need slots are **disconnected**: departed nodes cannot relay, and the remaining graph falls apart. Removing a fraction f of the nodes leaves a mean degree of about 3(1−f).
  - Another 11% of need slots are stranded with departed agents.
- **Forced ejection is a weapon.**
  - **Gift-ejection:** give someone their last need, and their spare keys leave the game.
  - **Burn-ejection:** burn the one need they are missing; they "win" at 2/3, leave, and take their keys with them.
  - Both remove supply at no cost to the attacker.
- **Games under sit_out never end early.** Any stranded need keeps an agent "not done", so every game runs to max_rounds (0/30 finished early in every sit_out cell). Departed agents make no calls, so the cost effect is mixed.

**End-game effects.**
- In the last round, the free-lottery defect (§2) is weakly +EV for any agent whose lowest-id open need is unheld.
- Nothing else unravels, because giving was never costly.
- The God schedule acts at rounds 3 and 5. Under sit_out, its "closest to winning" target has often already left, and the power then fails unspent.

## 4. Solvability on the network (ER mean degree 3, N=40)

**Geometry** of the 30 worlds; the first 6 are the live worlds.

| | value |
|---|---|
| realised mean degree (connected by rejection) | 3.23. Live worlds: 3.10 / 3.60 / 3.65 / 2.90 / 3.30 / 3.45 |
| agents of degree 1 | 12.6% |
| mean hops, needer → nearest holder / → copy in the optimal assignment | 2.63 / 2.78 |
| need slots with nearest holder ≥2 hops / ≥3 hops | **84.3% / 51.5%**. Live worlds: 82-87% / 38-60% |
| agents with none of their 3 needs held by a neighbour | **60%** |

**Results with all-C:**

| information | contacts (B) | known_ids (C) |
|---|---|---|
| neighbour board only (the LLM default) | **0.153** | **0.153** |
| 2-hop forwarding | 0.459 (relays needed) | 1.000 in 5.7 rounds |
| full flooding | 1.000 in **21.3** rounds | 1.000 in 5.5 rounds |
| full flooding, sit_out | 0.670 | 0.833 |
| complete graph, for reference | 1.000 in 4.7 rounds | |

**What the table shows.**
- **Without forwarding, the network game is unsolvable.** The two network modes are the same then, because known_ids learns names only from text that mentions them.
- **known_ids explodes once names get mentioned:** introductions compound, a small-world effect.
- **contacts needs physical relays:** 323 relay gives per game, and about 21 rounds even with perfect information.
- **Relays are necessary.** Cn (never relays) stays at 0.153 under every information mode.

**Is relaying individually rational? It is neutral.**
- One focal non-relayer among relayers scores 1.000, like a relayer (gossipAll, continue); under sit_out it scores 0.825 vs 0.758, overlapping CIs.
- Relaying spends free action slots for zero private gain.
- Under sit_out, a relay that wins while holding a key in transit takes that key out of the game.
- **Relays can break:** a departed node cannot receive (`recipient_left`) or forward.

**When is connect worth it?** Only when the connector knows a far holder's *name and holdings*.
- **With board-only information:** K = C = 0.153. Connect is useless, because nobody knows whom to connect to.
- **With 2-hop forwarding:** welfare 0.459 → **0.621**.
- **With flooding:** time to finish drops from 21.3 to **15.9** rounds; under sit_out, welfare rises from 0.670 to 0.768.
- **Cost 2 vs 3 rounds makes no difference** (0.621 vs 0.626; 15.9 vs 16.6 rounds). The skipped turns cost the connector nothing privately (§5). One focal connector among cooperators scores ≥ a cooperator.
- **Rule of thumb:** connect beats waiting for a relay when the holder is at d ≥ c hops (c = connect cost), because a relay chain needs about d rounds of forwarding plus d gives.

## 5. Information, honesty and gossip

**What can an agent know?** Its own keys and needs, DMs to it, the (scoped) board, and the local log of gives. Nothing about others' holdings or needs is verifiable.

**Incentives to tell the truth:**
- **About your own needs:** yes. That is how you get gifts.
- **Cost of telling the truth about needs:** announced needs invite correct defects from co-needers. GAME_THEORY.md measured board-named needs burned 16.8% of the time, against 10.0% for needs never named.
- **About your keys:** neutral.
- **About third parties (gossip):** zero private value. It costs a slot, or a whole turn under `post_costs_turn`, or k rounds under `post_skip_rounds`.
- **Consequence:** the information the network cells depend on is a public good that the rules do not reward.

**Lying is free and sometimes useful:**
- **"I need X" when you don't:**
  - it attracts a copy of X, which costs the real X-needer whenever X has zero slack;
  - it acts as a **honeypot**: an informed defector who believes you loses a need;
  - it is the only defence against being burned.
- **"I hold Y":** this extracts reciprocal gifts. Nothing checks the claim except the local action log.
- **There is no penalty for lying anywhere in the rules.**

## 6. Exploits and rule interactions

Ranked by expected damage:

1. **God's best target in contacts mode is a bridge.** We modelled a note overwrite ("never give keys") as one agent turning H. Blocking the agent that sits on the most needer→holder shortest paths costs **19%** of welfare (1.000 → 0.807, flooding, continue). A random agent costs 6% (0.937). On the complete graph, blocking one agent costs 2% wherever it sits.
   - The scripted God targets "closest to winning". That is the right target under `continue`, but the wrong one on a network and under sit_out.
   - In known_ids, God's forged DMs carry names and therefore *teach* them, which helps the swarm.
2. **Blind defecting.** All-B welfare is 0.23 on the complete graph and 0.04-0.10 on the network, because 1.6% accuracy times lose_need is ruinous. Wrong defects mostly cost the defector itself, and the warning in the prompt ("you are penalised") does not say how much.
3. **Gift-ejection and burn-ejection under sit_out** (§3).
4. **Board spam.** Posting is free by default, and spam competes for the 14k-token context window. That is a commons problem: the attention of the readers is the shared resource. `post_costs_turn` fixes it, but turn costs are externalities (next point).
5. **Turn costs are externalities.** In this game an agent's own turn produces value only through communication and defects; receiving is passive.
   - `post_skip_rounds` and `connect`'s skip therefore remove the agent's *gives to others*, not its own score.
   - Combined with sit_out, an agent that is skipping can be ejected by a gift before it hands out its spares.
   - `board.anonymous` together with known_ids blocks name learning, and anonymous need posts cannot be served unless the text names the poster.
6. **Collusion.** Gives are already free, so two colluders gain nothing from each other. The only collusive moves are:
   - win-washing: a friend burns your hopeless last need so that you "win";
   - joint burns of a third party's shared need, which nets nothing (mint plus a burn).
   - Neither raises score, so collusion matters only if agents optimise "win".
7. **Holding a key hostage** works at N=10 (82% of needs have a swap partner) and deadlocks at N=40 (27%).

## 7. Where I agree and disagree with GAME_THEORY.md

| claim there | verdict |
|---|---|
| giving spares is free; both "all give" and "nobody gives" are equilibria | **Agree**: reproduced (all-C 1.000, H_in_C 1.000). |
| with perfect information, D weakly dominates; break-even p\* = q or higher | **Agree.** Exact form: p\* = L/(G+L). It is 1 among cooperators, and 0 for a hopeless agent in the last round, which they did not note. |
| all-D welfare 0.753 | **Same direction, a different number:** 0.648 at N=10 and 0.661 at N=40 here, with simultaneous turns and one round of board lag. Theirs was sequential with oracle information. |
| contested infos are "the only real rivalry" | **Partly disagree.** Supply = demand, so they are not scarce at all: rivalry exists only if someone defects. What they really are is *fragile* (zero slack), which matters once keys can leave (sit_out). |
| proposal: `winner_policy: sit_out` "stops self-harm but removes help" | **Disagree that it is a clean fix.** It costs 16% of welfare among *perfect* cooperators (13% of needs stranded), up to 33% on ER3, makes D strictly dominant, and adds ejection attacks. |
| "make giving costly", "scarcity", "retune defect", "close the win/score gap" | **Agree**, and §8 makes them concrete. |
| reciprocity matters little | **Agree, and it is structural:** at N=40 only 27% of needs even have a swap partner. |
| B-section data findings (ICC, LLM accuracy, post-win self-harm) | Not re-derived here; no new LLM data. |

## 8. Ranked issues and minimal fixes

| # | issue | severity | evidence | minimal fix | predicted effect |
|---|---|---|---|---|---|
| 1 | No strategic tension: giving is free, never scarce, keys worthless to their holder, so "cooperation" is coordination plus rule comprehension, not a dilemma | **high** for the paper's framing | all-C 1.000 in 3-5 rounds; H free-rides at 1.000; demand ≤ supply in 100% of worlds | **Value held keys:** +0.05 score per key held at the end (or 1/6 need per spare). Optionally make 10-20% of infos scarce (3 needers, 2 copies) via the generator. | Giving then costs ε while the receiver gains 1/3: a real PD-like social dilemma. Reciprocity becomes rational; hoarding becomes a temptation; the defect gain no longer depends only on timing. Expect lower LLM welfare and real strategy differences. |
| 2 | sit_out strands keys and makes defection strictly better | **high** (if sit_out is used) | 13.4% stranded, welfare 0.84; ER3 0.67; D 0.98 vs C 0.82 | **Leaving is voluntary** (a `leave` action that locks the score), or **lock the score at the win but keep the agent in play** (it can give and relay but cannot lose needs). Alternatively, its keys pass to its contacts. | Recovers about 1.00 among cooperators (the `continue` cells are this fix in the sim), removes the ejection attacks, and keeps the self-harm fix. |
| 3 | Network cells are information-starved; forwarding is a public good with zero reward | **high** for the network track | contacts/known ceiling 0.153 without forwarding; 84% of needs ≥2 hops; LLMs do not gossip | **Score = own + α·mean(contacts' scores)**, with α≈0.3, or credit per successful relay. At minimum, state in the paper that the network cells measure *unrewarded* altruistic forwarding. | Forwarding and relaying become privately positive. You can then ask whether LLMs respond to the incentive, which is testable, instead of whether they altruistically gossip. |
| 4 | Regressive wrong-defect penalty | medium | p\*=0 for a hopeless agent; prompt says only "you are penalised" | Lose the **highest-value held** need (or a key) instead of the lowest-id open need, and state the penalty in the prompt. | Removes the free-lottery defects late in the game; the defect becomes a deliberate gamble. |
| 5 | Win ≠ score: wins created by losing needs | medium | 13% of LLM wins (GAME_THEORY B1) | **Win = score 1.0** (all *original* needs held), or drop "win" from the prompt and show the live score. | Removes win-washing and the motive for deliberate wrong defects. |
| 6 | Turn costs (`post_costs_turn`, `post_skip_rounds`, connect skip) tax the helper, not the actor | medium | K cost 2 vs 3: no difference (0.621 vs 0.626) | Charge the private resource instead: a key, or score ε per post or connect. Otherwise describe these knobs as "friction on help". | Real trade-offs between advertising and holding. |
| 7 | God's scripted targeting misses the best lever on networks | medium for the God track | bridge block −19% vs random −6% | Add a `max_betweenness` target to ScriptedGod for network cells. | Bigger, cleaner God effects in B; no change on the complete graph. |
| 8 | Defect gain mint inflates supply, so a correct defect can be Pareto-improving when copies are stranded | low | §2 | Use `defect_gain: steal` (already a knob) if defects should be pure transfers. | Defect becomes strictly zero-sum, which makes the dilemma cleaner. |
| 9 | N changes the game's nature (swap partners 82% → 27%) | low, but it must be reported | §1 | Report it; compare N=10 and N=40 reciprocity results with care. | |

**Proposed minimal package for a "real dilemma" cell:**
- keys held at the end score ε=0.05;
- `defect_gain: steal`;
- lose the highest held need on a wrong defect;
- win = 1.0;
- `continue`, with winners' scores locked.

This keeps every current mechanic and adds one private cost (holding vs giving) and one private gain (stealing).

## Caveats
- **The policies are hand-written and the information is idealised** (truthful, complete posting). The simulation shows what the *rules* allow, not what LLMs do. LLM welfare will sit well below these ceilings, especially in the network cells, where it depends on forwarding the LLMs rarely do.
- **`connect` is modelled from the brief** (an edge plus 2-3 skipped rounds, aimed at a believed holder); the branch has no code yet.
- **The God bridge experiment is a proxy:** the agent turns H from round 1, whereas the real God acts at round 3 with an overwrite whose effect may decay.
- **Intervals:** 95% bootstrap over worlds (n=30; n=16 at N=10). Invasion cells use 10 worlds × 4 seats. Some sit_out invasion differences (e.g. H 0.86 vs C 0.82) are inside the noise.
