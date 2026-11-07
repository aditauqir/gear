# Orchestrator status (resume file)
Updated: 2026-11-07 04:22 UTC

**Goal:** a minimal Keys & God demo ASAP, then the 58-game grid. Deadline Sun Nov 8 at 18:00 AoE.

**Plan docs:** plan/ARCHITECTURE_v2.md (design), plan/CONTRACTS.md (frozen interfaces), plan/REVIEW_v2.md.

**Done:**
- WP0 contracts (committed)
- B2: llm, agents, prompts
- B3: adversary, context, leak oracle
- B5: monitors (Codex)

**In progress:**
- B1: swarm/game (fix the test_observe window test)
- B4: runlog, runner, viz, analysis, doctor, plus a FakeLLM end-to-end test

**Next:** an integrator wires runner/wiring.py, starts vLLM (infra/serve.sh), runs configs/demo.yaml, opens the HTML report, and commits.

**Infra:** vLLM is started with infra/serve.sh (needs PYTHONNOUSERSITE=1). The OpenRouter key is in /home/iraj/projects/swarm_data?/.planAdemoenv. Never print it.
