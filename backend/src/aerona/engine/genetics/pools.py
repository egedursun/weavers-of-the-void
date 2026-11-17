from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.genetics import GIFT_LOCI_ORDER, LOCI, LocusSpec
from aerona.catalog.kinds.gifts import GIFT_STANCES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.nature import SenseProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.ecology import SizeClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.genetics import GiftStance, Locus
from aerona.domain.enums.mind import ActKind, ValueHolder
from aerona.domain.enums.nature import SenseKind, Thermoregulation
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import gifted_schools
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.ethics import ethic_reading
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up

JITTER = 50
LEAN = 60
GIFT_ALLELES = ("gifted", "wild")
FREQUENCIES = "frequencies"
STANCE = "gift_stance"
SHARE = "gifted_share"
COHORTS = "cohort_shares"
HOT = frozenset({TemperatureBand.WARM, TemperatureBand.HOT, TemperatureBand.SEARING})
COLD = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
LARGE = frozenset({SizeClass.LARGE, SizeClass.HUGE, SizeClass.COLOSSAL})
SENSE_LOCI: dict[Locus, SenseKind] = {
    Locus.SIGHT: SenseKind.SIGHT,
    Locus.NIGHT_VISION: SenseKind.NIGHT_VISION,
    Locus.SMELL: SenseKind.SMELL,
    Locus.HEARING: SenseKind.HEARING,
}


def normalised(weights: dict[str, float]) -> dict[str, int]:
    total = sum(weights.values()) or 1.0
    shares = {key: round_half_up(value * PERCENT / total) for key, value in weights.items()}
    gap = PERCENT - sum(shares.values())
    if gap and shares:
        first = max(shares, key=lambda key: (shares[key], key))
        shares[first] = max(0, shares[first] + gap)
    return shares


def climate_lean(locus: Locus, biology: PeopleBiologyRow) -> int:
    cold = biology.acclimatised in COLD
    hot = biology.acclimatised in HOT or biology.thermoregulation is Thermoregulation.ECTOTHERM
    if locus is Locus.COLD_TOLERANCE:
        return 1 if cold else -1 if hot else 0
    if locus is Locus.HEAT_TOLERANCE:
        return 1 if hot else -1 if cold else 0
    return 0


