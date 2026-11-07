from typing import Any

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium, OpinionSubject, SignalKind, SignalState


class DispatchView(ApiModel):
    id: int
    sender: NodeRef | None
    recipient: NodeRef | None
    medium: Medium | None
    medium_label: str
    content: DispatchContent | None
    content_label: str
    state: DispatchState | None
    state_label: str
    language: NodeRef | None
    envoy: NodeRef | None
    envoy_fate: EnvoyFate | None
    envoy_fate_label: str | None
    intercepted_by: NodeRef | None
    payload: dict[str, Any]
    sent_epoch: int
    arrival_epoch: int | None
    forged: bool
    misread: bool
    enciphered: bool
    held: list[str]


class PublicOpinionView(ApiModel):
    community: NodeRef | None
    subject: NodeRef | None
    subject_kind: OpinionSubject
    subject_label: str
    approval: int
    censored: bool
    epoch: int
    held: list[str]


class CipherView(ApiModel):
    owner: NodeRef | None
    strength: int
    broken_by: list[NodeRef]
    attempts: int
    break_known: bool
    since_epoch: int
    held: list[str]


class SignalView(ApiModel):
    id: int
    owner: NodeRef | None
    kind: SignalKind
    kind_label: str
    start: NodeRef | None
    end: NodeRef | None
    state: SignalState
    state_label: str
    since_epoch: int
    held: list[str]


class CorrespondenceView(ApiModel):
    node_id: int
    sent: list[DispatchView]
    received: list[DispatchView]
    intercepted: list[DispatchView]
    opinions: list[PublicOpinionView]
    regarded: list[PublicOpinionView]
    cipher: CipherView | None
    ciphers_read: list[CipherView]
    signals: list[SignalView]
    mediums: list[LabelView]
    contents: list[LabelView]
    states: list[LabelView]
    subjects: list[LabelView]
    signal_kinds: list[LabelView]
    signal_states: list[LabelView]
