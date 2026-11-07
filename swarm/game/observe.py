"""Agent observations (WP1b): the ONLY path from GameState (truth) to what an agent may know.

`observe(state, agent, cfg, turn_idx)` builds an `Observation` field by field from whitelisted view
models. No truth field (forged, true_sender, intervention ids, tamper flags, copy ids, refs, release
turns) is ever copied, and forged messages render exactly like real ones (the shown sender).

Timing (all by global turn index t; `prev` = AgentState.last_obs_turn, -1 before the first one):
- A record stamped at slot s is first visible to observations with index > s.
- inbox / board / notices: "new since your previous observation" = prev <= s < t.
  Notices with `deliver_from_turn` d use schema.release_visible(d, t, prev) instead (shown once).
- view_log: the rolling window schema.log_visible(s, t, window_turns) (window = n_agents by default)
  over give / board_post (+ dm_meta / dm under actions_msg_meta / full; never under actions_only).
- Defects (D12): `public` -> in the rolling window like any action. `victim_only` -> never in the log.
  `delayed` -> every viewer gets the line once, at release (release_visible). `victim_then_delayed`
  -> every viewer except the victim gets it once at release (the victim got a notice at t_d+1).
  Wrong defects follow the same path (ok=False on the line).
- content="none": empty log, grep disabled.

`grep_log` searches the agent's VISIBLE log history: the union of the windows of all its past
observations (`obs_turns`, tracked by the engine) plus released defect lines, matched as a
case-insensitive literal substring of the rendered line (plus " #<info_id>").

The engine calls `mark_observed(state, agent, t)` after each observation; `observe` itself is pure.
"""

from __future__ import annotations

from collections.abc import Sequence

from swarm.config import GameCfg
from swarm.context.base import render_log_line
from swarm.game.rules import open_needs, score
from swarm.schema import (
    ActionRecord,
    AgentId,
    AgentMessageView,
    GameState,
    GrepResult,
    KeyView,
    LogLine,
    Message,
    NoticeView,
    Observation,
    PinnedFacts,
    log_visible,
    release_visible,
)


def _new_since(stamp: int, viewer_turn: int, prev: int) -> bool:
    return prev <= stamp < viewer_turn


def _msg_view(m: Message, cfg: GameCfg) -> AgentMessageView:
    text = m.text
    if cfg.view_log.reveal_provenance and m.forged:          # ablation only
        text = "[FORGED] " + text
    return AgentMessageView(msg_id=m.msg_id, channel=m.channel, sender=m.sender_shown,
                            receiver=m.receiver, text=text)


def pinned_facts(state: GameState, agent: AgentId, cfg: GameCfg) -> PinnedFacts:
    """Identity, needs, holdings (with key ids, D15), score. Rebuilt from state every turn."""
    s = state.agents[agent]
    holdings = sorted((KeyView(info_id=k.info_id, key=k.key) for k in s.keys),
                      key=lambda kv: (kv.info_id, kv.key))
    return PinnedFacts(
        agent=agent, round=state.round, max_rounds=cfg.max_rounds,
        needs_open=list(open_needs(state, agent)), needs_burned=list(s.burned), needs_lost=list(s.lost),
        holdings=holdings, can_give=sorted({k.info_id for k in s.keys}), score=score(state, agent),
        peers=sorted(a for a in state.agents if a != agent), won=s.won_round is not None,
    )


# ------------------------------------------------------------------ view_log
def _line(rec: ActionRecord, state: GameState, cfg: GameCfg) -> LogLine | None:
    """Render one ActionRecord as a LogLine under cfg.view_log (None = not shown at all)."""
    vl = cfg.view_log
    hidden = vl.actor_identity == "hidden"
    if rec.kind == "defect":
        ident = vl.defect_actor_identity or vl.actor_identity
        return LogLine(round=rec.round, kind="defect",
                       actor=None if ident == "hidden" else rec.actor,
                       target=rec.target, info_id=rec.info_id, ok=rec.ok)
    if rec.kind == "give":
        return LogLine(round=rec.round, kind="give", actor=None if hidden else rec.actor,
                       target=rec.target, info_id=rec.info_id)
    msg = _msg_by_id(state, rec.msg_id)
    if msg is None:
        return None
    sender = None if hidden else msg.sender_shown          # never the true sender
    if rec.kind == "board_post":
        return LogLine(round=rec.round, kind="board_post", actor=sender, text=msg.text)
    if rec.kind == "dm":
        if vl.content == "actions_msg_meta":
            return LogLine(round=rec.round, kind="dm_meta", actor=sender, target=msg.receiver)
        if vl.content == "full":
            text = ("[FORGED] " + msg.text) if (vl.reveal_provenance and msg.forged) else msg.text
            return LogLine(round=rec.round, kind="dm", actor=sender, target=msg.receiver, text=text)
        return None                                         # actions_only: no message events at all
    return None


def _msg_by_id(state: GameState, msg_id: str | None) -> Message | None:
    if msg_id is None:
        return None
    for m in state.messages:
        if m.msg_id == msg_id:
            return m
    return None


