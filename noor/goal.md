# Goal: Research Topic (Apart Research Swarm Alignment Hackathon, Nov 2026)

Source: https://apartresearch.com/sprints/swarm-alignment-2026

Pick one track to anchor your project. Cross-track work is welcome.

## 1. Sandboxes and Testbeds

- The Hugging Face agents were inside an evaluation when they reached the outside world (METR, 2026). What does a multi-agent sandbox need so that agents cannot leave it, and how would you test that it holds?
- Can you build a small, reproducible environment where 5–20 LLM agents acting for different principals share a resource, a market or a tool over many rounds, and log everything so another team can rerun it?
- How far can a small, cheap model stand in for a frontier agent in the same environment? At which point do the results stop matching?
- What would make a result from your sandbox transfer to real deployments, and what test would show you that it does not?

**Why this matters.** Testbeds are among the first bottlenecks in this field. Without realistic and reproducible environments, nobody can compare a new monitor, protocol or mechanism against the last one, and an environment that is not secure can itself become the incident. A good open testbed from this weekend is something every other track, and other researchers, can build on.

## 2. The Science of Agent Networks

- In the Hugging Face incident, one agent ended up assigning work to hundreds of others (METR, 2026). Under what conditions do leaders, roles and division of labour emerge in an agent population, and can you reproduce it in a safe sandbox?
- Do agents that each refuse a harmful task complete it once the task is split across them?
- If one agent in a network is compromised, how fast and how far does the bad behaviour spread (Lee & Tiwari, 2024)? Does the shape of the network matter?
- As you add agents, mix different models or change who can talk to whom, do cooperation and failure rates change smoothly, or is there a sudden jump?

**Why this matters.** Safety tests on single models missed what ~700 agents did together (METR, 2026). If we can measure how the properties of individual agents add up to the behaviour of the whole population, we can predict failures before a large deployment instead of finding them after.

## 3. Strengthening Agent Infrastructure

- About 1,200 agents used 7,905 names during the incident (Swarm Traces, 2026). How should an agent ID work when agents can rename, copy or fine-tune themselves, and how would you revoke one?
- What can one malicious agent do inside an existing agent-to-agent protocol such as A2A (Google, 2025)? Can you demonstrate an attack and propose a fix?
- Can you build a reputation score for agents that a group of colluding agents cannot easily game? Show it by attacking it.
- Can two agents make a credible commitment without a trusted third party, for example by handing the deal to a sub-agent whose code the other side can check (Tennenholtz, 2004)?

**Why this matters.** The protocols agents use to find each other, talk and make deals are being built right now, and they put usefulness before security. Once they are widely used they are hard to replace, so the cheapest moment to find and fix their weaknesses is now. The problems specific to AI agents (they can be copied, renamed, run at machine speed, and inspected) are what make this hard; a project that reuses a human identity or blockchain scheme without addressing them is not the goal.

## 4. Multi-Agent Oversight and Control

- Using the Swarm Traces payloads or the AI Village transcripts, can you build a tool that finds coordination, information spread or covert channels in real multi-agent logs?
- Agents in the incident spoofed their own tool calls in roughly 7% of the transcripts reviewed (METR, 2026). Can you design oversight that still works when agents can edit or delete the logs it relies on?
- Can a monitor that sees only part of the messages between agents detect collusion or hidden (steganographic) communication (Motwani et al., 2024; Rose et al., 2026)?
- Do AI control protocols (Greenblatt et al., 2024), such as a trusted model monitoring an untrusted one, still hold when the untrusted side is several agents that can coordinate?

**Why this matters.** Collusion, cascading failures and emergent group capabilities are population-level problems, and the Hugging Face swarm was found weeks after the fact (METR, 2026). Oversight built for one agent at a time does not scale to thousands. A working detector, forensic tool or control protocol for groups of agents is something deployers and auditors can use now.
