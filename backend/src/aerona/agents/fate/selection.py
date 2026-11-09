from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import or_, select

from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.scope import Scope
from aerona.agents.fate.prescreen import prescreen
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.fate import FateCreationEntryContext

ENTRY_SEPARATOR_LENGTH = 9
OPEN_VERDICTS = (Verdict.LIMBO, Verdict.UNJUDGED)


@dataclass
class Fitted:
    ids: list[int] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)
    epochs: dict[int, int] = field(default_factory=dict)


def judge_origins(scope: Scope) -> tuple[EntityOrigin, ...]:
    return (EntityOrigin.SON, EntityOrigin.MORTAL) if scope.rules.fate.review_mortal_creations else (EntityOrigin.SON,)


async def records_to_judge(scope: Scope, start: int, epoch: int) -> list[EntityRow]:
    judged = select(CreationVerdictRow.entity_id).where(CreationVerdictRow.verdict.not_in(OPEN_VERDICTS))
    statement = (
        select(EntityRow)
        .where(
            EntityRow.status == EntityStatus.CANON,
            EntityRow.pending_name.is_(False),
            EntityRow.origin.in_(judge_origins(scope)),
            EntityRow.birth_epoch.between(start, epoch),
            or_(EntityRow.birth_epoch == epoch, EntityRow.id.not_in(judged)),
        )
        .order_by(EntityRow.id)
    )
    return list(await scope.session.scalars(statement))


async def creation_entry(scope: Scope, entity: EntityRow, warn: bool) -> str:
    warnings = await prescreen(scope, entity) if warn else []
    return render(PromptId.FATE_CREATION_ENTRY, FateCreationEntryContext(detail=await entity_detail(scope, entity), warnings=warnings))


async def fit(scope: Scope, entities: Sequence[EntityRow], limit: float, warn: bool) -> tuple[Fitted, list[EntityRow]]:
    fitted = Fitted()
    used = 0
    overflow: list[EntityRow] = []
    for entity in entities:
        if overflow:
            overflow.append(entity)
            continue
        entry = await creation_entry(scope, entity, warn)
        if fitted.ids and used + len(entry) + ENTRY_SEPARATOR_LENGTH > limit:
            overflow.append(entity)
            continue
        fitted.ids.append(entity.id)
        fitted.entries.append(entry)
        fitted.epochs[entity.id] = entity.birth_epoch
        used += len(entry) + ENTRY_SEPARATOR_LENGTH
    return fitted, overflow


async def batches(scope: Scope, entities: Sequence[EntityRow], limit: int) -> list[Fitted]:
    groups: list[Fitted] = []
    remaining = list(entities)
    while remaining:
        group, remaining = await fit(scope, remaining, limit, True)
        groups.append(group)
    return groups


async def old_prophecies(scope: Scope, epoch: int) -> Fitted:
    prophecies = list(
        await scope.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.PROPHECY, EntityRow.status == EntityStatus.CANON, EntityRow.birth_epoch < epoch)
            .order_by(EntityRow.id.desc())
        )
    )
    fitted, _ = await fit(scope, prophecies, scope.rules.fate.budget_old_prophecies_chars, False)
    return fitted
