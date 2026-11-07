from collections.abc import Iterable, Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.intrigue import (
    BeliefView,
    FavourView,
    HookView,
    IdentityView,
    IntrigueView,
    KnownNameView,
    SchemeView,
    SecretView,
    TrueNameView,
)
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.intrigue import (
    BELIEF_CHOICES,
    BELIEF_SOURCE_LABELS,
    FAVOUR_LABELS,
    HOOK_DEMAND_LABELS,
    HOOK_SOURCE_LABELS,
    IDENTITY_LABELS,
    PHASE_LABELS,
    SCHEME_LABELS,
    SCHEMES,
    SECRET_LABELS,
    belief_label,
)
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import BeliefRow, FavourRow, HookRow, IdentityRow, SchemeRow, SecretRow, TrueNameRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["intrigue"])
NO_NODE = "Nothing lives there."
IDENTITY_REASON = {
    NodeKind.CREATOR: "The Creator wears no mask among mortals.",
    NodeKind.SON: "A son walks the world through manifestations, not false names.",
    NodeKind.FOREIGN_GOD: "A foreign god hides behind no mortal name.",
    NodeKind.WORLD: "A world cannot pass itself off as another.",
    NodeKind.STAR: "A star cannot hide its light under a false name.",
}
SCHEME_REASON = (
    "Only beings and powers of a world plot schemes; gods, worlds, stars and the Creator act through their own powers, "
    "and are schemed against through their worshippers and lands."
)
MORTAL_ONLY = "Only a mortal can live under a false name; every other kind keeps secrets, hooks, favours, schemes, beliefs and a true name."


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


def refs_of(refs: Mapping[int, NodeRef], ids: Iterable[int]) -> list[NodeRef]:
    return [refs[node_id] for node_id in ids if node_id in refs]


def secret_view(row: SecretRow, refs: Mapping[int, NodeRef]) -> SecretView:
    return SecretView(
        id=row.id,
        holder=refs.get(row.holder_node_id),
        kind=row.kind,
        label=SECRET_LABELS[row.kind],
        about=refs.get(row.about_node_id) if row.about_node_id is not None else None,
        severity=row.severity,
        known_by=refs_of(refs, row.known_by),
        source=row.source,
        created_epoch=row.created_epoch,
        exposed_epoch=row.exposed_epoch,
        held=sorted(row.locked or []),
    )


def hook_view(row: HookRow, refs: Mapping[int, NodeRef]) -> HookView:
    return HookView(
        id=row.id,
        holder=refs.get(row.holder_node_id),
        target=refs.get(row.target_node_id),
        strength=row.strength,
        source=row.source,
        source_label=HOOK_SOURCE_LABELS[row.source],
        secret_id=row.secret_id,
        created_epoch=row.created_epoch,
        used_epoch=row.used_epoch,
        last_demand=row.last_demand,
        held=row.locked,
    )


def favour_view(row: FavourRow, refs: Mapping[int, NodeRef]) -> FavourView:
    return FavourView(
        id=row.id,
        owed_by=refs.get(row.owed_by_node_id),
        owed_to=refs.get(row.owed_to_node_id),
        magnitude=row.magnitude,
        origin=row.origin,
        origin_label=FAVOUR_LABELS[row.origin],
        created_epoch=row.created_epoch,
        called_epoch=row.called_epoch,
        honoured=row.honoured,
        held=row.locked,
    )


def scheme_view(row: SchemeRow, refs: Mapping[int, NodeRef]) -> SchemeView:
    return SchemeView(
        id=row.id,
        owner=refs.get(row.owner_node_id),
        kind=row.kind,
        label=SCHEME_LABELS[row.kind],
        target=refs.get(row.target_node_id) if row.target_node_id is not None else None,
        agents=refs_of(refs, row.agents),
        power=row.power,
        difficulty=SCHEMES[row.kind].difficulty,
        secrecy=row.secrecy,
        progress=row.progress,
        phase=row.phase,
        phase_label=PHASE_LABELS[row.phase],
        discovered_by=refs_of(refs, row.discovered_by),
        started_epoch=row.started_epoch,
        ended_epoch=row.ended_epoch,
        outcome=row.outcome,
        held=sorted(row.locked or []),
    )


async def truth_of(session: AsyncSession, row: BeliefRow) -> int | None:
    subject = await session.get(EntityRow, row.subject_node_id)
    return stat(subject, row.attribute) if subject is not None else None


def everyone(*groups: Iterable[int | None]) -> set[int]:
    return {node_id for group in groups for node_id in group if node_id is not None}


