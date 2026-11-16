from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, LivingProfileRow, SymbiontRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.ecology import Temperament
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.living import CultivationMethod, Fertility, GrowthStage, HostPlacement, HostRelation, LineTrait, Metabolism
from aerona.domain.enums.powers import PowerOrigin, PowerState, PowerVisibility
from aerona.engine.context import TickContext
from aerona.engine.living.kin import line_of
from aerona.engine.living.lines import LineDraft, make_line, run_wild
from aerona.engine.living.traits import scaled, traits_of
from aerona.engine.notes import note
from aerona.engine.powers.control import PowerDraft, create_power
from aerona.engine.primitives.numbers import clamp_percent

FEED_OF = {Metabolism.FEEDING: CommodityKind.FODDER, Metabolism.CHEMICAL: CommodityKind.ORE}


async def node_exists(ctx: TickContext, node_id: int | None, what: str) -> None:
    if node_id is not None and await ctx.session.get(NodeRow, node_id) is None:
        raise NotFoundError(f"No such {what}.")


async def give_life(ctx: TickContext, thing_id: int, *, line_id: int | None, metabolism: Metabolism, lifespan: int, bonded_to: int | None) -> LivingProfileRow:
    thing = await ctx.session.get(EntityRow, thing_id)
    if thing is None or thing.status is not EntityStatus.CANON:
        raise NotFoundError("There is nothing there to bring to life.")
    if held(thing.id):
        raise ValidationFailedError("That is held against the world.")
    if await ctx.session.get(LivingProfileRow, thing.id) is not None:
        raise ValidationFailedError(f"{thing.name} is already alive.")
    line = await line_of(ctx, line_id) if line_id is not None else None
    await node_exists(ctx, bonded_to, "handler")
    row = LivingProfileRow(
        thing_node_id=thing.id,
        line_id=line.id if line is not None else None,
        metabolism=line.metabolism if line is not None else metabolism,
        feed_commodity=FEED_OF.get(metabolism),
        feed_per_season=1,
        growth_stage=GrowthStage.SEED,
        size_pct=20,
        regeneration=20,
        health=PERCENT,
        bonded_to_node_id=bonded_to,
        bond=PERCENT // 2,
        fertility=line.fertility if line is not None else Fertility.BREEDS_TRUE,
        lifespan_years=max(1, lifespan),
        age_seasons=0,
        designed_by_node_id=line.maker_node_id if line is not None else None,
        planted_epoch=ctx.epoch,
        locked=[],
    )
    traits = await traits_of(ctx.session, row.line_id)
    row.regeneration = clamp_percent(row.regeneration + traits.get(LineTrait.REGENERATION, 0))
    row.lifespan_years = max(1, scaled(row.lifespan_years, traits.get(LineTrait.LIFESPAN, 0)))
    if traits.get(LineTrait.NERVOUS_SYSTEM, 0) > 0:
        row.temperament = Temperament.PLACID if traits.get(LineTrait.DOCILITY, 0) > 0 else Temperament.CURIOUS
    ctx.session.add(row)
    await ctx.session.flush()
    if traits.get(LineTrait.GIFT, 0) >= ctx.rules.living.gift_at:
        await born_gift(ctx, thing.id, traits[LineTrait.GIFT])
    await note(ctx, f"{thing.name} came alive.", key="living.profile_made", ids=[thing.id])
    return row


async def born_gift(ctx: TickContext, thing_id: int, strength: int) -> None:
    rng = ctx.rng(f"living.gift.{thing_id}")
    draft = PowerDraft(
        thing_id,
        rng.pick(list(SpellTechnique)),
        rng.pick(list(SpellForm)),
        max(1, strength // 10),
        PERCENT // 4,
        PowerOrigin.GROWN,
        PowerState.LATENT,
        PowerVisibility.SUBTLE,
    )
    await create_power(ctx, draft)


async def end_life(ctx: TickContext, thing_id: int) -> LivingProfileRow:
    row = await ctx.session.get(LivingProfileRow, thing_id)
    if row is None:
        raise NotFoundError("That is not alive.")
    if held(thing_id):
        raise ValidationFailedError("That is held against the world.")
    row.health, row.growth_stage = 0, GrowthStage.DEAD
    await ctx.session.flush()
    return row


async def found_bank(ctx: TickContext, structure_id: int, holder_id: int | None) -> GeneBankRow:
    structure = await ctx.session.get(EntityRow, structure_id)
    if structure is None or structure.status is not EntityStatus.CANON:
        raise NotFoundError("There is no work there to hold a bank of life.")
    if await ctx.session.get(GeneBankRow, structure_id) is not None:
        raise ValidationFailedError(f"{structure.name} already keeps a bank of life.")
    await node_exists(ctx, holder_id, "holder")
    row = GeneBankRow(structure_entity_id=structure_id, holder_node_id=holder_id, upkeep=ctx.rules.genome_design.bank_upkeep, unpaid_epochs=0, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def host(ctx: TickContext, host_id: int, *, line_id: int | None, placement: HostPlacement, relation: HostRelation, strength: int) -> SymbiontRow:
    await node_exists(ctx, host_id, "host")
    if held(host_id):
        raise ValidationFailedError("That one is held against the world.")
    if line_id is not None:
        await line_of(ctx, line_id)
    row = SymbiontRow(
        host_node_id=host_id, line_id=line_id, placement=placement, relation=relation, strength=clamp_percent(strength), since_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def symbiont_of(ctx: TickContext, symbiont_id: int) -> SymbiontRow:
    row = await ctx.session.get(SymbiontRow, symbiont_id)
    if row is None:
        raise NotFoundError("No such symbiont.")
    return row


async def release(ctx: TickContext, line: LivingLineRow) -> LivingLineRow:
    if line.species_entity_id is None:
        raise ValidationFailedError("A line with no species behind it has nowhere wild to go.")
    if not await run_wild(ctx, line):
        line.escaped = True
    await note(ctx, f"{line.name} was let loose into the wild.", key="living.released", ids=[line.species_entity_id])
    return line


async def raise_line(ctx: TickContext, sample_id: int, maker_id: int) -> LivingLineRow:
    sample = await ctx.session.get(GeneBankSampleRow, sample_id)
    if sample is None:
        raise NotFoundError("No such sample in a bank of life.")
    organism = await ctx.session.get(EntityRow, sample.organism_node_id)
    bank = await ctx.session.get(GeneBankRow, sample.bank_entity_id)
    name = f"the line raised from {organism.name}" if organism is not None else "a line raised from a kept sample"
    draft = LineDraft(name, CultivationMethod.CLONING, maker_id, bank.holder_node_id if bank is not None else None, (sample.organism_node_id,), ())
    line = await make_line(ctx, draft, forced=True)
    line.stability = clamp_percent(sample.quality * ctx.rules.genome_design.raise_fidelity_pct // PERCENT)
    return line


async def contain(ctx: TickContext, line: LivingLineRow) -> LivingLineRow:
    if not line.escaped:
        raise ValidationFailedError(f"{line.name} has not got loose.")
    culled = 0
    if line.species_entity_id is not None:
        for row in list(await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == line.species_entity_id))):
            if row.since_epoch >= line.founded_epoch and not row.locked and not held(row.region_entity_id):
                await ctx.session.delete(row)
                culled += 1
    line.escaped = False
    await note(ctx, f"{line.name} was hunted down and held in again, out of {several(culled, 'land', 'lands')}.", key="living.contained", ids=[])
    return line
