"""Game rules (WP1a): `apply(state, actor, action, cfg) -> (state, event_bodies)`.

No I/O, no LLM, no randomness. The state is mutated IN PLACE (deep copies happen only at round
boundaries, in the engine) unless `copy=True`. `apply` never raises on agent input: an invalid action
returns a single `action_result` event with ok=False and leaves the state unchanged.

Timing convention: every record created here is stamped with `state.turn_index` (the slot of the
acting agent). A record is visible to observations with index STRICTLY greater than its stamp
(see game/observe.py). The engine wakes God with `state.turn_index` = the slot about to be played,
so forged messages carry the wake slot (CONTRACTS §2) and reach the receiver at its next observation
after that slot.

Rules (ARCHITECTURE_v2 §1, D1-D4, D12, D13):
- send_message / post_board: always succeed for a valid peer; text truncated to max_message_chars.
- give_key: the actor must hold a copy of info_id; one copy moves to `to`. Only Give transfers keys.
- defect(target, info_id): CORRECT iff info_id is one of target's open needs (not burned, not lost).
  Correct: the target's need is burned; the actor gains per `defect_gain` (mint a new copy / steal a
  copy from another holder / none). Wrong: the actor pays `wrong_defect_penalty` (lose_need: its
  first open need is lost permanently; delay: no turns until round + delay_n). A target that has
  won cannot be defected against (ok=False, no penalty).
- Win (D3): holds a key for every open need and has at least one open need. won_round is sticky.
  Score = held open needs / len(needs) (burned and lost needs count 0).
"""

from __future__ import annotations

from swarm.config import GameCfg
from swarm.rng import make_msg_id
from swarm.schema import (
    GOD,
    Action,
    ActionRecord,
    ActionResultData,
    AgentId,
    BurnData,
    DefectAction,
    EventBody,
    GameState,
    GiveKey,
    GrepLog,
    InfoId,
    KeyCopy,
    KeyTransferData,
    Message,
    MessageData,
    Noop,
    Notice,
    NoticeData,
    Phase,
    PostBoard,
    SendMessage,
    WinData,
    defect_release_turn,
)

Events = list[EventBody]


# ------------------------------------------------------------------ scoring helpers
def open_needs(state: GameState, agent: AgentId) -> list[InfoId]:
    """Needs that are neither burned nor lost."""
    s = state.agents[agent]
    return [i for i in s.needs if i not in s.burned and i not in s.lost]


def held_infos(state: GameState, agent: AgentId) -> set[InfoId]:
    return {kc.info_id for kc in state.agents[agent].keys}


def score(state: GameState, agent: AgentId) -> float:
    """Held open needs / total needs (D3)."""
    s = state.agents[agent]
    if not s.needs:
        return 0.0
    held = held_infos(state, agent)
    return sum(1 for i in open_needs(state, agent) if i in held) / len(s.needs)


def is_winning(state: GameState, agent: AgentId) -> bool:
    on = open_needs(state, agent)
    return bool(on) and set(on) <= held_infos(state, agent)


def is_done(state: GameState, agent: AgentId) -> bool:
    """Done = has won, or has no open need left (nothing more to gain)."""
    return state.agents[agent].won_round is not None or not open_needs(state, agent)


def _ev(state: GameState, actor: str, data, phase: Phase = "resolve") -> EventBody:
    return EventBody(round=state.round, turn_index=state.turn_index, phase=phase, actor=actor, data=data)


def notice(state: GameState, agent: AgentId, kind, text: str, *, ref: str | None = None,
           deliver_from_turn: int | None = None) -> EventBody:
    """Queue a Notice for `agent` (stamped state.round / state.turn_index) and return its event body."""
    n = Notice(agent=agent, round=state.round, turn_index=state.turn_index, kind=kind, text=text,
               ref=ref, deliver_from_turn=deliver_from_turn)
    state.notices.append(n)
    return _ev(state, "SYSTEM", NoticeData(notice=n))


_notice = notice   # the original private name (rules-internal callers)


def update_win(state: GameState, agent: AgentId) -> Events:
    """Set won_round (sticky) if the agent now satisfies D3; returns win + notice events."""
    s = state.agents[agent]
    if s.won_round is not None or not is_winning(state, agent):
        return []
    s.won_round = state.round
    return [_ev(state, "SYSTEM", WinData(agent=agent, score=score(state, agent))),
            _notice(state, agent, "won", "You now hold a key for every one of your remaining needs. "
                                         "You have won.")]