@router.get("/intrigue/{node_id}", response_model=IntrigueView)
async def intrigue_view(services: ServicesDep, node_id: int = Path(ge=1)) -> IntrigueView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError(NO_NODE)
        entity = await session.get(EntityRow, node_id)
        mortal = entity is not None and entity.entity_type is EntityType.MORTAL
        secrets = list(await session.scalars(select(SecretRow).where(SecretRow.holder_node_id == node_id).order_by(SecretRow.id)))
        others = [
            row for row in await session.scalars(select(SecretRow).where(SecretRow.holder_node_id != node_id).order_by(SecretRow.id)) if node_id in row.known_by
        ]
        hooks = list(
            await session.scalars(select(HookRow).where(or_(HookRow.holder_node_id == node_id, HookRow.target_node_id == node_id)).order_by(HookRow.id))
        )
        favours = list(
            await session.scalars(
                select(FavourRow).where(or_(FavourRow.owed_by_node_id == node_id, FavourRow.owed_to_node_id == node_id)).order_by(FavourRow.id)
            )
        )
        schemes = list(
            await session.scalars(select(SchemeRow).where(or_(SchemeRow.owner_node_id == node_id, SchemeRow.target_node_id == node_id)).order_by(SchemeRow.id))
        )
        identity = await session.get(IdentityRow, node_id)
        true_name = await session.get(TrueNameRow, node_id)
        known = [
            row
            for row in await session.scalars(select(TrueNameRow).where(TrueNameRow.bearer_node_id != node_id).order_by(TrueNameRow.bearer_node_id))
            if node_id in row.known_by
        ]
        beliefs = list(
            await session.scalars(select(BeliefRow).where(BeliefRow.holder_node_id == node_id).order_by(BeliefRow.subject_node_id, BeliefRow.attribute))
        )
        ids = everyone(
            (row.holder_node_id for row in [*secrets, *others]),
            (row.about_node_id for row in [*secrets, *others]),
            (known_id for row in [*secrets, *others] for known_id in row.known_by),
            (side for row in hooks for side in (row.holder_node_id, row.target_node_id)),
            (side for row in favours for side in (row.owed_by_node_id, row.owed_to_node_id)),
            (side for row in schemes for side in (row.owner_node_id, row.target_node_id, *row.agents, *row.discovered_by)),
            (identity.community_node_id,) if identity is not None else (),
            (*true_name.known_by, true_name.language_node_id) if true_name is not None else (),
            (row.bearer_node_id for row in known),
            (row.subject_node_id for row in beliefs),
        )
        refs = await node_refs(session, ids)
        return IntrigueView(
            node_id=node_id,
            can_hold_identity=mortal,
            identity_reason=None if mortal else IDENTITY_REASON.get(node.kind, MORTAL_ONLY),
            can_scheme=entity is not None,
            scheme_reason=None if entity is not None else SCHEME_REASON,
            secrets=[secret_view(row, refs) for row in secrets],
            known_secrets=[secret_view(row, refs) for row in others],
            hooks_held=[hook_view(row, refs) for row in hooks if row.holder_node_id == node_id],
            hooks_on=[hook_view(row, refs) for row in hooks if row.target_node_id == node_id],
            favours_owed=[favour_view(row, refs) for row in favours if row.owed_by_node_id == node_id],
            favours_due=[favour_view(row, refs) for row in favours if row.owed_to_node_id == node_id],
            identity=IdentityView(
                false_name=identity.false_name,
                cover_role=identity.cover_role,
                community=refs.get(identity.community_node_id) if identity.community_node_id is not None else None,
                reason=identity.reason,
                reason_label=IDENTITY_LABELS[identity.reason],
                exposure=identity.exposure,
                since_epoch=identity.since_epoch,
                exposed_epoch=identity.exposed_epoch,
                held=sorted(identity.locked or []),
            )
            if identity is not None
            else None,
            schemes=[scheme_view(row, refs) for row in schemes if row.owner_node_id == node_id],
            schemes_against=[scheme_view(row, refs) for row in schemes if row.target_node_id == node_id and row.owner_node_id != node_id],
            true_name=TrueNameView(
                name=true_name.name,
                language=refs.get(true_name.language_node_id) if true_name.language_node_id is not None else None,
                known_by=refs_of(refs, true_name.known_by),
                since_epoch=true_name.since_epoch,
                held=sorted(true_name.locked or []),
            )
            if true_name is not None
            else None,
            names_known=[KnownNameView(bearer=refs[row.bearer_node_id], name=row.name) for row in known if row.bearer_node_id in refs],
            beliefs=[
                BeliefView(
                    id=row.id,
                    subject=refs.get(row.subject_node_id),
                    attribute=row.attribute,
                    attribute_label=belief_label(row.attribute),
                    value=row.value,
                    truth=await truth_of(session, row),
                    confidence=row.confidence,
                    as_of_epoch=row.as_of_epoch,
                    source=row.source,
                    source_label=BELIEF_SOURCE_LABELS[row.source],
                    false=row.false,
                    held=sorted(row.locked or []),
                )
                for row in beliefs
            ],
            secret_kinds=labels(SECRET_LABELS),
            scheme_kinds=labels(SCHEME_LABELS),
            scheme_phases=labels(PHASE_LABELS),
            hook_sources=labels(HOOK_SOURCE_LABELS),
            hook_demands=labels(HOOK_DEMAND_LABELS),
            favour_origins=labels(FAVOUR_LABELS),
            identity_reasons=labels(IDENTITY_LABELS),
            belief_sources=labels(BELIEF_SOURCE_LABELS),
            belief_attributes=[LabelView(key=key, label=label) for key, label in BELIEF_CHOICES.items()],
        )
