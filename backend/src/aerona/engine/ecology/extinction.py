from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record

CRAFTS = {
    "venom": KnowledgeBranch.MEDICINE,
    "magic reagents": KnowledgeBranch.MAGIC,
    "great_bone": KnowledgeBranch.METALLURGY,
    "chitin": KnowledgeBranch.METALLURGY,
    "ivory": KnowledgeBranch.TRADE,
    "silk": KnowledgeBranch.TRADE,
    "feathers": KnowledgeBranch.TRADE,
}


async def still_yielded(ctx: TickContext, species: EntityRow, product: str) -> bool:
    others = select(SpeciesProductRow.species_entity_id).where(SpeciesProductRow.product == product, SpeciesProductRow.species_entity_id != species.id)
    found = await ctx.session.scalar(
        select(EntityRow.id).where(EntityRow.id.in_(others), EntityRow.status == EntityStatus.CANON, EntityRow.world_id == species.world_id).limit(1)
    )
    return found is not None


async def lost_crafts(ctx: TickContext, species: EntityRow) -> int:
    lost = 0
    products = await ctx.session.scalars(select(SpeciesProductRow.product).where(SpeciesProductRow.species_entity_id == species.id))
    for product in list(products):
        branch = CRAFTS.get(product)
        if branch is None or await still_yielded(ctx, species, product):
            continue
        holders = select(EntityRow.id).where(EntityRow.world_id == species.world_id)
        rows = await ctx.session.scalars(
            select(HolderLevelRow).where(HolderLevelRow.branch == branch, HolderLevelRow.holder_entity_id.in_(holders), HolderLevelRow.level > 0)
        )
        for row in list(rows):
            if "level" not in row.locked:
                row.level = max(0, row.level - ctx.rules.extinction.craft_loss)
                lost += 1
        if lost:
            await record(
                ctx,
                "ecology.craft_lost",
                roles={IncidentRole.SUBJECT: species.id},
                facts={"product": product, "craft": branch, "holders": lost, "loss": ctx.rules.extinction.craft_loss},
            )
    return lost


async def sacred_crisis(ctx: TickContext, species: EntityRow) -> int:
    table = ctx.rules.extinction
    profile = await ctx.session.get(SpeciesProfileRow, species.id)
    cults = set(
        await ctx.session.scalars(
            select(CultTenetRow.cult_entity_id).where(CultTenetRow.tenet == TenetKind.SACRED_SPECIES, CultTenetRow.target == str(species.id))
        )
    )
    if profile is not None and profile.sacred_to_node_id is not None:
        worshippers = select(BondRow.source_node_id).where(
            BondRow.target_node_id == profile.sacred_to_node_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
        )
        cults |= set(await ctx.session.scalars(worshippers))
    book = await FaithBook.load(ctx.session)
    shaken = 0
    faithful: list[int] = []
    for cult_id in sorted(cults):
        cult = await ctx.session.get(EntityRow, cult_id)
        if cult is None or cult.status is not EntityStatus.CANON:
            continue
        if stat(cult, "zeal") is not None:
            set_stats(cult, zeal=clamp_int((stat(cult, "zeal") or 0) - table.sacred_zeal, 0, PERCENT))
        church = book.churches.get(cult_id)
        for member in church.members if church is not None else []:
            town = await ctx.session.get(SettlementProfileRow, member.id)
            if town is not None and "unrest" not in town.locked:
                town.unrest = clamp_int(town.unrest + table.sacred_unrest, 0, PERCENT)
        shaken += 1
        faithful.append(cult.id)
    if shaken:
        await record(
            ctx,
            "ecology.sacred_lost",
            roles={IncidentRole.SUBJECT: species.id, IncidentRole.VICTIM: faithful},
            facts={"cults": shaken, "zeal_loss": table.sacred_zeal, "unrest": table.sacred_unrest},
        )
    return shaken


async def cascade(ctx: TickContext, species: EntityRow) -> int:
    return await lost_crafts(ctx, species) + await sacred_crisis(ctx, species)
