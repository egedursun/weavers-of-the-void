import re

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.fate.name_check import dialect_letters, god_lookalike, is_weak
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.renames import rewrite_name
from aerona.language.alphabet import first_word
from aerona.language.generator import NameKind
from aerona.language.similarity import normalize_name
from aerona.rules.registry import Rules

PERCENT = 100
NUMBERED = re.compile(r"^(\S+) (?:II|III|IV|V|VI|VII|VIII|IX|X)$")
REFIT_SEED = "dialect-refit"


class WorldDialectFit(BaseModel):
    model_config = ConfigDict(frozen=True)

    world_id: int
    world_name: str
    named: int
    misfits: int
    misfit_pct: int


class NameReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    worlds: list[WorldDialectFit]
    misfits: int
    weak_names: int
    numbered_borrowed_names: int
    god_lookalikes: int


async def name_report(session: AsyncSession, rules: Rules) -> NameReport:
    records = list(
        await session.scalars(
            select(EntityRow)
            .where(EntityRow.status != EntityStatus.REJECTED, EntityRow.entity_type != EntityType.LANGUAGE, EntityRow.pending_name.is_(False))
            .order_by(EntityRow.id)
        )
    )
    worlds: list[WorldDialectFit] = []
    for world in await session.scalars(select(WorldRow).order_by(WorldRow.id)):
        own = [record for record in records if record.world_id == world.id]
        phonology = world.phonology
        misfits = sum(1 for record in own if phonology is not None and dialect_letters(first_word(record.name), phonology))
        worlds.append(
            WorldDialectFit(
                world_id=world.id, world_name=world.name, named=len(own), misfits=misfits, misfit_pct=round(misfits * PERCENT / len(own)) if own else 0
            )
        )
    first_of: dict[str, EntityRow] = {}
    for record in records:
        first_of.setdefault(normalize_name(record.name), record)
    numbered = 0
    for record in records:
        match = NUMBERED.match(record.name)
        original = first_of.get(normalize_name(match.group(1))) if match else None
        if original is not None and original.entity_type is not record.entity_type:
            numbered += 1
    weak = sum(1 for record in records if is_weak(record.name, rules))
    lookalikes = 0
    for record in records:
        if len(record.name.split()) == 1 and await god_lookalike(session, rules, record.name):
            lookalikes += 1
    return NameReport(
        worlds=worlds, misfits=sum(world.misfits for world in worlds), weak_names=weak, numbered_borrowed_names=numbered, god_lookalikes=lookalikes
    )


async def refit_pending_names(session: AsyncSession, rules: Rules, epoch: int) -> int:
    flagged = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.NAME_FROM_LANGUAGE)
    pending = list(await session.scalars(select(EntityRow).where(EntityRow.pending_name.is_(True), EntityRow.id.in_(flagged)).order_by(EntityRow.id)))
    if not pending:
        return 0
    namer = Namer(session, rules)
    repository = EntityRepository(session)
    changed = 0
    for entity in pending:
        world = await session.get(WorldRow, entity.world_id)
        if world is None or world.phonology is None or not dialect_letters(first_word(entity.name), world.phonology):
            continue
        fresh = await namer.from_speaker(entity.id, seed_of(REFIT_SEED, entity.id), NameKind.GENERAL)
        if not fresh or fresh == entity.name or dialect_letters(first_word(fresh), world.phonology):
            continue
        old = entity.name
        await repository.rename(entity, fresh)
        await rewrite_name(session, entity.id, old, entity.name, epoch)
        changed += 1
    return changed
