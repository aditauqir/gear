"""Write configs/sweep_*.yaml (plan/SWEEP_PLAN.md): one-factor-at-a-time cells around G1
(configs/grid_oss_sim_k2.yaml: sim, N=10, 20 rounds, God K=2 = fraud r3 + cot_control r5, 5 keys).

God-only cells (start round, K) set runner.fork.control_god = G1's god section, so their control
branch is exactly G1's nogod game (same game_id/seeds; replays from the LLM cache) and the God
branch shares G1's cached prefix up to its first intervention. Game cells (keys, N, rounds) change
the game, so they get their own paired control. run.seed 1, game_idx 0..n-1 (= G1's worlds).

    python infra/sweep/make_configs.py          # rewrites configs/sweep_*.yaml
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

FRAUD = {"power": "message_fraud", "after_turns": 0,
         "args": {"sender": "recent_partner", "receiver": "closest_to_winning"}}
COT = {"power": "cot_control", "after_turns": 0,
       "args": {"agent": "closest_to_winning", "round": "prev", "target": "scratchpad", "mode": "replace"}}
G1_GOD = {"kind": "scripted", "start_round": 3, "budget": {"k": 2, "scope": "game"},
          "schedule": [{"round": 3, **FRAUD}, {"round": 5, **COT}]}


def sched(*items: tuple[int, dict]) -> list[dict]:
    return [{"round": r, **p} for r, p in items]


# name -> (factor, description, n_games, cap, conc_games, god, game overrides, control_god?)
CELLS = {
    # 1. first-intervention round (same two powers, same spacing: fraud r, cot_control r+2)
    "sweep_start1": ("start", "God first acts r1", None, None, 12,
                     {"start_round": 1, "schedule": sched((1, FRAUD), (3, COT))}, {}, True),
    "sweep_start8": ("start", "God first acts r8", None, None, 12,
                     {"start_round": 8, "schedule": sched((8, FRAUD), (10, COT))}, {}, True),
    "sweep_start14": ("start", "God first acts r14", None, None, 12,
                      {"start_round": 14, "schedule": sched((14, FRAUD), (16, COT))}, {}, True),
    # 2. budget K (K=2 = G1, K=6 = G3 exist). K=1: G1's first act; K=4: G3's first four acts.
    "sweep_k1": ("k", "God K=1 (fraud r3)", None, None, 12,
                 {"budget": {"k": 1, "scope": "game"}, "schedule": sched((3, FRAUD))}, {}, True),
    "sweep_k4": ("k", "God K=4 (fraud r3/r5, cot r4/r6)", None, None, 12,
                 {"budget": {"k": 4, "scope": "game"},
                  "schedule": sched((3, FRAUD), (4, COT), (5, FRAUD), (6, COT))}, {}, True),
    # 3. keys per agent (needs 3, copies 2 unchanged; feasibility is checked by world.py)
    "sweep_keys3": ("keys", "3 keys/agent", None, None, 12, {}, {"keys_per_agent": 3}, False),
    "sweep_keys8": ("keys", "8 keys/agent", None, None, 12, {}, {"keys_per_agent": 8}, False),
    # 4. number of agents
    "sweep_n20": ("n", "N=20", None, None, 8, {}, {"n_agents": 20}, False),
    "sweep_n5": ("n", "N=5", None, None, 16, {}, {"n_agents": 5}, False),
    # 5. rounds
    "sweep_r40": ("rounds", "40 rounds", None, None, 12, {}, {"max_rounds": 40}, False),
}


def dump(o, ind=0) -> str:
    """Tiny YAML emitter (flow style for leaves) -- keeps the files short and diffable."""
    pad = "  " * ind
    out = []
    for k, v in o.items():
        if isinstance(v, dict) and v and any(isinstance(x, (dict, list)) for x in v.values()):
            out.append(f"{pad}{k}:\n{dump(v, ind + 1)}")
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out.append(f"{pad}{k}:")
            out += [f"{pad}- {json.dumps(x)}" for x in v]
        else:
            out.append(f"{pad}{k}: {json.dumps(v)}")
    return "\n".join(out)


def main(seeds: dict[str, int], caps: dict[str, float], conc: dict[str, int]) -> None:
    for name, (factor, desc, _, _, conc_games, god, game, ctl) in CELLS.items():
        g = {**G1_GOD, **god}
        fork = {"enabled": True, "noise_replica": False, "serial_pair": False}
        if ctl:
            fork["control_god"] = G1_GOD
        cfg = {
            "extends": "base.yaml",
            "run": {"name": name, "seed": 1, "n_games": seeds[name], "max_concurrency_games": conc_games},
            "reasoning": {"salvage_truncated": True},
            "game": {"n_agents": 10, "max_rounds": 20, "turn_mode": "simultaneous", "turn_order": "reshuffle",
                     **game},
            "god": g,
            "runner": {"engine": "real", "report": True, "fork": fork},
            "roles": {r: {"backend": "openrouter", "model": "openai/gpt-oss-120b",
                          **({"max_tokens": 1000} if r == "agent" else {})}
                      for r in ("agent", "god", "judge", "summarizer")},
            "llm": {"budget_usd": caps[name], "cache": {"mode": "read_write"},
                    "openrouter": {"enabled": True, "model": "openai/gpt-oss-120b", "max_concurrency": conc[name],
                                   "global_cap_usd": 8.0, "price_in_per_mtok": 0.1, "price_out_per_mtok": 0.5,
                                   "reasoning_effort": "low", "provider_sort": "price"}},
        }
        head = (f"# Sweep cell ({factor}): {desc}. Generated by infra/sweep/make_configs.py (plan/SWEEP_PLAN.md);\n"
                f"# base = configs/grid_oss_sim_k2.yaml (G1). llm.budget_usd = this cell's hard cap.\n"
                + ("# control_god = G1's god: the control branch is G1's nogod game (cache replay).\n" if ctl else
                   "# Own paired control (the game itself changes).\n"))
        (REPO / "configs" / f"{name}.yaml").write_text(head + dump(cfg) + "\n")


# As launched (plan/SWEEP_PLAN.md): stage 1 = start*, k*, n20, n5; stage 2 (keys*, r40) only if money is left.
SEEDS = {"sweep_start1": 8, "sweep_start8": 8, "sweep_start14": 8, "sweep_k1": 8, "sweep_k4": 8,
         "sweep_n20": 6, "sweep_n5": 8, "sweep_keys3": 6, "sweep_keys8": 6, "sweep_r40": 6}
CAPS = {"sweep_start1": 0.27, "sweep_start8": 0.23, "sweep_start14": 0.15, "sweep_k1": 0.21, "sweep_k4": 0.26,
        "sweep_n20": 0.86, "sweep_n5": 0.125, "sweep_keys3": 0.30, "sweep_keys8": 0.30, "sweep_r40": 0.80}
CONC = {n: 4 for n in CELLS}      # two drivers x 4 = 8 OpenRouter calls in flight in total
if __name__ == "__main__":
    main(SEEDS, CAPS, CONC)