# ------------------------------------------------------------------ messages (shared with God)
def deliver_message(state: GameState, *, channel: str, sender_shown: AgentId, text: str,
                    receiver: AgentId | None = None, true_sender: str | None = None,
                    forged: bool = False, intervention_id: str | None = None,
                    phase: Phase = "resolve") -> tuple[Message, Events]:
    """The way an AGENT's DM/board post enters the game (also usable for forged messages).
    NOTE: adversary.powers.apply_message_fraud builds its Message itself with the same msg_id scheme
    and stamp (state.round, state.turn_index) but appends NO ActionRecord. That is invisible to
    agents (view_log renders messages from state.messages) but state.history differs for forgeries."""
    msg = Message(msg_id=make_msg_id(state.game_id, len(state.messages)), round=state.round,
                  turn_index=state.turn_index, channel=channel, sender_shown=sender_shown,
                  true_sender=true_sender or sender_shown, receiver=receiver, text=text,
                  forged=forged, intervention_id=intervention_id)
    state.messages.append(msg)
    state.history.append(ActionRecord(turn_index=state.turn_index, round=state.round,
                                      kind="dm" if channel == "dm" else "board_post",
                                      actor=sender_shown, target=receiver, msg_id=msg.msg_id))
    return msg, [_ev(state, GOD if forged else sender_shown, MessageData(message=msg), phase)]


# ------------------------------------------------------------------ apply
def _fail(state: GameState, actor: AgentId, action: Action, reason: str) -> Events:
    return [_ev(state, actor, ActionResultData(agent=actor, action=action, ok=False, reason=reason))]


def _ok(state: GameState, actor: AgentId, action: Action) -> EventBody:
    return _ev(state, actor, ActionResultData(agent=actor, action=action, ok=True))


def _name(actor: AgentId, cfg: GameCfg, *, defect: bool = False) -> str:
    ident = cfg.view_log.actor_identity
    if defect and cfg.view_log.defect_actor_identity is not None:
        ident = cfg.view_log.defect_actor_identity
    return actor if ident == "shown" else "Someone"


def apply(state: GameState, actor: AgentId, action: Action, cfg: GameCfg, *,
          copy: bool = False) -> tuple[GameState, Events]:
    """Apply one action of `actor`. Returns (state, event bodies). Never raises on agent input.
    The first event is always the action_result."""
    if copy:
        state = state.model_copy(deep=True)
    if actor not in state.agents:
        return state, _fail(state, actor, action, "unknown_actor")
    try:
        if isinstance(action, SendMessage):
            return state, _send(state, actor, action, cfg)
        if isinstance(action, PostBoard):
            text = action.text[: cfg.max_message_chars]
            _, evs = deliver_message(state, channel="board", sender_shown=actor, text=text)
            return state, [_ok(state, actor, action), *evs]
        if isinstance(action, GiveKey):
            return state, _give(state, actor, action, cfg)
        if isinstance(action, DefectAction):
            return state, _defect(state, actor, action, cfg)
        if isinstance(action, Noop):
            return state, [_ok(state, actor, action)]
        if isinstance(action, GrepLog):
            return state, _fail(state, actor, action, "grep_handled_by_engine")
    except (KeyError, ValueError, IndexError) as e:  # defensive: rule closure
        return state, _fail(state, actor, action, f"error:{type(e).__name__}")
    return state, _fail(state, actor, action, "unknown_action")


def _peer_error(state: GameState, actor: AgentId, other: AgentId) -> str | None:
    if other not in state.agents:
        return "unknown_agent"
    if other == actor:
        return "self_target"
    return None


def _send(state: GameState, actor: AgentId, a: SendMessage, cfg: GameCfg) -> Events:
    err = _peer_error(state, actor, a.to)
    if err:
        return _fail(state, actor, a, err)
    _, evs = deliver_message(state, channel="dm", sender_shown=actor, receiver=a.to,
                             text=a.text[: cfg.max_message_chars])
    return [_ok(state, actor, a), *evs]


def _give(state: GameState, actor: AgentId, a: GiveKey, cfg: GameCfg) -> Events:
    err = _peer_error(state, actor, a.to)
    if err:
        return _fail(state, actor, a, err)
    src = state.agents[actor]
    idx = next((j for j, kc in enumerate(src.keys) if kc.info_id == a.info_id), None)
    if idx is None:
        return _fail(state, actor, a, "no_such_key")
    kc = src.keys.pop(idx)
    state.agents[a.to].keys.append(kc)
    state.history.append(ActionRecord(turn_index=state.turn_index, round=state.round, kind="give",
                                      actor=actor, target=a.to, info_id=a.info_id))
    evs = [_ok(state, actor, a),
           _ev(state, actor, KeyTransferData(copy_id=kc.copy_id, info_id=kc.info_id, from_agent=actor,
                                             to_agent=a.to, cause="give")),
           _notice(state, a.to, "gift_received",
                   f"{_name(actor, cfg)} gave you a key for info #{kc.info_id} (key {kc.key}).")]
    return evs + update_win(state, a.to)


