"""Grid driver + watchdog (plan/GRID_PLAN.md): runs grid cells one after another, each in its own
process group, and kills the group when an abort condition fires.

    OPENROUTER_API_KEY=... PYTHONNOUSERSITE=1 python infra/grid_driver.py \
        --cell grid_oss_sim_k2:1.35:3 --cell grid_oss_sim_k6:0.95:2 --seeds 16 --rounds 20

--cell name:cap_usd:branches_per_seed (config configs/<name>.yaml, run id <name>; cap = the cell's
llm.budget_usd). Abort conditions, checked every 10 s (incremental reads of the run's files):
  ram        MemAvailable < 15 GB
  rg         more than 20 processes named rg
  ledger     global ledger total >= --ledger-stop (default 5.70)
  projection live projected cell cost > cap (after >= 150 paid calls): spent * W_total / W_done, with
             W(call in round r) = the smoke's per-call cost model (prompt grows ~550 tok/round, capped)
  errors     > 5% of LLM calls with an error (after >= 100 calls); any HTTP 400 at once
  parse      > 10% of turns parse_ok=false (after >= 100 turns)
  trunc      > 5% of responses finish_reason=length (after >= 200 responses)
On abort: SIGTERM to the cell's process group, SIGKILL after 20 s, no further cells; exit code 3.
Writes runs/grid_driver.log (status every 60 s). Never prints the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
LEDGER = RUNS / "openrouter_ledger.jsonl"
LOG = RUNS / "grid_driver.log"


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def call_weight(r: int) -> float:
    """Smoke cost model per call in round r (micro-$): prompt 686 + 550 (r-1) tokens (cap 14000)."""
    return min(686 + 550 * (r - 1), 14000) * 0.0142 + 350 * 0.0445


class Tail:
    """Incremental JSONL reader over a growing file."""

    def __init__(self, path: Path) -> None:
        self.path, self.pos, self.buf = path, 0, ""

    def new(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            f.seek(self.pos)
            chunk = f.read()
            self.pos = f.tell()
        self.buf += chunk
        lines = self.buf.split("\n")
        self.buf = lines.pop()
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
        return out


def mem_available_gb() -> float:
    for ln in open("/proc/meminfo"):
        if ln.startswith("MemAvailable"):
            return int(ln.split()[1]) / 1024 / 1024
    return 99.0


def count_rg() -> int:
    n = 0
    for p in Path("/proc").iterdir():
        if p.name.isdigit():
            try:
                if (p / "comm").read_text().strip() == "rg":
                    n += 1
            except OSError:
                pass
    return n


def ledger_total() -> float:
    t = 0.0
    for ln in open(LEDGER, encoding="utf-8"):
        try:
            t += float(json.loads(ln).get("cost_usd") or 0.0)
        except ValueError:
            pass
    return t


class Cell:
    def __init__(self, name: str, cap: float, branches: int, seeds: int, rounds: int) -> None:
        self.name, self.cap, self.branches, self.seeds, self.rounds = name, cap, branches, seeds, rounds
        self.run_dir = RUNS / name
        per_branch = sum(10 * call_weight(r) for r in range(1, rounds + 1))
        shared = sum(10 * call_weight(r) for r in range(1, 3))           # rounds 1-2 replayed by forks
        self.w_total = seeds * (branches * per_branch - (branches - 1) * shared)
        self.tails: dict[Path, Tail] = {}
        self.ledger = Tail(LEDGER)
        self.ledger.pos = LEDGER.stat().st_size if LEDGER.exists() else 0
        self.spent = self.w_done = 0.0
        self.calls = self.errors = self.http400 = self.paid = 0
        self.resp = self.length = self.turns = self.parse_fail = 0

    def update(self) -> None:
        for d in self.ledger.new():
            if d.get("run_id") == self.name:
                self.spent += float(d.get("cost_usd") or 0.0)
        games = self.run_dir / "games"
        if not games.is_dir():
            return
        for g in games.iterdir():
            for fn in ("llm_calls.jsonl", "events.jsonl"):
                p = g / fn
                if p not in self.tails:
                    self.tails[p] = Tail(p)
                for d in self.tails[p].new():
                    if fn == "llm_calls.jsonl":
                        self._call(d)
                    elif d.get("type") == "turn":
                        self.turns += 1
                        self.parse_fail += not d["data"].get("parse_ok", True)

    def _call(self, d: dict) -> None:
        self.calls += 1
        if d.get("error"):
            self.errors += 1
            self.http400 += "HTTP 400" in d["error"]
        r = d.get("response")
        if r:
            self.resp += 1
            self.length += r.get("finish_reason") == "length"
            if not r.get("cache_hit"):
                self.paid += 1
                self.w_done += call_weight(int(d["request"]["meta"].get("round") or 1))

    def projected(self) -> float:
        return self.spent * self.w_total / self.w_done if self.w_done else 0.0

    def status(self) -> str:
        return (f"{self.name}: spent ${self.spent:.4f} projected ${self.projected():.3f} (cap ${self.cap:.2f}) "
                f"done {self.w_done / self.w_total:.1%} calls {self.calls} paid {self.paid} errors {self.errors} "
                f"turns {self.turns} parse_fail {self.parse_fail} length {self.length}/{self.resp}")

    def abort_reason(self, ledger_stop: float) -> str | None:
        if (m := mem_available_gb()) < 15:
            return f"ram: MemAvailable {m:.1f} GB < 15"
        if (n := count_rg()) > 20:
            return f"rg: {n} rg processes > 20"
        if (t := ledger_total()) >= ledger_stop:
            return f"ledger: total ${t:.3f} >= ${ledger_stop:.2f}"
        if self.paid >= 150 and self.projected() > self.cap:
            return f"projection: ${self.projected():.3f} > cap ${self.cap:.2f}"
        if self.http400:
            return f"errors: {self.http400} HTTP 400"
        if self.calls >= 100 and self.errors / self.calls > 0.05:
            return f"errors: {self.errors}/{self.calls} calls"
        if self.turns >= 100 and self.parse_fail / self.turns > 0.10:
            return f"parse: {self.parse_fail}/{self.turns} turns"
        if self.resp >= 200 and self.length / self.resp > 0.05:
            return f"trunc: {self.length}/{self.resp} responses"
        return None


def kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", action="append", required=True)
    ap.add_argument("--seeds", type=int, required=True)
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--ledger-stop", type=float, default=5.70)
    ap.add_argument("--set", dest="sets", action="append", default=[], help="override passed to every cell")
    ap.add_argument("--run-prefix", default="", help="run id prefix (dry runs)")
    args = ap.parse_args()
    fake = any(s.startswith("roles.agent.backend=fake") for s in args.sets)
    if not fake and not os.environ.get("OPENROUTER_API_KEY"):
        log("OPENROUTER_API_KEY not set")
        return 2
    for spec in args.cell:
        name, cap, branches = spec.split(":")
        cell = Cell(args.run_prefix + name, float(cap), int(branches), args.seeds, args.rounds)
        if (r := cell.abort_reason(args.ledger_stop)) is not None:
            log(f"NOT starting {name}: {r}")
            return 3
        cmd = [sys.executable, "-m", "swarm.run", "--config", f"configs/{name}.yaml", "--run-id", cell.name,
               *args.sets]
        out = open(RUNS / f"{cell.name}.log", "a")
        proc = subprocess.Popen(cmd, cwd=REPO, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        log(f"START {cell.name} pid/pgid {proc.pid} cap ${cell.cap:.2f} seeds {args.seeds} rounds {args.rounds}")
        last = 0.0
        while proc.poll() is None:
            time.sleep(10)
            cell.update()
            reason = cell.abort_reason(args.ledger_stop)
            if reason:
                log(f"ABORT {name}: {reason}; {cell.status()}")
                kill_group(proc)
                return 3
            if time.time() - last >= 60:
                log(cell.status())
                last = time.time()
        cell.update()
        log(f"END {name} exit {proc.returncode}; {cell.status()}")
        if proc.returncode != 0:
            return 4
    log("GRID DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
