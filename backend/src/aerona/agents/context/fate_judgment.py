from collections.abc import Sequence

from sqlalchemy import case, select

from aerona.agents.context.scope import Scope
from aerona.agents.context.tired_images import tired_images
from aerona.agents.context.world_summary import world_summary
from aerona.agents.fate.threads import ThreadQuota
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.prompts.contexts.common import NamedRecord
from aerona.prompts.contexts.fate import FateJudgmentContext, FateThreadLine, WorldRecordLine


async def world_records(scope: Scope, epoch: int) -> list[WorldRecordLine]:
    statement = (
        select(EntityRow)
        .where(EntityRow.birth_epoch == epoch, EntityRow.origin == EntityOrigin.ENGINE, EntityRow.status != EntityStatus.REJECTED)
        .order_by(case((EntityRow.entity_type == EntityType.EVENT, 0), else_=1), EntityRow.id.desc())
    )
    return [
        WorldRecordLine(id=entity.id, name=entity.name, kind_label=entity.subtype or ENTITY_TYPES[entity.entity_type].label)
        for entity in await scope.session.scalars(statement)
    ]


async def pantheon(scope: Scope) -> list[NamedRecord]:
    sons = await scope.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id))
    return [NamedRecord(id=son.id, name=son.name) for son in sons]


async def languages(scope: Scope) -> list[NamedRecord]:
    rows = await scope.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [NamedRecord(id=row.id, name=row.name) for row in rows]


async def fate_judgment_context(
    scope: Scope,
    epoch: int,
    *,
    age_events: str,
    engine_notes: Sequence[str],
    creations: Sequence[str],
    pending: Sequence[str],
    prophecies: Sequence[str],
    quota: ThreadQuota,
) -> FateJudgmentContext:
    return FateJudgmentContext(
        lore_language=scope.cosmos.lore_language,
        rules=scope.rules,
        age=epoch,
        min_close=quota.min_close,
        new_max=quota.new_max,
        close_candidates=quota.candidates,
        world_summary=await world_summary(scope),
        age_events=age_events,
        engine_notes=list(engine_notes),
        new_creations=list(creations),
        pending=list(pending),
        world_records=await world_records(scope, epoch),
        prophecies=list(prophecies),
        threads=[
            FateThreadLine(
                id=state.thread.id,
                age=state.thread.epoch,
                advancers=state.advancers,
                advance_count=state.advance_count,
                stagnant_ages=state.stagnant,
                text=state.thread.text,
            )
            for state in quota.threads
        ],
        pantheon=await pantheon(scope),
        languages=await languages(scope),
        tired_images=await tired_images(scope, None),
    )
