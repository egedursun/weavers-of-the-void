from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.repositories.names import normalize_name
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.lore import HistorianViewRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.record_keepers.keepers import keeper_rows
from aerona.engine.recording.record import record
from aerona.engine.recording.scope import recording

LEGACY_FIXUP = "record_keepers.legacy"


async def named_mortal(ctx: TickContext, name: str) -> EntityRow | None:
    wanted = normalize_name(name)
    for being in await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL).order_by(EntityRow.id)):
        if normalize_name(being.name) == wanted:
            return being
    return None


async def first_home(ctx: TickContext, people_id: int | None) -> EntityRow | None:
    towns = await towns_of_people(ctx.session, people_id) if people_id is not None else []
    if towns:
        return await ctx.session.get(EntityRow, towns[0])
    return await ctx.session.scalar(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )


@dataclass(frozen=True)
class Written:
    name: str
    who: str
    people_id: int | None
    first: int
    last: int
    living: bool


async def remembered(ctx: TickContext, written: Written) -> EntityRow:
    name, who, people_id, first, last, living = written.name, written.who, written.people_id, written.first, written.last, written.living
    found = await named_mortal(ctx, name)
    if found is not None:
        return found
    home = await first_home(ctx, people_id)
    being = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.MORTAL,
            name=name,
            body=who,
            stats=MortalStats(age=ctx.rules.record_keepers.recovered_age, lifespan=ctx.rules.record_keepers.recovered_lifespan),
            power=1,
            location_id=home.id if home is not None else None,
            world_id=home.world_id if home is not None else None,
        ),
    )
    being.birth_epoch = max(1, first - 1)
    if not living:
        being.end_epoch = last
        being.status = EntityStatus.DEAD
    await ctx.session.flush()
    return being


async def recover_chroniclers(ctx: TickContext, chronicler: RecordKeeperRow | None) -> int:
    rows = list(
        await ctx.session.scalars(
            select(EpochRow).where(EpochRow.chronicler_name.is_not(None), EpochRow.chronicler_entity_id.is_(None)).order_by(EpochRow.epoch)
        )
    )
    spans: dict[str, tuple[int, int, str]] = {}
    for row in rows:
        name = row.chronicler_name or ""
        first, _, who = spans.get(name, (row.epoch, row.epoch, row.chronicler_identity or ""))
        spans[name] = (first, row.epoch, who)
    if chronicler is None or held(chronicler.scope_node_id):
        return 0
    latest = rows[-1].chronicler_name if rows else None
    linked = 0
    for name, (first, last, who) in sorted(spans.items(), key=lambda item: item[1][0]):
        living = name == latest and chronicler is not None and chronicler.keeper_entity_id is None and "keeper_entity_id" not in (chronicler.locked or [])
        async with recording(ctx, "record_keeper.recovered"):
            being = await remembered(ctx, Written(name, who, None, first, last, living))
            for row in rows:
                if row.chronicler_name == name:
                    row.chronicler_entity_id = being.id
            if living and chronicler is not None:
                chronicler.keeper_entity_id = being.id
                chronicler.since_epoch = first
            await record(ctx, "record_keeper.recovered", roles={IncidentRole.SUBJECT: being.id}, facts={"kind": RecordKeeperKind.CHRONICLER})
        linked += 1
    return linked


async def recover_historians(ctx: TickContext, historians: dict[int, RecordKeeperRow]) -> int:
    rows = list(
        await ctx.session.scalars(
            select(HistorianViewRow)
            .where(HistorianViewRow.historian.is_not(None), HistorianViewRow.historian_entity_id.is_(None))
            .order_by(HistorianViewRow.id)
        )
    )
    spans: dict[tuple[int, str], tuple[int, int]] = {}
    for row in rows:
        key = (row.people_entity_id, row.historian or "")
        first, _ = spans.get(key, (row.epoch, row.epoch))
        spans[key] = (first, row.epoch)
    latest = {row.people_entity_id: row.historian for row in sorted(rows, key=lambda view: (view.epoch, view.id))}
    linked = 0
    for (people_id, name), (first, last) in sorted(spans.items(), key=lambda item: (item[1][0], item[0])):
        keeper = historians.get(people_id)
        if keeper is None or held(people_id):
            continue
        living = latest.get(people_id) == name and keeper is not None and keeper.keeper_entity_id is None and "keeper_entity_id" not in (keeper.locked or [])
        async with recording(ctx, "record_keeper.recovered"):
            being = await remembered(ctx, Written(name, "", people_id, first, last, living))
            for row in rows:
                if row.people_entity_id == people_id and row.historian == name:
                    row.historian_entity_id = being.id
            if living and keeper is not None:
                keeper.keeper_entity_id = being.id
                keeper.since_epoch = first
            await record(ctx, "record_keeper.recovered", roles={IncidentRole.SUBJECT: being.id}, facts={"kind": RecordKeeperKind.HISTORIAN})
        linked += 1
    return linked


async def recover_keepers(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return 0
    rows = await keeper_rows(ctx)
    chronicler = next((row for row in rows if row.kind is RecordKeeperKind.CHRONICLER), None)
    historians = {row.scope_node_id: row for row in rows if row.kind is RecordKeeperKind.HISTORIAN}
    result = {"chroniclers": await recover_chroniclers(ctx, chronicler), "historians": await recover_historians(ctx, historians)}
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
