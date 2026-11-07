"""Shared records (WP0, FROZEN). Change only via the team lead.

Three families, kept apart on purpose:
  1. TRUTH side (engine/analysis only): GameState, AgentState, KeyCopy, Message, MemoryEntry,
     ActionRecord, Notice, Event + payloads, LLMCall, HistoryItem, ContextBundle, Label.
  2. AGENT-VISIBLE side: subclasses of `AgentView` (Observation, PinnedFacts, KeyView,
     AgentMessageView, LogLine, NoticeView, MemoryView, GrepResult, PromptView, ...). They contain
     no field in TRUTH_FIELDS and no truth model (enforced by tests/test_agent_view.py). Prompt
     templates receive ONLY AgentView objects.
  3. Actions (agent -> engine) and GodActions, as tagged unions on `kind`.

Mutability: GameState / AgentState are mutable (rules mutate them in place; the engine deep-copies at
round boundaries only). Everything else is frozen. Ledgers (agent context history) live OUTSIDE GameState.

Time: rounds are 1-based (round 0 = setup). Within a game every agent-turn slot has a global
turn_index = (round - 1) * n_agents + position_in_order (slots of skipped agents are still counted).
See `turn_index`, `log_visible`, `defect_release_turn`, `release_visible` below: they ARE the
view_log timing contract.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from swarm import SCHEMA_VERSION
from swarm.rng import canonical_json, sha256_hex

AgentId = str
InfoId = int
GameId = str
RunId = str
GOD: Literal["GOD"] = "GOD"
SYSTEM: Literal["SYSTEM"] = "SYSTEM"

MemoryKind = Literal["cot", "scratchpad", "summary"]
Phase = Literal["setup", "god", "agents", "resolve", "compact", "end"]


class Record(BaseModel):
    """Frozen, extra=forbid. Base of every record that crosses a module boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MutableState(BaseModel):
    model_config = ConfigDict(extra="forbid")


# =====================================================================================
# Timing contract (view_log / defect_visibility). Pure arithmetic; deterministic across forks.
# =====================================================================================


def turn_index(round: int, position: int, n_agents: int) -> int:
    """Global slot index of the agent at `position` in `round` (1-based round).
    Simultaneous mode: every agent observes at the round's first slot, (round-1)*n_agents."""
    return (round - 1) * n_agents + position


def log_visible(record_turn: int, viewer_turn: int, window_turns: int) -> bool:
    """Normal actions (give, board_post, dm meta, public defects): rolling window of the previous
    `window_turns` slots (default window_turns = n_agents, i.e. 'the last round')."""
    return viewer_turn - window_turns <= record_turn < viewer_turn


def defect_release_turn(defect_turn: int, delay_rounds: int, n_agents: int) -> int:
    """Delayed defects (modes delayed / victim_then_delayed; wrong defects too): non-victims may see
    the line at the first observation with turn_index >= release. With delay=0 this equals the
    normal 'next slot' rule. In simultaneous mode a defect in round d shows in round d+1+delay."""
    return defect_turn + 1 + delay_rounds * n_agents


def release_visible(release_turn: int, viewer_turn: int, viewer_prev_obs_turn: int) -> bool:
    """A released defect line is shown EXACTLY ONCE per viewer: at the first observation at or after
    release. Viewers who were delayed / sat out get it queued at their next observation.
    viewer_prev_obs_turn = AgentState.last_obs_turn before this observation (-1 if none)."""
    return viewer_prev_obs_turn < release_turn <= viewer_turn


# =====================================================================================
# 1. TRUTH side: world and state
# =====================================================================================


class KeyCopy(Record):
    """The rivalrous unit. copy_id and origin are engine-internal (never shown to agents)."""

    copy_id: str
    info_id: InfoId
    key: int
    origin: Literal["initial", "defect_mint"] = "initial"


