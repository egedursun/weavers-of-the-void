from collections import Counter

from sqlalchemy import select

from aerona.catalog.genetics import LOCI, LOOKS_LOCI
from aerona.catalog.kinds.gifts import GIFT_STANCES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow, HouseResemblanceRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import PreferenceKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import HouseTrait
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import genome_of, gifted_schools, phenotype
from aerona.engine.genetics.life import TRAIT_ALLELES
from aerona.engine.mind.preferences import rows_of, write_pref
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record

SHARE = "share"
ALLELE = "allele"
WEALTH_UNITS = 10


async def blood_traits(ctx: TickContext, alive: list[EntityRow], held_traits: set[HouseTrait]) -> list[HouseTrait]:
    need = ctx.rules.houses.trait_members
    found: list[HouseTrait] = []
    genomes = [genome for mortal in alive if (genome := await genome_of(ctx.session, mortal.id)) is not None]
    for trait, (locus, allele) in TRAIT_ALLELES.items():
        if trait in held_traits:
            continue
        carriers = sum(1 for genome in genomes if phenotype(genome.genes, locus) == allele or allele in (genome.genes.get(locus.value) or [])[:1])
        if carriers >= need:
            found.append(trait)
    return found


async def tend_resemblance(ctx: TickContext, house: EntityRow, alive: list[EntityRow]) -> bool:
    if held(house.id):
        return False
    table = ctx.rules.genetics
    row = await ctx.session.get(HouseResemblanceRow, house.id)
    if row is not None and {ALLELE, SHARE} & set(row.locked or []):
        return False
    genomes = [genome for mortal in alive if (genome := await genome_of(ctx.session, mortal.id)) is not None]
    best: tuple[int, str, str] | None = None
    if len(genomes) >= table.resemblance_members:
        for locus in LOOKS_LOCI:
            counts = Counter(phenotype(genome.genes, locus) for genome in genomes)
            allele, count = max(counts.items(), key=lambda item: (item[1], item[0]))
            share = round_half_up(count * PERCENT / len(genomes))
            if share >= table.resemblance_share and (best is None or share > best[0]):
                best = (share, locus.value, allele)
    if best is None:
        if row is not None:
            await ctx.session.delete(row)
        return False
    share, locus_key, allele = best
    spec = LOCI[next(locus for locus in LOOKS_LOCI if locus.value == locus_key)]
    if row is None or row.locus is not spec.locus or row.allele != allele:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        ctx.session.add(HouseResemblanceRow(house_node_id=house.id, locus=spec.locus, allele=allele, share=share, since_epoch=ctx.epoch, locked=[]))
        await record(ctx, "genetics.resemblance", roles={IncidentRole.SUBJECT: house.id}, facts={"locus": spec.locus, "share": share})
        return True
    row.share = share
    return False


async def seed_looks(ctx: TickContext, people: EntityRow, pool: AllelePoolRow) -> int:
    if any(row.kind is PreferenceKind.LOOKS for row in await rows_of(ctx.session, people.id)):
        return 0
    table = ctx.rules.preferences
    made = 0
    for locus in LOOKS_LOCI:
        found = pool.frequencies.get(locus.value) or {}
        if not found:
            continue
        ranked = sorted(found.items(), key=lambda item: (-item[1], item[0]))
        await write_pref(ctx.session, people.id, PreferenceKind.LOOKS, f"{locus.value}:{ranked[0][0]}", table.seed_strength)
        made += 1
        if len(ranked) > 1:
            await write_pref(ctx.session, people.id, PreferenceKind.LOOKS, f"{locus.value}:{ranked[-1][0]}", -table.seed_strength // 2)
            made += 1
    return made


async def stance_effects(ctx: TickContext, pool: AllelePoolRow, members: list[tuple[EntityRow, GenomeRow]]) -> int:
    table = ctx.rules.gift
    touched = 0
    for mortal, genome in members:
        if held(mortal.id) or not gifted_schools(ctx.rules, genome.genes):
            continue
        profile = await ctx.session.get(MortalProfileRow, mortal.id)
        if profile is None:
            continue
        spec = GIFT_STANCES[pool.gift_stance]
        if spec.renown:
            mortal.importance = (mortal.importance or 0) + table.honour_renown
        if spec.fear_times:
            profile.stress = clamp_int(profile.stress + table.fear_stress * spec.fear_times, 0, PERCENT)
        if spec.taxed and "standing" not in (profile.locked or []):
            paid = min(profile.wealth, table.tax_wealth)
            profile.wealth -= paid
            town = await ctx.session.get(SettlementProfileRow, mortal.location_id) if mortal.location_id is not None else None
            if town is not None and "treasury" not in (town.locked or []) and not held(town.settlement_entity_id):
                town.treasury += paid * WEALTH_UNITS
        touched += 1
    return touched


async def examine_children(ctx: TickContext) -> int:
    table = ctx.rules.gift
    orders = await ctx.session.scalars(
        select(FactionProfileRow).where(FactionProfileRow.kind == FactionKind.MAGE_ORDER).order_by(FactionProfileRow.faction_entity_id)
    )
    taken = 0
    for order in orders:
        home = order.home_entity_id
        faction = await ctx.session.get(EntityRow, order.faction_entity_id)
        if home is None or faction is None or faction.status is not EntityStatus.CANON or held(faction.id):
            continue
        members = {bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF], targets=[faction.id])}
        children = await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [home]))
            .order_by(EntityRow.id)
        )
        for child in children:
            if child.id in members or held(child.id) or (stat(child, "age") or 0) > table.test_age:
                continue
            genome = await genome_of(ctx.session, child.id)
            schools = gifted_schools(ctx.rules, genome.genes) if genome is not None else []
            if not schools or not ctx.rng(f"genetics.test.{faction.id}.{child.id}.{ctx.epoch}").chance(table.recruit_pct):
                continue
            await connect(ctx.session, child.id, faction.id, BondKind.MEMBER_OF, ctx.epoch, description="tested and found gifted")
            taken += 1
            await record(
                ctx, "genetics.order_recruits", roles={IncidentRole.ACTOR: faction.id, IncidentRole.LEARNER: child.id}, facts={"school": schools[0]}, place=home
            )
    return taken