def _defect_shown_by_release(rec: ActionRecord, viewer: AgentId, cfg: GameCfg) -> bool:
    """Is this defect record shown to `viewer` via the release rule (not the rolling window)?"""
    mode = cfg.view_log.defect_visibility
    if mode == "delayed":
        return True
    if mode == "victim_then_delayed":
        return viewer != rec.target
    return False


def _window_record(rec: ActionRecord, cfg: GameCfg) -> bool:
    """Records that use the rolling-window rule."""
    if rec.kind == "defect":
        return cfg.view_log.defect_visibility == "public"
    return True


def view_log(state: GameState, viewer: AgentId, cfg: GameCfg, viewer_turn: int,
             prev_obs_turn: int) -> list[LogLine]:
    """The log lines `viewer` sees in the observation at `viewer_turn` (D5/D12/D16)."""
    if cfg.view_log.content == "none":
        return []
    w = cfg.window_turns
    out: list[tuple[int, int, LogLine]] = []
    for idx, rec in enumerate(state.history):
        if _window_record(rec, cfg):
            show = log_visible(rec.turn_index, viewer_turn, w)
        elif rec.release_turn is not None and _defect_shown_by_release(rec, viewer, cfg):
            show = release_visible(rec.release_turn, viewer_turn, prev_obs_turn)
        else:
            show = False
        if show:
            line = _line(rec, state, cfg)
            if line is not None:
                out.append((rec.turn_index, idx, line))
    out.sort(key=lambda x: (x[0], x[1]))
    return [ln for _, _, ln in out]


# ------------------------------------------------------------------ observe
def observe(state: GameState, agent: AgentId, cfg: GameCfg, turn_idx: int | None = None) -> Observation:
    """Build the agent-visible Observation at global slot `turn_idx` (default state.turn_index).
    Pure: does not update last_obs_turn (call mark_observed)."""
    t = state.turn_index if turn_idx is None else turn_idx
    prev = state.agents[agent].last_obs_turn
    inbox = [_msg_view(m, cfg) for m in state.messages
             if m.channel == "dm" and m.receiver == agent and _new_since(m.turn_index, t, prev)]
    board = [_msg_view(m, cfg) for m in state.messages
             if m.channel == "board" and m.sender_shown != agent and _new_since(m.turn_index, t, prev)]
    notices = []
    for n in state.notices:
        if n.agent != agent:
            continue
        due = (release_visible(n.deliver_from_turn, t, prev) if n.deliver_from_turn is not None
               else _new_since(n.turn_index, t, prev))
        if due:
            notices.append(NoticeView(kind=n.kind, text=n.text))
    return Observation(agent=agent, round=state.round, turn_index=t, pinned=pinned_facts(state, agent, cfg),
                       inbox=inbox, board=board, log=view_log(state, agent, cfg, t, prev), notices=notices)


def mark_observed(state: GameState, agent: AgentId, turn_idx: int) -> None:
    """Record that `agent` observed at `turn_idx` (drives the 'new since last observation' rules)."""
    state.agents[agent].last_obs_turn = turn_idx


# ------------------------------------------------------------------ grep_log
def grep_text(line: LogLine) -> str:
    """The searchable text of a line: its rendering plus ' #<info_id>' (D15 key ids)."""
    s = render_log_line(line)
    return s + (f" #{line.info_id}" if line.info_id is not None else "")


def visible_history(state: GameState, viewer: AgentId, cfg: GameCfg, obs_turns: Sequence[int]) -> list[LogLine]:
    """Union of everything view_log showed `viewer` at the observations `obs_turns` (ascending, the
    current one included), with defect releases evaluated as of the latest observation."""
    if cfg.view_log.content == "none" or not obs_turns:
        return []
    w = cfg.window_turns
    now = max(obs_turns)
    out: list[tuple[int, int, LogLine]] = []
    for idx, rec in enumerate(state.history):
        if _window_record(rec, cfg):
            show = any(log_visible(rec.turn_index, t, w) for t in obs_turns)
        elif rec.release_turn is not None and _defect_shown_by_release(rec, viewer, cfg):
            show = rec.release_turn <= now
        else:
            show = False
        if show:
            line = _line(rec, state, cfg)
            if line is not None:
                out.append((rec.turn_index, idx, line))
    out.sort(key=lambda x: (x[0], x[1]))
    return [ln for _, _, ln in out]


def grep_log(state: GameState, viewer: AgentId, cfg: GameCfg, pattern: str, obs_turns: Sequence[int],
             rounds: int | None = None) -> GrepResult:
    """Case-insensitive LITERAL substring search over the viewer's visible log history (D5).
    Patterns longer than grep_max_pattern_chars give no hits; results are capped at grep_max_results."""
    vl = cfg.view_log
    if not vl.grep_enabled or vl.content == "none" or not pattern or len(pattern) > vl.grep_max_pattern_chars:
        return GrepResult(pattern=pattern[: vl.grep_max_pattern_chars], hits=[])
    pat = pattern.lower()
    hits = [ln for ln in visible_history(state, viewer, cfg, obs_turns)
            if (rounds is None or ln.round > state.round - rounds) and pat in grep_text(ln).lower()]
    cap = vl.grep_max_results
    return GrepResult(pattern=pattern, hits=hits[-cap:], truncated=len(hits) > cap)