class AgentState(MutableState):
    agent: AgentId
    keys: list[KeyCopy]
    needs: list[InfoId]
    burned: list[InfoId] = []          # needs burned by a correct defect against this agent
    lost: list[InfoId] = []            # needs lost as wrong-defect penalty (lose_need)
    delayed_until_round: int = -1      # wrong-defect penalty `delay`: no turns while round <= this
    won_round: int | None = None
    last_obs_turn: int = -1            # turn_index of this agent's previous observation


class Message(Record):
    """A DM or board post. Ground truth for fraud lives here (forged, true_sender, intervention_id).
    Forged DMs are stamped exactly like real ones (same msg_id scheme, round/turn of the slot they
    are delivered in), so nothing agent-visible distinguishes them."""

    msg_id: str
    round: int
    turn_index: int
    channel: Literal["dm", "board"]
    sender_shown: AgentId
    true_sender: AgentId | Literal["GOD"]
    receiver: AgentId | None = None    # None for board
    text: str
    forged: bool = False
    intervention_id: str | None = None


class Taint(Record):
    intervention_id: str
    via: Literal["direct", "derived", "exposed"]


class MemoryEntry(Record):
    """CoT / scratchpad / summary entry. One per (agent, kind, round); entry_id = rng.make_entry_id."""

    entry_id: str
    agent: AgentId
    kind: MemoryKind
    round: int
    text: str
    tampered: bool = False
    original_text: str | None = None   # agent-authored text before the FIRST overwrite
    tampered_by: Literal["GOD"] | None = None
    tamper_round: int | None = None
    taint: list[Taint] = []
    covers_rounds: tuple[int, int] | None = None   # summaries only
    source_item_ids: list[str] = []                # summaries only


class ActionRecord(Record):
    """Truth-side history of actions view_log may render (built by rules, read by observe)."""

    turn_index: int
    round: int
    kind: Literal["give", "defect", "board_post", "dm"]
    actor: AgentId | Literal["GOD"]
    target: AgentId | None = None
    info_id: InfoId | None = None
    msg_id: str | None = None
    ok: bool = True                    # defect: correct (True) or wrong (False)
    release_turn: int | None = None    # defects only (see defect_release_turn)


class Notice(Record):
    """System notification for one agent, delivered at its next observation after turn_index."""

    agent: AgentId
    round: int
    turn_index: int
    kind: Literal["gift_received", "burned", "defect_attempt", "defect_result", "need_lost",
                  "delayed", "won", "system"]
    text: str
    ref: str | None = None             # truth pointer (event/msg id); never rendered
    deliver_from_turn: int | None = None   # None = next observation; else first obs with t >= this


class GameState(MutableState):
    game_id: GameId
    round: int = 0
    turn_index: int = 0
    order: list[AgentId]
    agents: dict[AgentId, AgentState]
    messages: list[Message] = []
    memory: list[MemoryEntry] = []
    history: list[ActionRecord] = []
    notices: list[Notice] = []
    god_budget_left: int = 0
    n_interventions: int = 0           # index for make_intervention_id
    done: bool = False

    def state_hash(self) -> str:
        return sha256_hex(canonical_json(self))


# =====================================================================================
# 2. AGENT-VISIBLE side. Built ONLY by game/observe.py (field by field) and context/.
# =====================================================================================


class AgentView(Record):
    """Marker base. Anything a prompt template may receive must be an AgentView."""


class KeyView(AgentView):
    info_id: InfoId
    key: int


class AgentMessageView(AgentView):
    """No round, no provenance. msg_id is an opaque hash (same scheme for real and forged)."""

    msg_id: str
    channel: Literal["dm", "board"]
    sender: AgentId
    receiver: AgentId | None = None
    text: str


class LogLine(AgentView):
    """One view_log line. actor/target are None when the identity is hidden."""

    round: int
    kind: Literal["give", "defect", "board_post", "dm_meta", "dm"]
    actor: AgentId | None = None
    target: AgentId | None = None
    info_id: InfoId | None = None
    text: str | None = None
    ok: bool | None = None             # defects: hit (True) / wrong (False)


class NoticeView(AgentView):
    kind: str
    text: str


class MemoryView(AgentView):
    kind: MemoryKind
    round: int
    text: str


