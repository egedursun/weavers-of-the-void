from collections import defaultdict

from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import PeopleSubstrateRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.minds import MindOrigin, MindSeat
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.profiles import is_made
from aerona.engine.notes import note
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record

PEOPLE_POWER = 10


async def form(ctx: TickContext, maker: EntityRow, rows: list[MindProfileRow]) -> EntityRow:
    seats: dict[MindSeat, int] = defaultdict(int)
    for row in rows:
        seats[row.seat] += 1
    seat = max(seats, key=lambda key: (seats[key], key.value))
    origin = MindOrigin.MADE if any(row.origin is MindOrigin.MADE for row in rows) else rows[0].origin
    people = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=f"the minds made by {maker.name}",
            body=f"The made minds of {maker.name}, become a people of their own in epoch {ctx.epoch}.",
            stats=PeopleStats(population=len(rows)),
            power=PEOPLE_POWER,
            location_id=maker.location_id,
            world_id=maker.world_id,
        ),
    )
    ctx.session.add(PeopleSubstrateRow(people_entity_id=people.id, seat=seat, origin=origin, share_pct=100, locked=[]))
    for row in rows:
        await connect(ctx.session, row.node_id, people.id, BondKind.MEMBER_OF, ctx.epoch, description="one of this people")
    await note(ctx, f"The made minds of {maker.name} became a people.", key="made_people.formed", ids=[people.id, maker.id])
    return people


@reads("table.bonds", "table.entities", "table.mind_profiles", "table.people_substrates")
@writes("table.bonds", "table.entities", "table.people_substrates")
async def form_made_peoples(ctx: TickContext) -> None:
    lines: dict[int, list[MindProfileRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.made_by_node_id.is_not(None)).order_by(MindProfileRow.node_id)):
        if is_made(row) and row.made_by_node_id is not None and not held(row.node_id):
            lines[row.made_by_node_id].append(row)
    members = select(BondRow.source_node_id).where(BondRow.kind == BondKind.MEMBER_OF, BondRow.target_node_id.in_(select(PeopleSubstrateRow.people_entity_id)))
    joined = set(await ctx.session.scalars(members))
    have = {maker for maker, rows in lines.items() if any(row.node_id in joined for row in rows)}
    for maker_id, rows in sorted(lines.items()):
        if maker_id in have or len(rows) < ctx.rules.made_peoples.formation_minds or held(maker_id):
            continue
        maker = await ctx.session.get(EntityRow, maker_id)
        if maker is None:
            continue
        await form(ctx, maker, rows)
        ctx.count("made_peoples_formed")
    await ctx.session.flush()
