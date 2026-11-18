from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import spoken
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.affairs import CourtPositionRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.enums.statecraft import CourtPosition
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.folk import folk_among, towns_of_people
from aerona.engine.recording.record import record
from aerona.engine.recording.scope import recording

LETTERED = frozenset({MortalRole.SCRIBE, MortalRole.SAGE, MortalRole.PRIEST, MortalRole.JOURNALIST, MortalRole.SCIENTIST})


@dataclass
class KeeperTally:
    seated: int = 0
    succeeded: int = 0
    vacant: int = 0


async def living_mortal(session: AsyncSession, entity_id: int | None) -> EntityRow | None:
    being = await session.get(EntityRow, entity_id) if entity_id is not None else None
    return being if being is not None and being.entity_type is EntityType.MORTAL and being.status is EntityStatus.CANON else None


async def candidates(session: AsyncSession, row: RecordKeeperRow) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    if row.kind is RecordKeeperKind.HISTORIAN:
        towns = await towns_of_people(session, row.scope_node_id)
        if not towns:
            return []
        statement = statement.where(await folk_among(session, towns))
    return [being for being in await session.scalars(statement.order_by(EntityRow.id)) if not held(being.id)]


async def standing_of(ctx: TickContext, being: EntityRow, previous_id: int | None, previous_place: int | None) -> int:
    table = ctx.rules.record_keepers
    score = 0
    if being.mortal_role in LETTERED:
        score += table.lettered_weight
    court = await ctx.session.scalar(
        select(CourtPositionRow.polity_entity_id).where(CourtPositionRow.holder_entity_id == being.id, CourtPositionRow.position == CourtPosition.CHRONICLER)
    )
    if court is not None:
        score += table.court_chronicler_weight
    writing = await ctx.session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id == being.id, SkillRow.skill == SkillKind.WRITING).order_by(SkillRow.level.desc()).limit(1)
    )
    score += int(writing or 0) * table.writing_weight_pct // 100
    if previous_id is not None:
        apprentice = await ctx.session.scalar(
            select(BondRow.id)
            .where(
                BondRow.kind == BondKind.APPRENTICE_OF,
                BondRow.source_node_id == being.id,
                BondRow.target_node_id == previous_id,
                BondRow.state == BondState.ACTIVE,
            )
            .limit(1)
        )
        if apprentice is not None:
            score += table.apprentice_weight
    if previous_place is not None and being.location_id == previous_place:
        score += table.same_place_weight
    return score


async def successor(ctx: TickContext, row: RecordKeeperRow, previous: EntityRow | None) -> EntityRow | None:
    best: tuple[int, int, EntityRow] | None = None
    for being in await candidates(ctx.session, row):
        score = await standing_of(ctx, being, previous.id if previous is not None else None, previous.location_id if previous is not None else None)
        if best is None or (score, -being.id) > (best[0], best[1]):
            best = (score, -being.id, being)
    return best[2] if best is not None else None


async def seat(ctx: TickContext, row: RecordKeeperRow, tally: KeeperTally) -> None:
    if held(row.scope_node_id) or "keeper_entity_id" in (row.locked or []):
        return
    current = await living_mortal(ctx.session, row.keeper_entity_id)
    if current is not None:
        return
    previous = await ctx.session.get(EntityRow, row.keeper_entity_id) if row.keeper_entity_id is not None else None
    chosen = await successor(ctx, row, previous)
    if chosen is None:
        if row.keeper_entity_id is not None:
            row.keeper_entity_id = None
        tally.vacant += 1
        return
    key = "record_keeper.succeeded" if previous is not None else "record_keeper.seated"
    roles: dict[IncidentRole, int | list[int]] = {IncidentRole.SUBJECT: chosen.id, IncidentRole.AUTHORITY: row.scope_node_id}
    if previous is not None:
        roles[IncidentRole.PREDECESSOR] = previous.id
    async with recording(ctx, key, participants=[chosen.id, row.scope_node_id], place_id=chosen.location_id):
        row.keeper_entity_id = chosen.id
        row.since_epoch = ctx.epoch
        await record(ctx, key, roles=roles, facts={"kind": row.kind}, place=chosen.location_id)
    if previous is not None:
        tally.succeeded += 1
    else:
        tally.seated += 1


async def keeper_rows(ctx: TickContext) -> list[RecordKeeperRow]:
    creator = await CosmosRepository(ctx.session).creator()
    rows = {(row.kind, row.scope_node_id): row for row in await ctx.session.scalars(select(RecordKeeperRow).order_by(RecordKeeperRow.id))}
    if creator is not None and not held(creator.id) and not any(kind is RecordKeeperKind.CHRONICLER for kind, _ in rows):
        made = RecordKeeperRow(kind=RecordKeeperKind.CHRONICLER, scope_node_id=creator.id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(made)
        rows[(made.kind, creator.id)] = made
    for people in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if (RecordKeeperKind.HISTORIAN, people.id) not in rows and not held(people.id):
            made = RecordKeeperRow(kind=RecordKeeperKind.HISTORIAN, scope_node_id=people.id, since_epoch=ctx.epoch, locked=[])
            ctx.session.add(made)
            rows[(made.kind, people.id)] = made
    await ctx.session.flush()
    return sorted(rows.values(), key=lambda row: row.id)


async def keep_record_keepers(ctx: TickContext, tally: KeeperTally) -> None:
    for row in await keeper_rows(ctx):
        await seat(ctx, row, tally)
    await ctx.session.flush()


async def keeper_of(session: AsyncSession, kind: RecordKeeperKind, scope_node_id: int | None) -> EntityRow | None:
    if scope_node_id is None:
        return None
    row = await session.scalar(select(RecordKeeperRow).where(RecordKeeperRow.kind == kind, RecordKeeperRow.scope_node_id == scope_node_id))
    return await living_mortal(session, row.keeper_entity_id) if row is not None else None


async def chronicler_now(session: AsyncSession) -> EntityRow | None:
    creator = await CosmosRepository(session).creator()
    return await keeper_of(session, RecordKeeperKind.CHRONICLER, creator.id if creator is not None else None)


async def identity_of(session: AsyncSession, being: EntityRow) -> str:
    profile = await session.get(MortalProfileRow, being.id)
    trade = (
        spoken(profile.profession) if profile is not None and profile.profession is not None else spoken(being.mortal_role) if being.mortal_role else "mortal"
    )
    people = await people_of(session, being)
    place = await session.get(EntityRow, being.location_id) if being.location_id is not None else None
    parts = [trade]
    if people is not None:
        parts.append(f"of {people.name}")
    if place is not None:
        parts.append(f"in {place.name}")
    return " ".join(parts)