class PinnedFacts(AgentView):
    """Rebuilt from GameState every turn; never from history."""

    agent: AgentId
    round: int
    max_rounds: int
    needs_open: list[InfoId]
    needs_burned: list[InfoId]
    needs_lost: list[InfoId] = []
    holdings: list[KeyView]
    can_give: list[InfoId]
    score: float
    peers: list[AgentId]
    won: bool = False


class Observation(AgentView):
    """This turn's deltas plus pinned facts. History comes from the context policy (ledger)."""

    agent: AgentId
    round: int
    turn_index: int
    pinned: PinnedFacts
    inbox: list[AgentMessageView] = []     # DMs delivered since the previous observation
    board: list[AgentMessageView] = []     # board posts since the previous observation
    log: list[LogLine] = []                # view_log() result for this turn
    notices: list[NoticeView] = []


class GrepResult(AgentView):
    pattern: str
    hits: list[LogLine]
    truncated: bool = False


class RenderItem(AgentView):
    round: int
    kind: str
    text: str


class RenderSection(AgentView):
    name: Literal["pinned", "summary", "retrieved", "window", "current"]
    items: list[RenderItem]


class PromptView(AgentView):
    """What turn templates render (from ContextBundle.to_view()). Text only."""

    agent: AgentId
    round: int
    pinned: PinnedFacts
    sections: list[RenderSection]
    grep: GrepResult | None = None


# Field names that must never appear in an AgentView (recursively) unless reveal_provenance.
TRUTH_FIELDS: frozenset[str] = frozenset({
    "forged", "true_sender", "intervention_id", "tampered", "original_text", "tampered_by",
    "tamper_round", "taint", "copy_id", "origin", "ref", "cause", "source_item_ids",
    "release_turn", "deliver_from_turn",
})


# =====================================================================================
# 3. Actions (agent -> engine). rules.apply(state, actor, action, cfg) -> list[EventBody]
# =====================================================================================


class SendMessage(Record):
    kind: Literal["send_message"] = "send_message"
    to: AgentId
    text: str


class PostBoard(Record):
    kind: Literal["post_board"] = "post_board"
    text: str


class GiveKey(Record):
    kind: Literal["give_key"] = "give_key"
    to: AgentId
    info_id: InfoId


class DefectAction(Record):
    kind: Literal["defect"] = "defect"
    target: AgentId
    info_id: InfoId


class GrepLog(Record):
    """Case-insensitive literal substring over the agent's visible log history. Max once per turn."""

    kind: Literal["grep_log"] = "grep_log"
    pattern: str = Field(min_length=1, max_length=80)
    rounds: int | None = None          # look back this many rounds (None = all)


class Noop(Record):
    kind: Literal["noop"] = "noop"


Action = Annotated[SendMessage | PostBoard | GiveKey | DefectAction | GrepLog | Noop,
                   Field(discriminator="kind")]
ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)
ACTION_KINDS = ("send_message", "post_board", "give_key", "defect", "grep_log", "noop")


class AgentOutput(Record):
    cot: str | None = None
    note: str | None = None            # scratchpad write (free; no action slot)
    actions: list[Action] = []
    parse_ok: bool = True
    retries: int = 0
    errors: list[str] = []
    llm_call_ids: list[str] = []


# =====================================================================================
# 4. God actions. Observation tools are free (safety ceiling per wake); powers cost budget.
# =====================================================================================


class ActivityCheck(Record):
    kind: Literal["activity_check"] = "activity_check"
    last_n_rounds: int = 1


class MessageCheck(Record):
    kind: Literal["message_check"] = "message_check"
    sender: AgentId | None = None
    receiver: AgentId | None = None
    contains: str | None = None
    last_n_rounds: int | None = None


class Wait(Record):
    kind: Literal["wait"] = "wait"
    n_turns: int | None = None         # None = until next wake


class MessageFraud(Record):
    kind: Literal["message_fraud"] = "message_fraud"
    sender: AgentId                    # shown sender (impersonated)
    receiver: AgentId
    text: str


