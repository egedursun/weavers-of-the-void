from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.lore import (
    IncidentRef,
    KeeperView,
    KinView,
    LanguageCard,
    LegendCard,
    RegisterView,
    SpeakerView,
    TraditionCard,
    TraditionEffectView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.db.tables.culture import (
    LanguageIntelligibilityRow,
    LanguageRegisterRow,
    LanguageStandingRow,
    LegendProfileRow,
    SpeakerCohortRow,
    TraditionEffectRow,
    TraditionParticipationRow,
    TraditionProfileRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.entity import EntityType

Refs = dict[int, NodeRef]


def ref(refs: Refs, node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def incident_ref(session: AsyncSession, incident_id: int | None) -> IncidentRef | None:
    row = await session.get(IncidentRow, incident_id) if incident_id is not None else None
    return IncidentRef(id=row.id, kind=row.kind, epoch=row.epoch, note=row.note) if row is not None else None


async def register_views(session: AsyncSession, rows: list[LanguageRegisterRow]) -> list[RegisterView]:
    refs = await node_refs(session, [*(row.holder_entity_id for row in rows), *(row.language_entity_id for row in rows)])
    return [
        RegisterView(
            holder=ref(refs, row.holder_entity_id),
            kind=row.register,
            language=ref(refs, row.language_entity_id),
            since_epoch=row.since_epoch,
            held="language_entity_id" in row.locked,
        )
        for row in rows
    ]


async def registers_of_language(session: AsyncSession, language_id: int) -> list[RegisterView]:
    rows = await session.scalars(
        select(LanguageRegisterRow)
        .where(LanguageRegisterRow.language_entity_id == language_id)
        .order_by(LanguageRegisterRow.register, LanguageRegisterRow.holder_entity_id)
    )
    return await register_views(session, list(rows))


async def registers_of_languages(session: AsyncSession, language_ids: list[int]) -> list[RegisterView]:
    if not language_ids:
        return []
    rows = await session.scalars(
        select(LanguageRegisterRow)
        .where(LanguageRegisterRow.language_entity_id.in_(language_ids))
        .order_by(LanguageRegisterRow.register, LanguageRegisterRow.holder_entity_id)
    )
    return await register_views(session, list(rows))


async def language_card(session: AsyncSession, entity_id: int) -> LanguageCard | None:
    row = await session.get(LanguageStandingRow, entity_id)
    if row is None:
        return None
    cohorts = list(
        await session.scalars(select(SpeakerCohortRow).where(SpeakerCohortRow.language_entity_id == entity_id).order_by(SpeakerCohortRow.community_entity_id))
    )
    kin = list(
        await session.scalars(
            select(LanguageIntelligibilityRow)
            .where((LanguageIntelligibilityRow.first_entity_id == entity_id) | (LanguageIntelligibilityRow.second_entity_id == entity_id))
            .order_by(LanguageIntelligibilityRow.value.desc())
        )
    )
    others = [item.second_entity_id if item.first_entity_id == entity_id else item.first_entity_id for item in kin]
    refs = await node_refs(session, [*(item.community_entity_id for item in cohorts), *others])
    return LanguageCard(
        prestige=row.prestige,
        prestige_parts=row.prestige_parts,
        standardisation=row.standardisation,
        liturgical=row.liturgical,
        lingua_franca=row.lingua_franca,
        speakers=[
            SpeakerView(
                community=ref(refs, item.community_entity_id), kind=item.kind, share=item.share, since_epoch=item.since_epoch, held="share" in item.locked
            )
            for item in cohorts
        ],
        kin=[KinView(language=ref(refs, other), value=item.value, held="value" in item.locked) for item, other in zip(kin, others, strict=True)],
        registers=await registers_of_language(session, entity_id),
        locked=row.locked,
    )


async def legend_card(session: AsyncSession, entity_id: int) -> LegendCard | None:
    row = await session.get(LegendProfileRow, entity_id)
    if row is None:
        return None
    refs = await node_refs(session, [*row.tellers, *(item for item in (row.subject_node_id, row.fixed_in_entity_id) if item is not None)])
    bards = set(await session.scalars(select(EntityRow.id).where(EntityRow.id.in_(row.tellers), EntityRow.entity_type == EntityType.MORTAL)))
    return LegendCard(
        archetype=row.archetype,
        credence=row.credence,
        distortion=row.distortion,
        subject=ref(refs, row.subject_node_id),
        moral=row.moral,
        tellers=[refs[item] for item in row.tellers if item in refs and item not in bards],
        bards=[refs[item] for item in row.tellers if item in refs and item in bards],
        fixed_in=ref(refs, row.fixed_in_entity_id),
        source=await incident_ref(session, row.source_incident_id),
        custom_archetype_id=row.custom_archetype_id,
        locked=row.locked,
    )


async def tradition_card(session: AsyncSession, entity_id: int) -> TraditionCard | None:
    row = await session.get(TraditionProfileRow, entity_id)
    if row is None:
        return None
    keepers = list(
        await session.scalars(
            select(TraditionParticipationRow)
            .where(TraditionParticipationRow.tradition_entity_id == entity_id)
            .order_by(TraditionParticipationRow.community_entity_id)
        )
    )
    effects = list(
        await session.scalars(
            select(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == entity_id).order_by(TraditionEffectRow.effect, TraditionEffectRow.target)
        )
    )
    refs = await node_refs(session, [*(item.community_entity_id for item in keepers), *([row.origin_entity_id] if row.origin_entity_id else [])])
    return TraditionCard(
        kind=row.kind,
        calendar_slot=row.calendar_slot,
        season_position=row.season_position,
        calendar_entity_id=row.calendar_entity_id,
        notable_year_id=row.notable_year_id,
        in_season=row.in_season,
        cost=row.cost,
        effects=[TraditionEffectView(effect=item.effect, target=item.target, magnitude=item.magnitude) for item in effects],
        taboo_target=row.taboo_target,
        taboo_act=row.taboo_act,
        custom_kind_id=row.custom_kind_id,
        origin=ref(refs, row.origin_entity_id),
        origin_incident=await incident_ref(session, row.origin_incident_id),
        keepers=[
            KeeperView(
                community=ref(refs, item.community_entity_id),
                participation=item.participation,
                skipped=item.skipped,
                last_celebrated_epoch=item.last_celebrated_epoch,
                held="participation" in item.locked,
            )
            for item in keepers
        ],
        locked=row.locked,
    )