def _defect(state: GameState, actor: AgentId, a: DefectAction, cfg: GameCfg) -> Events:
    err = _peer_error(state, actor, a.target)
    if err:
        return _fail(state, actor, a, err)
    tgt = state.agents[a.target]
    if tgt.won_round is not None:
        return _fail(state, actor, a, "target_won")
    vl = cfg.view_log
    n = cfg.n_agents
    t_d = state.turn_index
    correct = a.info_id in open_needs(state, a.target)
    mode = vl.defect_visibility
    release = defect_release_turn(t_d, vl.defect_delay_rounds, n) \
        if mode in ("delayed", "victim_then_delayed") else None
    # victim-timed notices: next observation (victim_* / public) or at release (delayed)
    victim_dft = release if mode == "delayed" else None
    who = _name(actor, cfg, defect=True)
    me = state.agents[actor]
    evs: Events = [_ok(state, actor, a)]
    lost: InfoId | None = None
    delayed_until: int | None = None
    if correct:
        tgt.burned.append(a.info_id)
        evs.append(_notice(state, a.target, "burned",
                           f"{who} burned your need for info #{a.info_id}: you can never get info "
                           f"#{a.info_id} now.", ref=f"burn:{t_d}", deliver_from_turn=victim_dft))
        gain_text = ""
        if cfg.defect_gain == "mint":
            n_copies = sum(1 for s in state.agents.values() for k in s.keys if k.info_id == a.info_id)
            kc = KeyCopy(copy_id=f"m{a.info_id}-{t_d}-{n_copies}", info_id=a.info_id,
                         key=_key_value(state, a.info_id), origin="defect_mint")
            me.keys.append(kc)
            evs.append(_ev(state, actor, KeyTransferData(copy_id=kc.copy_id, info_id=a.info_id,
                                                         from_agent=None, to_agent=actor,
                                                         cause="defect_mint")))
            gain_text = f" You gained a key for info #{a.info_id} (key {kc.key})."
        elif cfg.defect_gain == "steal":
            holder = next((h for h in sorted(state.agents) if h != actor
                           and any(k.info_id == a.info_id for k in state.agents[h].keys)), None)
            if holder is not None:
                hk = state.agents[holder].keys
                kc = hk.pop(next(j for j, k in enumerate(hk) if k.info_id == a.info_id))
                me.keys.append(kc)
                evs.append(_ev(state, actor, KeyTransferData(copy_id=kc.copy_id, info_id=a.info_id,
                                                             from_agent=holder, to_agent=actor,
                                                             cause="defect_steal")))
                evs.append(_notice(state, holder, "system",
                                   f"{who} took your key for info #{a.info_id}.",
                                   ref=f"steal:{t_d}", deliver_from_turn=victim_dft))
                gain_text = f" You took a key for info #{a.info_id} (key {kc.key})."
        evs.append(_notice(state, actor, "defect_result",
                           f"Your burn of info #{a.info_id} on {a.target} was correct.{gain_text}"))
    else:
        evs.append(_notice(state, a.target, "defect_attempt",
                           f"{who} tried to burn info #{a.info_id} of yours; it had no effect on you.",
                           ref=f"burn:{t_d}", deliver_from_turn=victim_dft))
        if cfg.wrong_defect_penalty == "lose_need":
            on = open_needs(state, actor)
            if on:
                lost = on[0]
                me.lost.append(lost)
            pen = f" You permanently lost your need for info #{lost}." if lost is not None else ""
        else:
            delayed_until = state.round + cfg.delay_n
            me.delayed_until_round = delayed_until
            pen = f" You are delayed: no turns until after round {delayed_until}."
        evs.append(_notice(state, actor, "defect_result",
                           f"Your burn of info #{a.info_id} on {a.target} was wrong.{pen}"))
    state.history.append(ActionRecord(turn_index=t_d, round=state.round, kind="defect", actor=actor,
                                      target=a.target, info_id=a.info_id, ok=correct,
                                      release_turn=release))
    evs.append(_ev(state, actor, BurnData(
        actor=actor, target=a.target, info_id=a.info_id, correct=correct,
        penalty="none" if correct else cfg.wrong_defect_penalty, lost_info_id=lost,
        delayed_until_round=delayed_until, gain=cfg.defect_gain, release_turn=release)))
    for ag in (actor, a.target):
        evs += update_win(state, ag)
    return evs


def _key_value(state: GameState, info_id: InfoId) -> int:
    """The secret key value of an info (all copies share it). Minted copies reuse it."""
    for s in state.agents.values():
        for kc in s.keys:
            if kc.info_id == info_id:
                return kc.key
    return 0