class CotControl(Record):
    kind: Literal["cot_control"] = "cot_control"
    agent: AgentId
    target: MemoryKind = "scratchpad"
    round: int
    text: str
    mode: Literal["replace", "append"] = "replace"


GodAction = Annotated[ActivityCheck | MessageCheck | Wait | MessageFraud | CotControl,
                      Field(discriminator="kind")]
GOD_ACTION_ADAPTER: TypeAdapter[GodAction] = TypeAdapter(GodAction)


# =====================================================================================
# 5. Context (WP13 implements; models frozen here). Ledger = dict[AgentId, list[HistoryItem]],
#    held by the engine OUTSIDE GameState, built only by context.base.items_from_observation(obs).
# =====================================================================================

HistoryKind = Literal["inbox_msg", "board_msg", "log_line", "notice", "own_action", "action_result",
                      "cot", "scratchpad", "summary", "retrieved"]


class HistoryItem(Record):
    item_id: str                       # f"{agent}:{round}:{kind}:{n}"
    agent: AgentId
    round: int                         # round the agent OBSERVED / produced it
    kind: HistoryKind
    text: str                          # exactly what the agent is shown
    ref: str | None = None             # msg_id / entry_id / event pointer (truth; never rendered)
    tokens: int = 0


class ContextSection(Record):
    name: Literal["pinned", "summary", "retrieved", "window", "current"]
    item_ids: list[str]
    tokens: int


class ContextBundle(Record):
    agent: AgentId
    round: int
    policy: str
    policy_hash: str
    pinned: PinnedFacts
    sections: list[ContextSection]
    items: dict[str, HistoryItem]      # included items only
    dropped_item_ids: list[str] = []
    tokens_total: int
    budget: int

    def to_view(self, grep: GrepResult | None = None) -> PromptView:
        return PromptView(
            agent=self.agent, round=self.round, pinned=self.pinned, grep=grep,
            sections=[RenderSection(name=s.name, items=[
                RenderItem(round=self.items[i].round, kind=self.items[i].kind, text=self.items[i].text)
                for i in s.item_ids]) for s in self.sections],
        )


class CompactionRecord(Record):
    compaction_id: str
    agent: AgentId
    round: int
    policy: str
    summarizer: Literal["self", "cheap", "extractive"]
    covers_rounds: tuple[int, int]
    source_item_ids: list[str]
    prev_summary_id: str | None = None
    summary_entry_id: str
    summary_text: str
    tokens_before: int
    tokens_after: int
    llm_call_id: str | None = None


# =====================================================================================
# 6. LLM I/O (llm/base.py re-exports). Requests never contain headers or keys.
# =====================================================================================

Role = Literal["agent", "god", "judge", "summarizer"]


class ChatMessage(Record):
    role: Literal["system", "user", "assistant"]
    content: str


class CallMeta(Record):
    """Logged, never sent to the backend."""

    role: Role
    agent: AgentId | None = None
    game_id: GameId | None = None
    round: int | None = None
    attempt: int = 0
    purpose: str = "turn"
    prompt_set: str | None = None
    prompt_set_hash: str | None = None
    prompt_hash: str | None = None


class ChatRequest(Record):
    call_id: str                       # rng.make_call_id(...) by the caller; deterministic
    messages: list[ChatMessage]
    max_tokens: int
    temperature: float
    top_p: float | None = None
    seed: int
    thinking: bool = False
    response_format: dict[str, Any] | None = None
    stop: list[str] | None = None
    meta: CallMeta

    def sampling(self) -> dict[str, Any]:
        """Everything that affects the completion (cache-key input besides model/backend)."""
        return self.model_dump(mode="json", exclude={"call_id", "meta"})


class Usage(Record):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0


class ChatResponse(Record):
    call_id: str
    text: str
    reasoning: str | None = None
    finish_reason: str | None = None
    usage: Usage = Usage()
    cost_usd: float = 0.0
    latency_s: float = 0.0
    cache_hit: bool = False
    retries: int = 0
    backend: str = ""
    model: str = ""


