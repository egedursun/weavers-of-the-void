from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record

CARRIER_BOND_KINDS = (BondKind.LIVES_IN, BondKind.DESCENDS_FROM)
BALLAD_SUBTYPE = "heroic ballad"


async def legend_carrier(ctx: TickContext, hero: EntityRow) -> EntityRow | None:
    location = await living_entity(ctx.session, hero.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    repository = BondRepository(ctx.session)
    bonds = [bond for kind in CARRIER_BOND_KINDS for bond in await repository.outgoing(hero.id, kind, active_only=False)]
    for bond in sorted(bonds, key=lambda item: (item.active, item.id), reverse=True):
        target = await living_entity(ctx.session, bond.target_node_id)
        if target is not None and target.entity_type in COMMUNITY_TYPES:
            return target
    return None


async def carry_legend(ctx: TickContext, hero: EntityRow, legend: EntityRow, description: str) -> None:
    carrier = await legend_carrier(ctx, hero)
    if carrier is not None:
        await connect(ctx.session, carrier.id, legend.id, BondKind.TELLS_OF, ctx.epoch, description=description)


async def tell_legend(ctx: TickContext, *, name: str, subtype: str, body: str, power: int, spread: int, subjects: list[EntityRow]) -> EntityRow:
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=name,
            body=body,
            stats=LegendStats(spread=spread),
            power=power,
            world_id=subjects[0].world_id,
            subtype=subtype,
        ),
    )
    for subject in subjects:
        await connect(ctx.session, legend.id, subject.id, BondKind.TELLS_OF, ctx.epoch)
    return legend


async def sing_of_slaying(ctx: TickContext, hero: EntityRow, beast: EntityRow, deed: str) -> EntityRow:
    hunt = ctx.rules.world_hunt
    ballad = await tell_legend(
        ctx,
        name=f"{hero.name} and {beast.name}",
        subtype=BALLAD_SUBTYPE,
        body=f"{hero.name}, {deed}, killed {beast.name}. The mortals began to tell of it.",
        power=hunt.ballad_power,
        spread=hunt.ballad_spread,
        subjects=[hero, beast],
    )
    await carry_legend(ctx, hero, ballad, "sings their ballad")
    return ballad