def leaned(spec: LocusSpec, rng: SeededRandom, biology: PeopleBiologyRow | None, senses: Mapping[SenseKind, int] | None = None) -> dict[str, int]:
    weights = {allele.key: allele.weight * (PERCENT + rng.integer(-JITTER, JITTER)) / PERCENT for allele in spec.alleles}
    sense = SENSE_LOCI.get(spec.locus)
    if sense is not None and senses and sense in senses:
        tilt = (senses[sense] - PERCENT // 2) / (PERCENT // 2)
        for allele in spec.alleles:
            weights[allele.key] *= max(0.01, (PERCENT + allele.score * tilt * LEAN) / PERCENT)
    if biology is not None:
        if spec.locus is Locus.SKIN:
            for allele in spec.alleles:
                if biology.acclimatised in HOT:
                    weights[allele.key] *= (PERCENT + allele.score * LEAN // 5) / PERCENT
                elif biology.acclimatised in COLD:
                    weights[allele.key] *= (PERCENT + (5 - allele.score) * LEAN // 5) / PERCENT
        if spec.locus in (Locus.HEIGHT, Locus.GIANT_BLOOD, Locus.MUSCLE, Locus.BONE_DENSITY) and biology.size_class in LARGE:
            for allele in spec.alleles:
                weights[allele.key] *= (PERCENT + max(0, allele.score) * LEAN) / PERCENT
        lean = climate_lean(spec.locus, biology)
        if lean:
            for allele in spec.alleles:
                weights[allele.key] *= max(1, PERCENT + allele.score * lean * LEAN) / PERCENT
    return normalised(weights)


async def seed_pool(ctx: TickContext, people: EntityRow) -> AllelePoolRow:
    biology = await ctx.session.get(PeopleBiologyRow, people.id)
    senses = {row.sense: row.acuity for row in await ctx.session.scalars(select(SenseProfileRow).where(SenseProfileRow.holder_entity_id == people.id))}
    rng = ctx.rng(f"genetics.pool.{people.id}")
    row = AllelePoolRow(
        people_node_id=people.id,
        frequencies={locus.value: leaned(spec, rng, biology, senses) for locus, spec in LOCI.items()},
        gift_stance=GiftStance.HONOURED,
        gifted_share=0,
        cohort_shares={},
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def members_by_people(ctx: TickContext) -> dict[int, list[tuple[EntityRow, GenomeRow]]]:
    statement = (
        select(EntityRow, GenomeRow)
        .join(GenomeRow, GenomeRow.holder_node_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found: dict[int, list[tuple[EntityRow, GenomeRow]]] = defaultdict(list)
    for mortal, genome in await ctx.session.execute(statement):
        people = await people_of(ctx.session, mortal)
        if people is not None:
            found[people.id].append((mortal, genome))
    return found


def observed(members: list[tuple[EntityRow, GenomeRow]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, float]] = {locus.value: defaultdict(float) for locus in LOCI}
    for _mortal, genome in members:
        for locus, spec in LOCI.items():
            for allele in (genome.genes.get(locus.value) or [])[:2]:
                if allele in spec.keys:
                    counts[locus.value][allele] += 1
    return {locus: normalised(dict(found)) for locus, found in counts.items() if found}


def drifted(rules_pct: int, current: dict[str, int], seen: dict[str, int]) -> dict[str, int]:
    keys = sorted(set(current) | set(seen))
    return normalised({key: current.get(key, 0) + (seen.get(key, 0) - current.get(key, 0)) * rules_pct / PERCENT for key in keys})


def shifted_gift(frequencies: dict[str, dict[str, int]], pct: int) -> dict[str, dict[str, int]]:
    moved = dict(frequencies)
    for locus in GIFT_LOCI_ORDER:
        found = dict(moved.get(locus.value) or {})
        if not found:
            continue
        for allele in GIFT_ALLELES:
            found[allele] = round_half_up(max(0, found.get(allele, 0) * (PERCENT + pct) / PERCENT))
        moved[locus.value] = normalised({key: float(value) for key, value in found.items()})
    return moved


async def stance_for(ctx: TickContext, people: EntityRow, laws: LawBook) -> GiftStance:
    table = ctx.rules.gift
    if laws.in_force(people.id, LawKind.MAGIC_BAN) is not None:
        return GiftStance.PERSECUTED
    if laws.in_force(people.id, LawKind.LICENSED_MAGIC) is not None:
        return GiftStance.TAXED
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    reading = await ethic_reading(ctx.session, ctx.rules, people.id, ActKind.MAGIC_USE, values)
    if reading < table.persecuted_at:
        return GiftStance.PERSECUTED
    if reading < table.feared_at:
        return GiftStance.FEARED
    if reading >= table.honoured_at:
        return GiftStance.HONOURED
    return GiftStance.TAXED


def hardy_weinberg(rules_gift_at: int, frequencies: dict[str, dict[str, int]], carrier: int, gifted: int, wild: int) -> int:
    best = 0.0
    for locus in GIFT_LOCI_ORDER:
        found = frequencies.get(locus.value) or {}
        p_gifted = found.get("gifted", 0) / PERCENT
        p_wild = found.get("wild", 0) / PERCENT
        share = 0.0
        if wild >= rules_gift_at:
            share += 1 - (1 - p_wild) ** 2
        if gifted >= rules_gift_at:
            share += p_gifted**2
        if carrier >= rules_gift_at:
            share += 2 * p_gifted * (1 - p_gifted - p_wild)
        best = max(best, share)
    return clamp_int(best * PERCENT, 0, PERCENT)


def gift_shares(ctx: TickContext, row: AllelePoolRow, members: list[tuple[EntityRow, GenomeRow]]) -> tuple[int, dict[str, int]]:
    table = ctx.rules.gift
    estimate = hardy_weinberg(table.gifted_at, row.frequencies, table.carrier_aptitude, table.gifted_aptitude, table.wild_aptitude)
    by_class: dict[str, list[bool]] = defaultdict(list)
    for mortal, genome in members:
        by_class[(mortal.social_class.value if mortal.social_class is not None else "common")].append(bool(gifted_schools(ctx.rules, genome.genes)))
    cohorts = {key: round_half_up(sum(flags) * PERCENT / len(flags)) for key, flags in sorted(by_class.items()) if flags}
    known = [flag for flags in by_class.values() for flag in flags]
    overall = round_half_up((sum(known) * PERCENT / len(known) + estimate) / 2) if known else estimate
    return clamp_int(overall, 0, PERCENT), cohorts


async def tend_pool(ctx: TickContext, people: EntityRow, row: AllelePoolRow, members: list[tuple[EntityRow, GenomeRow]], laws: LawBook) -> None:
    if held(people.id):
        return
    locked = set(row.locked or [])
    if FREQUENCIES not in locked:
        seen = observed(members)
        frequencies = {locus: drifted(ctx.rules.genetics.pool_drift_pct, current, seen.get(locus, current)) for locus, current in row.frequencies.items()}
        nature = await ctx.laws()
        shift = 0
        if nature.has(NaturalLaw.GIFT_FLOWERING, people.world_id):
            shift += ctx.rules.gift.law_shift_pct
        if nature.has(NaturalLaw.GIFT_WITHERING, people.world_id):
            shift -= ctx.rules.gift.law_shift_pct
        if GIFT_STANCES[row.gift_stance].culls_the_gift:
            shift -= ctx.rules.gift.persecution_pct
        shift += round(ctx.rules.gift.law_shift_pct * await ctx.hook_pct(people.id, DomainHook.BLOODLINE) / PERCENT)
        row.frequencies = shifted_gift(frequencies, shift) if shift else frequencies
    if STANCE not in locked:
        row.gift_stance = await stance_for(ctx, people, laws)
    share, cohorts = gift_shares(ctx, row, members)
    if SHARE not in locked:
        row.gifted_share = share
    if COHORTS not in locked:
        row.cohort_shares = cohorts
    row.epoch = ctx.epoch