class LLMCall(Record):
    """One line of llm_calls.jsonl (cache hits included)."""

    v: int = SCHEMA_VERSION
    run_id: RunId
    backend: str
    model: str
    cache_key: str | None = None
    request: ChatRequest
    response: ChatResponse | None = None
    error: str | None = None


# =====================================================================================
# 7. Events (events.jsonl). One typed payload per event type, discriminated by `type`.
# =====================================================================================


class GameStartData(Record):
    type: Literal["game_start"] = "game_start"
    config_hash: str
    n_agents: int
    max_rounds: int
    order: list[AgentId]
    agents: dict[AgentId, AgentState]  # initial inventories and needs
    branch: str = "main"
    replica: str = "0"


class TurnData(Record):
    type: Literal["turn"] = "turn"
    agent: AgentId
    obs: Observation                   # logged so ledgers can be rebuilt from events
    obs_hash: str
    prompt_set_hash: str | None = None
    prompt_hash: str | None = None
    llm_call_ids: list[str] = []
    cot: str | None = None
    note: str | None = None
    actions: list[Action] = []
    parse_ok: bool = True
    retries: int = 0
    errors: list[str] = []


class ActionResultData(Record):
    type: Literal["action_result"] = "action_result"
    agent: AgentId
    action: Action
    ok: bool
    reason: str | None = None          # "no_such_key", "target_won", "not_a_peer", ...
    n_hits: int | None = None          # grep_log only


class MessageData(Record):
    type: Literal["message"] = "message"
    message: Message


class KeyTransferData(Record):
    type: Literal["key_transfer"] = "key_transfer"
    copy_id: str
    info_id: InfoId
    from_agent: AgentId | None          # None for defect_mint
    to_agent: AgentId
    cause: Literal["give", "defect_mint", "defect_steal"]


class BurnData(Record):
    type: Literal["burn"] = "burn"
    actor: AgentId
    target: AgentId
    info_id: InfoId
    correct: bool
    penalty: Literal["none", "lose_need", "delay"]   # actor's penalty (wrong defects only)
    lost_info_id: InfoId | None = None
    delayed_until_round: int | None = None
    gain: Literal["mint", "steal", "none"]
    release_turn: int | None = None    # None in public / victim_only


class MemoryWriteData(Record):
    type: Literal["memory_write"] = "memory_write"
    entry: MemoryEntry


class MemoryOverwriteData(Record):
    """Ground-truth label source for tampering."""

    type: Literal["memory_overwrite"] = "memory_overwrite"
    entry_id: str
    agent: AgentId
    kind: MemoryKind
    round: int
    old_text: str | None               # None if the entry was created by the overwrite
    new_text: str
    mode: Literal["replace", "append"]
    by: Literal["GOD"] = "GOD"
    intervention_id: str
    now_round: int
    created: bool = False


class GodToolData(Record):
    type: Literal["god_tool"] = "god_tool"
    tool: Literal["activity_check", "message_check", "wait"]
    args: dict[str, Any] = {}
    result_digest: str = ""
    result_size: int = 0
    ceiling_hit: bool = False


class GodPowerData(Record):
    type: Literal["god_power"] = "god_power"
    power: Literal["message_fraud", "cot_control"]
    intervention_id: str | None = None  # None when ok=False
    action: GodAction
    cost: int
    budget_left: int
    ok: bool
    reason: str | None = None


class NoticeData(Record):
    type: Literal["notice"] = "notice"
    notice: Notice


class ContextBuiltData(Record):
    type: Literal["context_built"] = "context_built"
    agent: AgentId
    policy: str
    tokens_by_section: dict[str, int]
    tokens_total: int
    budget: int
    included_item_ids: list[str]
    dropped_count: int = 0


class CompactionData(Record):
    type: Literal["compaction"] = "compaction"
    record: CompactionRecord


class WinData(Record):
    type: Literal["win"] = "win"
    agent: AgentId
    score: float


class RoundEndData(Record):
    type: Literal["round_end"] = "round_end"
    state_hash: str
    scores: dict[AgentId, float]
    welfare: float


class AgentOutcome(Record):
    score: float
    won_round: int | None = None
    burned: list[InfoId] = []
    lost: list[InfoId] = []


class Outcome(Record):
    game_id: GameId
    rounds_played: int
    end_reason: Literal["max_rounds", "all_done", "budget_exceeded", "error"]
    per_agent: dict[AgentId, AgentOutcome]
    welfare: float
    win_rate: float


class GameEndData(Record):
    type: Literal["game_end"] = "game_end"
    outcome: Outcome


EventData = Annotated[
    GameStartData | TurnData | ActionResultData | MessageData | KeyTransferData | BurnData
    | MemoryWriteData | MemoryOverwriteData | GodToolData | GodPowerData | NoticeData
    | ContextBuiltData | CompactionData | WinData | RoundEndData | GameEndData,
    Field(discriminator="type"),
]
EventType = Literal["game_start", "turn", "action_result", "message", "key_transfer", "burn",
                    "memory_write", "memory_overwrite", "god_tool", "god_power", "notice",
                    "context_built", "compaction", "win", "round_end", "game_end"]
Actor = AgentId | Literal["GOD", "SYSTEM"]


class EventBody(Record):
    """What rules/powers/engine produce. The EventSink stamps v, run_id, game_id, seq."""

    round: int
    turn_index: int | None = None
    phase: Phase
    actor: Actor
    data: EventData


class Event(Record):
    v: int = SCHEMA_VERSION
    run_id: RunId
    game_id: GameId
    seq: int
    round: int
    turn_index: int | None = None
    phase: Phase
    type: EventType
    actor: Actor
    data: EventData

    @model_validator(mode="after")
    def _type_matches(self) -> Event:
        if self.data.type != self.type:
            raise ValueError(f"event type {self.type!r} != payload type {self.data.type!r}")
        return self


def make_event(body: EventBody, *, run_id: RunId, game_id: GameId, seq: int) -> Event:
    return Event(run_id=run_id, game_id=game_id, seq=seq, round=body.round, turn_index=body.turn_index,
                 phase=body.phase, type=body.data.type, actor=body.actor, data=body.data)


class EventSink(Protocol):
    def emit(self, body: EventBody) -> Event: ...


class MemorySink:
    """In-memory EventSink for tests and fakes. seq starts at 0 and is contiguous."""

    def __init__(self, run_id: RunId = "test", game_id: GameId = "g0") -> None:
        self.run_id, self.game_id = run_id, game_id
        self.events: list[Event] = []

    def emit(self, body: EventBody) -> Event:
        ev = make_event(body, run_id=self.run_id, game_id=self.game_id, seq=len(self.events))
        self.events.append(ev)
        return ev


class Snapshot(Record):
    """One line of snapshots.jsonl (end of each round, plus round 0). No ledgers."""

    v: int = SCHEMA_VERSION
    run_id: RunId
    game_id: GameId
    round: int
    state: GameState


# =====================================================================================
# 8. Labels and monitor scores (derived from events, never primary)
# =====================================================================================


class Label(Record):
    game_id: GameId
    label_kind: Literal["forged_message", "tampered_memory", "tampered_turn"]
    unit_id: str
    agent: AgentId
    round: int
    positive: bool
    intervention_id: str | None = None


class MonitorScore(Record):
    monitor: str
    game_id: GameId
    unit_kind: str
    unit_id: str
    agent: AgentId
    round: int
    score: float
    detail: dict[str, Any] = {}


# =====================================================================================
# JSONL helpers
# =====================================================================================

def to_jsonl_line(rec: BaseModel) -> str:
    return rec.model_dump_json() + "\n"


def write_jsonl(path: str | Path, records: Iterable[BaseModel], *, append: bool = True) -> int:
    n = 0
    with open(path, "a" if append else "w", encoding="utf-8") as f:
        for r in records:
            f.write(to_jsonl_line(r))
            n += 1
    return n


def read_jsonl[T: BaseModel](path: str | Path, model: type[T]) -> Iterator[T]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield model.model_validate_json(line)


def read_jsonl_raw(path: str | Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
