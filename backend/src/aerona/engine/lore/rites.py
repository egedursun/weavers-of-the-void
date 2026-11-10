from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import DESPERATE_SCHOOLS, DOMAIN_SCHOOLS, RITE_TEMPLATES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow, WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import CastingRow, ItemEnchantmentRow, RiteEffectRow, RiteProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import ForcedWeatherRow, LeyLineRow, WorldSeasonRow
from aerona.db.tables.faith import PossessionRow, SpiritProfileRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, CaptiveCohortRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import BattleRow, WarSideRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import DamageType, HarmCause, InjuryState
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cosmography import PhenomenonCause, PhenomenonKind, RiftCause
from aerona.domain.enums.culture import (
    BacklashKind,
    CalendarSlot,
    CustomCatalog,
    MagicSchool,
    MagicSource,
    RiteEffectKind,
    SummonForm,
    Technique,
)
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import DivineScale, MagicSiteKind
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherEffect, WeatherKind
from aerona.domain.enums.faith import AfterlifeState, BindingKind, SpiritAlignment, TenetKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import ActKind, SkillKind, SkillSource, ValueAxis
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import RiteStats, SpiritStats
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.beings import banish_near, bind_near
from aerona.engine.cosmos.omens import celestial_rite_pct
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.cosmos.rifts import seal_near, tear_toward
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.divine.decrees import outlawed_schools
from aerona.engine.divine.laws import binds
from aerona.engine.dominion.book import DominionBook
from aerona.engine.dominion.sites import found_sites_in
from aerona.engine.ecology.control import spawn_beast
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.environment.control import force_weather
from aerona.engine.environment.local import weather_here
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.faith.souls import exorcise, seal_with, soul_near, unseal_with
from aerona.engine.genetics.genome import gift_factors
from aerona.engine.gods.interventions import apply_abundance
from aerona.engine.industry.pollution import void_scar
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.intrigue.names import name_power
from aerona.engine.intrigue.sources import hidden_rites
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.intel import gain_intel
from aerona.engine.lore.kinds import RiteEffectParams, kind_of, params_of
from aerona.engine.lore.research import has_technique
from aerona.engine.lore.truth import theory_factor
from aerona.engine.military.control import add_stack
from aerona.engine.mind.book import set_skill, values_for
from aerona.engine.mind.hooks import judged
from aerona.engine.mortal.learning import practise_subject, school_level
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, connect, living_entity, remove_flag
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, set_stats, stat

S = MagicSchool
E = RiteEffectKind
SCHOOL_TECHNIQUES = {S.WARDING: Technique.WARDING, S.SUMMONING: Technique.SUMMONING, S.DEATH: Technique.NECROMANCY, S.BINDING: Technique.SUMMONING}
SCHOOL_WEATHER = {S.ELEMENTAL_WATER: WeatherKind.RAIN, S.STORM: WeatherKind.STORM, S.ILLUSION: WeatherKind.FOG, S.ELEMENTAL_FIRE: WeatherKind.HEAT_WAVE}
SCHOOL_DAMAGE = {
    S.ELEMENTAL_FIRE: DamageType.FIRE,
    S.ELEMENTAL_WATER: DamageType.COLD,
    S.VOID: DamageType.VOID,
    S.STORM: DamageType.MAGIC,
    S.DEATH: DamageType.VOID,
}
SOURCE_BACKLASH = {
    MagicSource.LEY: BacklashKind.INJURY,
    MagicSource.DIVINE: BacklashKind.INJURY,
    MagicSource.BLOOD: BacklashKind.INJURY,
    MagicSource.SOUL: BacklashKind.ESCAPE,
    MagicSource.REAGENT: BacklashKind.INJURY,
    MagicSource.VOID: BacklashKind.LEAK,
}
HOSTILE = frozenset({E.DAMAGE, E.CURSE, E.SCRY})
MADDENING = frozenset({S.MIND, S.ILLUSION, S.DIVINATION})
DARK_SCHOOLS = frozenset({S.BLOOD, S.VOID})
DARK_SOURCES = frozenset({MagicSource.BLOOD, MagicSource.VOID})
DEFAULT_SCHOOLS = (S.DIVINATION, S.EARTH, S.LIFE)
ROW_FIXUP = "lore.rite_profiles"
PHENOMENON_KEY = "region.danger"


class RiteRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    technique: Technique | None = None
    skill: int | None = Field(default=None, ge=0, le=PERCENT)
    place: EntityType | None = None
    ley: bool = False
    slot: CalendarSlot | None = None
    sky: SkyEventKind | None = None
    participants: int | None = Field(default=None, ge=0)


def requirements_of(row: RiteProfileRow) -> RiteRequirements:
    try:
        return RiteRequirements.model_validate(row.requirements or {})
    except ValidationError as error:
        raise ValidationFailedError(f"Those are not the requirements of a rite: {error.errors()[0]['msg']}.") from error


def checked_requirements(values: dict[str, int | str | bool]) -> dict[str, int | str | bool]:
    try:
        return RiteRequirements.model_validate(values).model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    except ValidationError as error:
        raise ValidationFailedError(f"Those are not the requirements of a rite: {error.errors()[0]['msg']}.") from error


async def spellcraft(session: AsyncSession, mortal_id: int) -> int:
    level = await session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill == SkillKind.SPELLCRAFT).limit(1))
    return int(level or 0)


async def patron_of(ctx: TickContext, caster: EntityRow) -> int | None:
    found = await patron_node(ctx.session, caster.id)
    if found is None and caster.location_id is not None:
        found = await patron_node(ctx.session, caster.location_id)
    return found


async def patron_domains(ctx: TickContext, caster: EntityRow) -> list[Domain]:
    patron = await patron_of(ctx, caster)
    son = await ctx.session.get(SonRow, patron) if patron is not None else None
    if son is not None:
        return list(son.domains)
    god = await ctx.session.get(ForeignGodRow, patron) if patron is not None else None
    return [domain for domain in (god.domain_primary, god.domain_secondary) if domain is not None] if god is not None else []


async def schools_for(ctx: TickContext, caster: EntityRow) -> list[MagicSchool]:
    found: list[MagicSchool] = []
    for domain in await patron_domains(ctx, caster):
        found.extend(DOMAIN_SCHOOLS.get(domain, ()))
    values = await values_for(ctx.session, caster.id)
    if values.get(ValueAxis.MERCY, 0) <= ctx.rules.rites.desperate_mercy:
        found.extend(sorted(DESPERATE_SCHOOLS))
    allowed = []
    for school in dict.fromkeys(found or DEFAULT_SCHOOLS):
        technique = SCHOOL_TECHNIQUES.get(school)
        if technique is None or await has_technique(ctx.session, caster.location_id, technique):
            allowed.append(school)
    return allowed


async def rite_of(ctx: TickContext, school: MagicSchool) -> tuple[EntityRow, RiteProfileRow] | None:
    rows = await ctx.session.scalars(select(RiteProfileRow).where(RiteProfileRow.school == school).order_by(RiteProfileRow.rite_entity_id))
    for row in rows:
        rite = await living_entity(ctx.session, row.rite_entity_id)
        if rite is not None:
            return rite, row
    return None


def profile_for(ctx: TickContext, rite: EntityRow, school: MagicSchool, inventor_id: int | None) -> RiteProfileRow:
    template = RITE_TEMPLATES[school]
    row = RiteProfileRow(
        rite_entity_id=rite.id,
        school=school,
        source=template.source,
        requirements={"technique": SCHOOL_TECHNIQUES[school].value} if school in SCHOOL_TECHNIQUES else {},
        cost={},
        power=template.power,
        backlash_chance=clamp_int(template.power * ctx.rules.backlash.per_power_pct, 0, PERCENT),
        backlash=BacklashKind.MADNESS if school in MADDENING else SOURCE_BACKLASH[template.source],
        holy=template.source is MagicSource.DIVINE,
        heretical=school in DESPERATE_SCHOOLS,
        inventor_entity_id=inventor_id,
        forbidden_by=[],
        locked=[],
    )
    row.cost = cost_of(ctx, row, priced=False)
    ctx.session.add(row)
    for effect, magnitude in template.effects:
        ctx.session.add(
            RiteEffectRow(rite_entity_id=rite.id, effect=effect, magnitude=magnitude, damage_type=SCHOOL_DAMAGE.get(school) if effect is E.DAMAGE else None)
        )
    return row


async def devise(ctx: TickContext, school: MagicSchool, inventor: EntityRow) -> tuple[EntityRow, RiteProfileRow]:
    template = RITE_TEMPLATES[school]
    rite = await create_record(
        ctx,
        RecordSpec(
            name=template.name,
            entity_type=EntityType.RITE,
            stats=RiteStats(power=template.power, castings=0),
            body=f"A rite of the {school.value.replace('_', ' ')} school, first worked by {inventor.name}.",
            power=template.power,
            world_id=inventor.world_id,
            location_id=inventor.location_id,
        ),
    )
    row = profile_for(ctx, rite, school, inventor.id)
    await connect(ctx.session, inventor.id, rite.id, BondKind.OWNS, ctx.epoch, description="devised")
    return rite, row


def cost_of(ctx: TickContext, row: RiteProfileRow, *, priced: bool) -> dict[str, int]:
    table = ctx.rules.rites
    scale = table.magic_price_pct / PERCENT if priced else 1
    per = {
        MagicSource.DIVINE: ("essence", table.essence_per_power),
        MagicSource.BLOOD: ("blood", table.hp_per_power),
        MagicSource.SOUL: ("souls", 1),
        MagicSource.REAGENT: ("reagents", table.reagents_per_power),
        MagicSource.VOID: ("sanity", table.sanity_per_power),
    }
    if row.source is MagicSource.LEY:
        return {"ley": row.power}
    key, amount = per[row.source]
    return {key: max(1, round_half_up(amount * (1 if row.source is MagicSource.SOUL else row.power) * scale))}


async def priced(ctx: TickContext, caster: EntityRow) -> bool:
    laws = await ctx.laws()
    return laws.has(NaturalLaw.MAGIC_PRICE, caster.world_id)


async def pay_divine(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
    patron = await patron_of(ctx, caster)
    son = await ctx.session.get(SonRow, patron) if patron is not None else None
    if son is not None and son.essence >= amount:
        son.essence -= amount
        return True
    god = await ctx.session.get(ForeignGodRow, patron) if patron is not None else None
    if god is not None and god.faith >= amount:
        god.faith -= amount
        return True
    return False


async def captives_of(ctx: TickContext, caster: EntityRow) -> CaptiveCohortRow | None:
    keepers = [caster.id, *([caster.location_id] if caster.location_id is not None else [])]
    return await ctx.session.scalar(
        select(CaptiveCohortRow).where(CaptiveCohortRow.captor_entity_id.in_(keepers), CaptiveCohortRow.count > 0).order_by(CaptiveCohortRow.id).limit(1)
    )


async def pay_blood(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
    cohort = await captives_of(ctx, caster)
    if cohort is not None:
        taken = min(cohort.count, max(1, amount // ctx.rules.rites.hp_per_captive))
        cohort.count -= taken
        if cohort.origin_entity_id is not None:
            await judged(ctx, caster.id, cohort.origin_entity_id, ActKind.HUMAN_SACRIFICE, note="blood of captives for a rite")
        return True
    harm = Harm(damage=amount, cause=HarmCause.SACRIFICE, death_cause="bled out working a blood rite", source_node_id=caster.id)
    await apply_hits(ctx, caster, harm, lethal=False)
    return True


async def pay_souls(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
    rows = list(
        await ctx.session.scalars(
            select(SpiritProfileRow)
            .where(SpiritProfileRow.state == AfterlifeState.WANDERING, SpiritProfileRow.binding == BindingKind.NONE)
            .order_by(SpiritProfileRow.spirit_entity_id)
            .limit(amount)
        )
    )
    if len(rows) < amount:
        return False
    for row in rows:
        row.state = AfterlifeState.CONSUMED
        spirit = await ctx.session.get(EntityRow, row.spirit_entity_id)
        if spirit is not None:
            spirit.status, spirit.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    return True


async def pay_reagents(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
    if caster.location_id is None:
        return False
    taken = await GoodsLedger(ctx.session, ctx.epoch).take_units(caster.location_id, CommodityKind.MAGICAL_REAGENTS, amount, GoodsFlow.CONSUMPTION)
    return taken >= amount


async def pay_sanity(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
    shift_sanity(ctx.rules, caster, -amount)
    return True


async def pay_ley(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
    atlas = await RegionAtlas.load(ctx.session)
    region = await ctx.session.get(EntityRow, atlas.top_region(caster.id) or 0)
    return region is not None and (stat(region, "magic") or 0) >= amount


PAYMENTS: dict[str, Callable[[TickContext, EntityRow, int], Awaitable[bool]]] = {
    "ley": pay_ley,
    "essence": pay_divine,
    "blood": pay_blood,
    "souls": pay_souls,
    "reagents": pay_reagents,
    "sanity": pay_sanity,
}


async def licence(ctx: TickContext, caster: EntityRow, realms: RealmBook) -> bool:
    fee = await law_param(ctx.session, caster.location_id or 0, LawKind.LICENSED_MAGIC, "fee")
    if fee is None:
        return True
    town = await ctx.session.get(SettlementProfileRow, caster.location_id or 0)
    realm = realms.realm_of(caster.location_id)
    if town is None or realm is None or town.treasury < int(fee):
        return False
    town.treasury -= int(fee)
    spend(ctx, realm, int(fee), TreasuryEntry.TAX, f"licence of the mage {caster.name}")
    return True


async def forbidders(ctx: TickContext, caster: EntityRow, realms: RealmBook) -> set[int]:
    found = {caster.id, *([caster.location_id] if caster.location_id is not None else [])}
    realm = realms.realm_of(caster.location_id or caster.id)
    if realm is not None:
        found.add(realm.profile.polity_entity_id)
    patron = await patron_of(ctx, caster)
    if patron is not None:
        found.add(patron)
    cults = await ctx.session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id.in_(list(found)), BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
    )
    found.update(cults)
    return found


async def lawful(ctx: TickContext, caster: EntityRow, row: RiteProfileRow, realms: RealmBook) -> str | None:
    home = caster.location_id or 0
    tenets = await faith_tenets(ctx.session, home)
    if row.forbidden_by and set(row.forbidden_by) & await forbidders(ctx, caster, realms):
        return "it is forbidden here"
    if TenetKind.ANTI_MAGIC in tenets and not row.holy:
        return "the faith forbids it"
    level = await law_param(ctx.session, home, LawKind.RITE_RESTRICTIONS, "level")
    if level is not None and row.power * 10 > PERCENT - int(level):
        return "the law restricts so strong a rite"
    if row.heretical and TenetKind.SANCTIFIED_MAGIC in tenets:
        return "the church brands it heresy"
    if row.school in await outlawed_schools(ctx):
        return "the council of the gods outlawed it"
    return None if await licence(ctx, caster, realms) else "no licence"


async def on_ley(ctx: TickContext, caster: EntityRow) -> bool:
    region = (await RegionAtlas.load(ctx.session)).top_region(caster.id)
    if region is None:
        return False
    line = await ctx.session.scalar(
        select(LeyLineRow.id).where((LeyLineRow.region_a_id == region) | (LeyLineRow.region_b_id == region), LeyLineRow.severed.is_(False)).limit(1)
    )
    return line is not None


async def gathering(ctx: TickContext, caster: EntityRow) -> int:
    if caster.entity_type is EntityType.MORTAL:
        return 1
    return headcount(caster) or int(stat(caster, "followers") or 0)


async def season_of(ctx: TickContext, caster: EntityRow, slot: CalendarSlot) -> bool:
    if slot is CalendarSlot.HOLY_DAY:
        return await ctx.session.scalar(select(SkyEventRow.id).where(SkyEventRow.epoch == ctx.epoch).limit(1)) is not None
    if slot is CalendarSlot.CAMPAIGN:
        sides = [caster.id, *([caster.location_id] if caster.location_id is not None else [])]
        return await ctx.session.scalar(select(WarSideRow.war_id).where(WarSideRow.entity_id.in_(sides), WarSideRow.left_epoch.is_(None)).limit(1)) is not None
    cold = WorldSeasonRow.temperature_shift < 0
    green = WorldSeasonRow.growth >= PERCENT // 2
    seasons = select(WorldSeasonRow).where(WorldSeasonRow.world_id == caster.world_id, cold if slot is CalendarSlot.MIDWINTER else green)
    return await ctx.session.scalar(seasons.limit(1)) is not None


async def sky_shows(ctx: TickContext, kind: str) -> bool:
    return await ctx.session.scalar(select(SkyEventRow.id).where(SkyEventRow.kind == kind, SkyEventRow.epoch == ctx.epoch).limit(1)) is not None


async def unmet(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> str | None:
    need = requirements_of(row)
    home = await living_entity(ctx.session, caster.location_id)
    mortal = caster.entity_type is EntityType.MORTAL
    checks = (
        (
            need.technique is not None and not await has_technique(ctx.session, caster.location_id or caster.id, Technique(need.technique)),
            "the technique is unknown here",
        ),
        (need.skill is not None and mortal and await spellcraft(ctx.session, caster.id) < need.skill, "the caster's spellcraft is too weak"),
        (need.place is not None and (home is None or home.entity_type is not EntityType(need.place)), "it must be worked in another kind of place"),
        (need.ley and not await on_ley(ctx, caster), "it needs a ley line"),
        (need.sky is not None and not await sky_shows(ctx, str(need.sky)), "the sky does not show the sign it needs"),
        (need.slot is not None and not await season_of(ctx, caster, CalendarSlot(need.slot)), "it is not the season for it"),
        (need.participants is not None and await gathering(ctx, caster) < need.participants, "too few take part"),
    )
    return next((reason for failed, reason in checks if failed), None)


async def dominion_price(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(caster.id)
    book = await DominionBook.load(ctx.session)
    patron = await patron_of(ctx, caster)
    factor = book.cost_factor(ctx.rules, patron, region) if patron is not None else 1.0
    death = max(0, -book.scale_at(ctx.rules, region, DivineScale.GROWTH))
    if row.school is MagicSchool.DEATH and death:
        factor *= max(0.0, 1 - death * ctx.rules.dominion.necromancy_per_step_pct / PERCENT)
    return factor


async def pay(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> bool:
    factor = await dominion_price(ctx, caster, row)
    for key, amount in cost_of(ctx, row, priced=await priced(ctx, caster)).items():
        if not await PAYMENTS[key](ctx, caster, max(1, round_half_up(amount * factor))):
            return False
    bloodless = not await binds(ctx, NaturalLaw.MAGIC_REQUIRES_BLOOD, caster)
    return bloodless or await pay_blood(ctx, caster, row.power * ctx.rules.natural_laws.blood_per_power)


async def victim_in(ctx: TickContext, place_id: int) -> EntityRow | None:
    statement = select(EntityRow).where(
        await present_among(ctx.session, [place_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    return await ctx.session.scalar(statement.order_by(EntityRow.id).limit(1))


async def wandering_near(ctx: TickContext, place_id: int) -> SpiritProfileRow | None:
    mortals = select(EntityRow.id).where(await present_among(ctx.session, [place_id]), EntityRow.entity_type == EntityType.MORTAL)
    statement = select(SpiritProfileRow).where(
        SpiritProfileRow.state == AfterlifeState.WANDERING, SpiritProfileRow.binding == BindingKind.NONE, SpiritProfileRow.origin_mortal_id.in_(mortals)
    )
    return await ctx.session.scalar(statement.order_by(SpiritProfileRow.spirit_entity_id).limit(1))


@dataclass(frozen=True)
class Working:
    caster: EntityRow
    target: EntityRow | None
    effect: RiteEffectRow
    magnitude: int
    row: RiteProfileRow


async def do_damage(ctx: TickContext, work: Working) -> str | None:
    target = work.target
    victim = target if target is not None and target.entity_type is EntityType.MORTAL else (await victim_in(ctx, target.id) if target is not None else None)
    if victim is None:
        return None
    kind = work.effect.damage_type or SCHOOL_DAMAGE.get(work.row.school, DamageType.MAGIC)
    harm = Harm(
        damage=work.magnitude * ctx.rules.rites.damage_per_power,
        cause=HarmCause.CURSE,
        death_cause="struck down by a rite",
        damage_type=kind,
        killer_id=work.caster.id,
        source_node_id=work.caster.id,
    )
    await apply_hits(ctx, victim, harm)
    return f"struck {victim.name} with {kind.value}"


async def do_heal(ctx: TickContext, work: Working) -> str | None:
    place = work.caster.location_id or 0
    mortals = select(EntityRow.id).where(
        await present_among(ctx.session, [place]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    wounds = list(
        await ctx.session.scalars(
            select(InjuryRow)
            .where(InjuryRow.bearer_node_id.in_(mortals), InjuryRow.state != InjuryState.LETHAL, InjuryRow.function_loss > 0)
            .order_by(InjuryRow.id)
        )
    )
    restore = work.magnitude * ctx.rules.rites.heal_per_power
    regrow = work.row.power >= ctx.rules.rites.regrow_power
    regrown = 0
    for wound in wounds[: work.magnitude]:
        if regrow and wound.state is InjuryState.PERMANENT:
            wound.function_loss, wound.state = 0, InjuryState.HEALED_SCAR
            regrown += 1
        else:
            wound.function_loss = max(0, wound.function_loss - restore)
    if not wounds:
        return None
    return f"mended {min(len(wounds), work.magnitude)} wounds" + (f" and made {regrown} lost limbs whole" if regrown else "")


async def countered(ctx: TickContext, region_id: int, caster: EntityRow, power: int) -> EntityRow | None:
    wards = select(RiteEffectRow.rite_entity_id).where(RiteEffectRow.effect == E.WARD)
    castings = await ctx.session.scalars(
        select(CastingRow).where(
            CastingRow.rite_entity_id.in_(wards), CastingRow.succeeded.is_(True), CastingRow.epoch >= ctx.epoch - 1, CastingRow.caster_entity_id != caster.id
        )
    )
    atlas = await RegionAtlas.load(ctx.session)
    for casting in castings:
        warder = await living_entity(ctx.session, casting.caster_entity_id)
        ward = await ctx.session.get(RiteProfileRow, casting.rite_entity_id)
        if warder is not None and ward is not None and atlas.top_region(warder.id) == region_id and ward.power >= power:
            return warder
    return None


async def do_weather(ctx: TickContext, work: Working) -> str | None:
    if work.row.power < ctx.rules.rites.weather_power:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    region = await ctx.session.get(EntityRow, atlas.top_region(work.target.id if work.target is not None else work.caster.id) or 0)
    kind = SCHOOL_WEATHER.get(work.row.school, WeatherKind.RAIN)
    if region is None or region.entity_type is not EntityType.REGION:
        return None
    warder = await countered(ctx, region.id, work.caster, work.row.power)
    if warder is not None:
        return f"the wards of {warder.name} turned the weather aside"
    await force_weather(ctx.session, region, kind, from_epoch=ctx.epoch, epochs=1, season_position=None)
    return f"called {kind.value.replace('_', ' ')} over {region.name}"


async def do_curse(ctx: TickContext, work: Working) -> str | None:
    if work.target is None:
        return None
    await add_flag(ctx.session, work.target.id, EntityFlag.CURSED, ctx.epoch)
    await connect(ctx.session, work.caster.id, work.target.id, BondKind.CURSED, ctx.epoch, description=f"by the rite {work.row.school.value}")
    return f"cursed {work.target.name}"


async def do_bless(ctx: TickContext, work: Working) -> str | None:
    home = await living_entity(ctx.session, work.caster.location_id)
    if home is None:
        return None
    await connect(ctx.session, work.caster.id, home.id, BondKind.BLESSED, ctx.epoch, description="by a rite")
    if stat(home, "prosperity") is not None:
        set_stats(home, prosperity=clamp_int((stat(home, "prosperity") or 0) + work.magnitude, 0, PERCENT))
    return f"blessed {home.name}"


async def do_ward(ctx: TickContext, work: Working) -> str | None:
    home = await living_entity(ctx.session, work.caster.location_id)
    if home is None:
        return None
    defense = stat(home, "defense")
    if defense is not None:
        set_stats(home, defense=clamp_int(defense + ctx.rules.intervention_effects.protection_defense_gain, 0, PERCENT))
    await add_flag(ctx.session, home.id, EntityFlag.PROTECTED, ctx.epoch)
    if work.row.power < ctx.rules.cosmic_beings.rite_banish_power:
        return f"warded {home.name}"
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(work.caster.id)
    done = [f"warded {home.name}"]
    driven = await banish_near(ctx, region, work.caster.name)
    if driven is not None:
        done.append(f"drove {driven} back to its dimension")
    sealed = await seal_near(ctx, region, work.caster.name)
    if sealed is not None:
        done.append("sealed the rift there")
    return " and ".join(done)


async def do_scry(ctx: TickContext, work: Working) -> str | None:
    if work.target is None or work.caster.location_id is None:
        return None
    await gain_intel(ctx, work.caster.location_id, work.target.id, work.magnitude * ctx.rules.rites.scry_intel)
    return f"scried the secrets of {work.target.name}"


async def do_bind(ctx: TickContext, work: Working) -> str | None:
    if work.row.power >= ctx.rules.cosmic_beings.rite_bind_power:
        region = (await RegionAtlas.load(ctx.session)).top_region(work.caster.id)
        bound = await bind_near(ctx, region, work.caster.id, work.caster.name)
        if bound is not None:
            return f"bound {bound} to serve"
    spirit = await wandering_near(ctx, work.caster.location_id or 0)
    if spirit is None:
        return None
    if "binding" in spirit.locked:
        return None
    spirit.binding, spirit.bound_entity_id, spirit.alignment = BindingKind.PLACE, work.caster.location_id, SpiritAlignment.GUARDIAN
    return "bound a wandering spirit as a guardian"


async def summon_beast(ctx: TickContext, work: Working) -> str | None:
    region = (await RegionAtlas.load(ctx.session)).top_region(work.caster.id)
    species = await ctx.session.scalar(
        select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == region).order_by(SpeciesRangeRow.abundance.desc()).limit(1)
    )
    if species is None:
        return None
    beast = await spawn_beast(ctx, species)
    profile = await ctx.session.get(BeastProfileRow, beast.id)
    if profile is not None:
        profile.temper, profile.bound_to_node_id = BeastTemper.BOUND, work.caster.id
    await connect(ctx.session, work.caster.id, beast.id, BondKind.COMMANDS, ctx.epoch, description="summoned")
    return f"called up {beast.name}"


async def do_summon(ctx: TickContext, work: Working) -> str | None:
    if work.effect.summon_form is SummonForm.BEAST:
        found = await summon_beast(ctx, work)
        if found is not None:
            return found
    if work.effect.summon_form is SummonForm.UNDEAD:
        return await do_raise(ctx, work)
    servant = await create_record(
        ctx,
        RecordSpec(
            name=f"Servant of {work.caster.name}",
            entity_type=EntityType.SPIRIT,
            stats=SpiritStats(),
            body=f"A spirit called across the veil by {work.caster.name}.",
            power=max(1, work.magnitude),
            world_id=work.caster.world_id,
            location_id=work.caster.location_id,
        ),
    )
    ctx.session.add(
        SpiritProfileRow(
            spirit_entity_id=servant.id,
            origin_mortal_id=work.caster.id,
            binding=BindingKind.PERSON,
            bound_entity_id=work.caster.id,
            alignment=SpiritAlignment.GUARDIAN,
            state=AfterlifeState.WANDERING,
        )
    )
    await connect(ctx.session, work.caster.id, servant.id, BondKind.COMMANDS, ctx.epoch, description="summoned")
    return f"summoned {servant.name}"


async def army_of(ctx: TickContext, caster: EntityRow) -> int | None:
    if caster.entity_type is EntityType.ARMY:
        return caster.id
    armies = select(EntityRow.id).where(EntityRow.entity_type == EntityType.ARMY, EntityRow.status == EntityStatus.CANON)
    return await ctx.session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == caster.id, BondRow.kind == BondKind.COMMANDS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(armies))
        .limit(1)
    )


async def claim_battle_dead(ctx: TickContext, wanted: int) -> int:
    battles = await ctx.session.scalars(select(BattleRow).where(BattleRow.epoch >= ctx.epoch - 1).order_by(BattleRow.id))
    claimed = 0
    for battle in battles:
        if claimed >= wanted:
            break
        raised = (battle.magic or {}).get("raised", 0)
        fallen = (battle.winner_losses + battle.loser_losses) * ctx.rules.rites.raise_dead_pct // PERCENT
        free = max(0, fallen - raised)
        take = min(free, wanted - claimed)
        if take > 0:
            battle.magic = {**(battle.magic or {}), "raised": raised + take}
            claimed += take
    return claimed


async def do_raise(ctx: TickContext, work: Working) -> str | None:
    army = await army_of(ctx, work.caster)
    if army is not None:
        count = await claim_battle_dead(ctx, work.magnitude * ctx.rules.rites.undead_per_power)
        if count > 0:
            await add_stack(ctx, army, UnitKind.GHOST_HOST, count)
            return f"raised {count} of the battle dead to march again"
    spirit = await wandering_near(ctx, work.caster.location_id or 0)
    if spirit is None:
        return None
    if "binding" in spirit.locked:
        return None
    spirit.binding, spirit.bound_entity_id, spirit.alignment = BindingKind.PERSON, work.caster.id, SpiritAlignment.VENGEFUL
    await connect(ctx.session, work.caster.id, spirit.spirit_entity_id, BondKind.COMMANDS, ctx.epoch, description="raised from the dead")
    return "raised a dead soul to serve"


async def do_fertility(ctx: TickContext, work: Working) -> str | None:
    home = await living_entity(ctx.session, work.caster.location_id)
    if home is None or not headcount(home):
        return None
    born = round_half_up(headcount(home) * work.magnitude / PERCENT / 10)
    if born <= 0:
        return None
    with flowing(FlowCategory.BIRTH):
        put_stat(ctx.rules, home, headcount_key(home), headcount(home) + born)
    return f"quickened {born} births"


async def do_harvest(ctx: TickContext, work: Working) -> str | None:
    home = await living_entity(ctx.session, work.caster.location_id)
    if home is None:
        return None
    await apply_abundance(ctx, home)
    return f"blessed the fields of {home.name}"


async def do_seal(ctx: TickContext, work: Working) -> str | None:
    caster, target, row = work.caster, work.target, work.row
    spirit_id = target.id if target is not None and target.entity_type is EntityType.SPIRIT else None
    if spirit_id is None:
        found = await soul_near(ctx, caster.location_id, sealed=False)
        spirit_id = found.spirit_entity_id if found is not None else None
    if spirit_id is None or not await seal_with(ctx, spirit_id, row.power):
        return None
    spirit = await ctx.session.get(EntityRow, spirit_id)
    return f"sealed {spirit.name if spirit is not None else 'a soul'} against return"


async def do_unseal(ctx: TickContext, work: Working) -> str | None:
    caster, target, row = work.caster, work.target, work.row
    spirit_id = target.id if target is not None and target.entity_type is EntityType.SPIRIT else None
    if spirit_id is None:
        found = await soul_near(ctx, caster.location_id, sealed=True)
        spirit_id = found.spirit_entity_id if found is not None else None
    if spirit_id is None:
        return None
    if not await unseal_with(ctx, spirit_id, row.power):
        return "the seal on the soul held"
    spirit = await ctx.session.get(EntityRow, spirit_id)
    return f"broke the seal on {spirit.name if spirit is not None else 'a soul'}"


async def do_exorcise(ctx: TickContext, work: Working) -> str | None:
    caster, target, row = work.caster, work.target, work.row
    host = target if target is not None and target.entity_type is EntityType.MORTAL else await possessed_near(ctx, caster.location_id)
    if host is None:
        return None
    if not await exorcise(ctx, host, row.power):
        return f"the spirit in {host.name} would not go"
    return f"drove the spirit out of {host.name}"


async def possessed_near(ctx: TickContext, place_id: int | None) -> EntityRow | None:
    if place_id is None:
        return None
    hosts = select(PossessionRow.host_entity_id)
    statement = select(EntityRow).where(await present_among(ctx.session, [place_id]), EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(hosts))
    return await ctx.session.scalar(statement.order_by(EntityRow.id).limit(1))


EFFECTS: dict[RiteEffectKind, Callable[[TickContext, Working], Awaitable[str | None]]] = {
    E.DAMAGE: do_damage,
    E.HEAL: do_heal,
    E.WEATHER_CHANGE: do_weather,
    E.CURSE: do_curse,
    E.BLESS: do_bless,
    E.WARD: do_ward,
    E.SCRY: do_scry,
    E.BIND: do_bind,
    E.SUMMON: do_summon,
    E.RAISE_DEAD: do_raise,
    E.FERTILITY: do_fertility,
    E.HARVEST_BLESSING: do_harvest,
    E.SEAL_SOUL: do_seal,
    E.UNSEAL_SOUL: do_unseal,
    E.EXORCISE: do_exorcise,
}


async def effects_of(ctx: TickContext, rite_id: int) -> list[RiteEffectRow]:
    return list(await ctx.session.scalars(select(RiteEffectRow).where(RiteEffectRow.rite_entity_id == rite_id).order_by(RiteEffectRow.effect)))


async def working(ctx: TickContext, caster: EntityRow, target: EntityRow | None, effect: RiteEffectRow, row: RiteProfileRow) -> Working:
    shaped = await shaped_working(ctx, caster, target, effect, row)
    boost = await celestial_rite_pct(ctx, caster.world_id, row.school)
    return replace(shaped, magnitude=round_half_up(shaped.magnitude * boost)) if boost != 1.0 else shaped


async def shaped_working(ctx: TickContext, caster: EntityRow, target: EntityRow | None, effect: RiteEffectRow, row: RiteProfileRow) -> Working:
    custom = await kind_of(ctx.session, effect.custom_kind_id, CustomCatalog.RITE_EFFECT)
    if custom is None:
        return Working(caster, target, effect, effect.magnitude, row)
    params = params_of(custom, RiteEffectParams)
    shaped_effect = RiteEffectRow(
        rite_entity_id=effect.rite_entity_id,
        effect=effect.effect,
        magnitude=effect.magnitude,
        detail=effect.detail,
        damage_type=DamageType(params.damage_type) if params.damage_type is not None else effect.damage_type,
        summon_form=SummonForm(params.summon_form) if params.summon_form is not None else effect.summon_form,
    )
    return replace(Working(caster, target, shaped_effect, effect.magnitude, row), magnitude=round_half_up(effect.magnitude * params.magnitude_pct / PERCENT))


async def phenomenon(ctx: TickContext, region: EntityRow) -> None:
    table = ctx.rules.backlash
    await force_weather(ctx.session, region, WeatherKind.MAGIC_STORM, from_epoch=ctx.epoch, epochs=table.phenomenon_epochs, season_position=None)
    await add_modifier(
        ctx.session,
        ModifierDraft(
            target_node_id=region.id,
            target_key=PHENOMENON_KEY,
            op=ModifierOp.ADD,
            magnitude=table.phenomenon_danger,
            source_kind=ModifierSource.PHENOMENON,
            reason_key="eternal_storm",
            start_epoch=ctx.epoch,
            end_epoch=ctx.epoch + table.phenomenon_epochs,
            stacking_group="eternal_storm",
        ),
    )
    await note(ctx, f"A rite gone wrong left a storm over {region.name} that will not die.", key="magic.eternal_storm", ids=[region.id])
    await form_phenomenon(ctx, PhenomenonKind.ETERNAL_STORM, region, PhenomenonCause.RITE_BACKLASH)


async def backlash(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> BacklashKind:
    table = ctx.rules.backlash
    kind = row.backlash
    if row.power >= table.phenomenon_power:
        kind = BacklashKind.PHENOMENON
    if row.school is MagicSchool.BLOOD and ctx.rng(f"blood_backlash.{caster.id}.{ctx.epoch}").chance(ctx.rules.effect_packages.backlash_blood_pct):
        await afflict(ctx, caster, PackageKind.VAMPIRISM, Transmission.RITE)
    if kind is BacklashKind.INJURY:
        await apply_hits(ctx, caster, Harm(damage=table.injury_hp, cause=HarmCause.MAGIC_BACKLASH, death_cause="consumed by a rite gone wrong"))
    elif kind is BacklashKind.MADNESS:
        shift_sanity(ctx.rules, caster, -table.injury_hp)
    elif kind is BacklashKind.LEAK:
        world = await ctx.session.get(WorldRow, caster.world_id or 0)
        if world is not None:
            world.leakage = clamp_int(world.leakage + table.leak_gain, 0, PERCENT)
        region = await ctx.session.get(EntityRow, caster.location_id) if caster.location_id is not None else None
        if (
            region is not None
            and region.entity_type is EntityType.REGION
            and ctx.rng(f"backlash_wound.{caster.id}").chance(ctx.rules.phenomena.backlash_chance)
        ):
            await form_phenomenon(ctx, PhenomenonKind.LEAK_WOUND, region, PhenomenonCause.RITE_BACKLASH)
        if world is not None and ctx.rng(f"backlash_rift.{caster.id}.{ctx.epoch}").chance(ctx.rules.rifts.backlash_chance):
            torn = region if region is not None and region.entity_type is EntityType.REGION else None
            await tear_toward(ctx, world, torn, RiftCause.RITE_BACKLASH, by_node_id=caster.id)
    elif kind is BacklashKind.ESCAPE:
        bound = await ctx.session.scalar(select(SpiritProfileRow).where(SpiritProfileRow.bound_entity_id == caster.id).limit(1))
        if bound is not None:
            bound.binding, bound.bound_entity_id, bound.alignment = BindingKind.NONE, None, SpiritAlignment.VENGEFUL
    else:
        atlas = await RegionAtlas.load(ctx.session)
        region = await ctx.session.get(EntityRow, atlas.top_region(caster.id) or 0)
        if region is not None and region.entity_type is EntityType.REGION:
            await phenomenon(ctx, region)
    return kind


async def infamy(ctx: TickContext, caster: EntityRow, row: RiteProfileRow, target: EntityRow | None) -> bool:
    if row.school not in DARK_SCHOOLS and row.source not in DARK_SOURCES:
        return False
    caster.importance = max(0, (caster.importance or 0) - ctx.rules.rites.dark_infamy)
    victim = target.id if target is not None else caster.location_id
    if victim is not None and victim != caster.id:
        await judged(ctx, caster.id, victim, ActKind.HUMAN_SACRIFICE, note="a dark rite")
    await note(
        ctx, f"{caster.name} worked dark magic, and all who heard of it shuddered.", key="magic.dark_rite", ids=[caster.id, *([victim] if victim else [])]
    )
    return True


def wanted(row: RiteProfileRow, effects: list[RiteEffectRow], target: EntityRow | None) -> bool:
    if target is None:
        return not all(effect.effect in HOSTILE for effect in effects)
    return any(effect.effect in HOSTILE for effect in effects) or row.school in DESPERATE_SCHOOLS


async def dampening(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> float:
    if row.school is not S.ELEMENTAL_FIRE:
        return 1.0
    weather = await weather_here(ctx, caster.id, f"rite.{caster.id}")
    wet = weather.effect(WeatherEffect.WET) if weather is not None else 0
    return max(0.0, 1 - wet / PERCENT * ctx.rules.rites.fire_wet_pct / PERCENT)


SCHOOL_ACTS = {MagicSchool.BLOOD: ActKind.BLOOD_MAGIC, MagicSchool.VOID: ActKind.VOID_MAGIC, MagicSchool.DEATH: ActKind.NECROMANCY}


async def site_factor(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(caster.id)
    if region is None:
        return 1.0
    table = ctx.rules.magic_sites
    factor = 1.0
    for site in await found_sites_in(ctx, atlas, region):
        if site.kind is MagicSiteKind.SCHOOL_SEAT and site.school is row.school:
            factor += table.school_pct * site.strength / PERCENT / PERCENT
        if site.kind is MagicSiteKind.WARD and row.school is MagicSchool.WARDING:
            factor += table.ward_pct * site.strength / PERCENT / PERCENT
    drain = max(0, -(await DominionBook.load(ctx.session)).scale_at(ctx.rules, region, DivineScale.MAGIC))
    if row.school is MagicSchool.WARDING:
        factor += drain * ctx.rules.dominion.ward_per_step_pct / PERCENT
    return factor


async def magic_factor(ctx: TickContext, caster: EntityRow) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    region = await ctx.session.get(EntityRow, atlas.top_region(caster.id) or 0)
    magic = stat(region, "magic") if region is not None else None
    if magic is None:
        return 1.0
    return max(0.0, 1 + (magic - PERCENT // 2) / PERCENT * ctx.rules.rites.magic_strength_pct / PERCENT)


async def cast(
    ctx: TickContext,
    caster: EntityRow,
    rite: EntityRow,
    row: RiteProfileRow,
    *,
    target: EntityRow | None,
    realms: RealmBook,
    forced: bool = False,
    paid: bool = False,
) -> CastingRow | None:
    if not forced and (await lawful(ctx, caster, row, realms) is not None or await unmet(ctx, caster, row) is not None):
        return None
    if not forced and not paid and not await pay(ctx, caster, row):
        return None
    rng = ctx.rng(f"rite.{rite.id}.{caster.id}.{ctx.epoch}")
    casting = CastingRow(
        rite_entity_id=rite.id,
        caster_entity_id=caster.id,
        target_entity_id=target.id if target is not None else None,
        epoch=ctx.epoch,
        succeeded=True,
        effect="",
    )
    mastery = await school_level(ctx.session, caster.id, rite.id)
    steadiness, strength = gift_factors(ctx.rules, await ctx.session.get(GenomeRow, caster.id), row.school)
    strength *= await name_power(ctx, caster.id, target)
    strength *= await ctx.hook_factor(caster.id, DomainHook.BLOOD_RITE)
    strength *= await magic_factor(ctx, caster)
    strength *= await site_factor(ctx, caster, row)
    await practise_subject(ctx.session, ctx.rules, caster.id, SkillKind.SPELLCRAFT, subject_id=rite.id, xp=ctx.rules.skills.spellcraft_xp, epoch=ctx.epoch)
    understood = await theory_factor(ctx.session, ctx.rules, caster.location_id or caster.id, TheoryDomain.MAGIC)
    if rng.chance(row.backlash_chance * steadiness * (1 - mastery / PERCENT * ctx.rules.skills.school_backlash_pct / PERCENT) / understood):
        casting.succeeded, casting.backlash = False, await backlash(ctx, caster, row)
        casting.effect = f"the rite turned on {caster.name} ({casting.backlash.value})"
    else:
        damp = await dampening(ctx, caster, row)
        works = [await working(ctx, caster, target, effect, row) for effect in await effects_of(ctx, rite.id)]
        done = [await EFFECTS[work.effect.effect](ctx, replace(work, magnitude=round_half_up(work.magnitude * damp * strength))) for work in works]
        if damp < 1:
            done.append("the wet weather smothered its fire")
        casting.effect = "; ".join(text for text in done if text)[:480] or "the rite was worked to no end"
        await infamy(ctx, caster, row, target)
    await judged(ctx, caster.id, target.id if target is not None else caster.id, SCHOOL_ACTS.get(row.school, ActKind.MAGIC_USE))
    await hidden_rites(ctx, caster, rite, row)
    if row.school is MagicSchool.VOID:
        await void_scar(ctx, target.id if target is not None else caster.id)
    set_stats(rite, castings=(stat(rite, "castings") or 0) + 1)
    ctx.session.add(casting)
    await ctx.session.flush()
    return casting


@dataclass(frozen=True)
class Design:
    name: str
    school: MagicSchool
    source: MagicSource | None
    power: int
    workings: tuple[tuple[RiteEffectKind, int, DamageType | None, SummonForm | None], ...]


async def design(ctx: TickContext, plan: Design, holder: EntityRow) -> tuple[EntityRow, RiteProfileRow]:
    rite = await create_record(
        ctx,
        RecordSpec(
            name=plan.name.strip() or RITE_TEMPLATES[plan.school].name,
            entity_type=EntityType.RITE,
            stats=RiteStats(power=plan.power, castings=0),
            body=f"A rite of the {plan.school.value.replace('_', ' ')} school, devised for {holder.name}.",
            power=plan.power,
            world_id=holder.world_id,
            location_id=holder.location_id if holder.entity_type is EntityType.MORTAL else holder.id,
        ),
    )
    row = profile_for(ctx, rite, plan.school, holder.id if holder.entity_type is EntityType.MORTAL else None)
    row.power = clamp_int(plan.power, 1, 10)
    if plan.source is not None:
        row.source, row.holy = plan.source, plan.source is MagicSource.DIVINE
    row.backlash_chance = clamp_int(row.power * ctx.rules.backlash.per_power_pct, 0, PERCENT)
    row.cost = cost_of(ctx, row, priced=False)
    await ctx.session.flush()
    await ctx.session.execute(delete(RiteEffectRow).where(RiteEffectRow.rite_entity_id == rite.id))
    workings: dict[RiteEffectKind, RiteEffectRow] = {}
    for effect, magnitude, damage, form in plan.workings:
        held = workings.get(effect)
        if held is not None:
            held.magnitude = clamp_int(held.magnitude + magnitude, 1, PERCENT)
            held.damage_type = held.damage_type or damage
            held.summon_form = held.summon_form or form
            continue
        strength = clamp_int(magnitude, 1, PERCENT)
        workings[effect] = RiteEffectRow(rite_entity_id=rite.id, effect=effect, magnitude=strength, damage_type=damage, summon_form=form)
    ctx.session.add_all(workings.values())
    await connect(ctx.session, holder.id, rite.id, BondKind.OWNS, ctx.epoch, description="devised")
    await ctx.session.flush()
    return rite, row


async def cast_by_son(ctx: TickContext, son: SonRow, rite: EntityRow, row: RiteProfileRow, *, vessel: EntityRow, target: EntityRow | None) -> CastingRow:
    cost = max(1, row.power * ctx.rules.rites.essence_per_power)
    if son.essence < cost:
        raise ValidationFailedError(f"{son.name} lacks the {cost} essence the rite asks.")
    son.essence -= cost
    casting = await cast(ctx, vessel, rite, row, target=target, realms=await RealmBook.load(ctx.session), forced=True)
    if casting is None:
        raise ValidationFailedError("The rite would not answer.")
    return casting


async def enchant(ctx: TickContext, caster: EntityRow, rite: EntityRow, row: RiteProfileRow) -> ItemEnchantmentRow | None:
    owned = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.ITEM, EntityRow.status == EntityStatus.CANON, EntityRow.maker_entity_id == caster.id)
        .order_by(EntityRow.id)
        .limit(1)
    )
    effects = await effects_of(ctx, rite.id)
    if owned is None or not effects:
        return None
    effect = effects[0]
    found = await ctx.session.get(ItemEnchantmentRow, (owned.id, effect.effect))
    if found is None:
        found = ItemEnchantmentRow(item_entity_id=owned.id, effect=effect.effect, strength=0, rite_entity_id=rite.id, since_epoch=ctx.epoch)
        ctx.session.add(found)
    found.strength = clamp_int(found.strength + effect.magnitude * row.power, 0, PERCENT)
    set_stats(owned, might=clamp_int((stat(owned, "might") or 0) + effect.magnitude, 0, PERCENT))
    return found


async def warded(ctx: TickContext, settlement_id: int) -> float:
    rites = select(RiteEffectRow.rite_entity_id).where(RiteEffectRow.effect == E.WARD)
    statement = select(CastingRow).where(
        CastingRow.rite_entity_id.in_(rites), CastingRow.succeeded.is_(True), CastingRow.epoch >= ctx.epoch - 1, CastingRow.caster_entity_id.is_not(None)
    )
    total = 0
    for casting in await ctx.session.scalars(statement):
        caster = await ctx.session.get(EntityRow, casting.caster_entity_id)
        row = await ctx.session.get(RiteProfileRow, casting.rite_entity_id)
        if caster is not None and row is not None and caster.location_id == settlement_id:
            total += row.power * ctx.rules.rites.ward_pct
    return 1 + min(PERCENT, total) / PERCENT


GENTLE = {
    True: frozenset({E.WARD, E.BLESS, E.HEAL, E.BIND, E.EXORCISE, E.SEAL_SOUL}),
    False: frozenset({E.HARVEST_BLESSING, E.FERTILITY, E.WEATHER_CHANGE, E.SUMMON}),
}


def fits(school: MagicSchool, *, hostile: bool, protective: bool) -> int:
    kinds = {effect for effect, _ in RITE_TEMPLATES[school].effects}
    if hostile:
        return 2 if kinds & HOSTILE else 0
    if kinds <= HOSTILE:
        return 0
    return 2 if kinds & GENTLE[protective] else 1


async def choose(ctx: TickContext, caster: EntityRow, *, hostile: bool, protective: bool) -> tuple[EntityRow, RiteProfileRow] | None:
    schools = [school for school in await schools_for(ctx, caster) if fits(school, hostile=hostile, protective=protective)]
    schools.sort(key=lambda school: -fits(school, hostile=hostile, protective=protective))
    rng = ctx.rng(f"rite.choose.{caster.id}.{ctx.epoch}")
    for school in schools:
        found = await rite_of(ctx, school)
        if found is not None:
            return found
        if rng.chance(ctx.rules.rites.invention_chance) and caster.entity_type is EntityType.MORTAL:
            return await devise(ctx, school, caster)
    return None


async def cult_rites(ctx: TickContext, realms: RealmBook) -> int:
    table = ctx.rules.rites
    worked = 0
    cults = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for cult in cults:
        if worked >= table.cap or not ctx.rng(f"rite.cult.{cult.id}.{ctx.epoch}").chance(table.cult_chance):
            continue
        holy = [school for school in await schools_for(ctx, cult) if RITE_TEMPLATES[school].source is MagicSource.DIVINE]
        found = next(iter([await rite_of(ctx, school) for school in holy]), None)
        if found is None:
            continue
        rite, row = found
        if await cast(ctx, cult, rite, row, target=None, realms=realms) is not None:
            worked += 1
    return worked


async def war_mages(ctx: TickContext, realms: RealmBook) -> int:
    table = ctx.rules.rites
    armies = await ctx.session.execute(
        select(ArmyProfileRow)
        .join(ArmyUnitRow, ArmyUnitRow.army_entity_id == ArmyProfileRow.army_entity_id)
        .where(ArmyUnitRow.kind == UnitKind.WAR_MAGES, ArmyUnitRow.count > 0, ArmyProfileRow.target_entity_id.is_not(None))
        .order_by(ArmyProfileRow.army_entity_id)
    )
    worked = 0
    for (profile,) in armies.unique().all():
        army = await living_entity(ctx.session, profile.army_entity_id)
        target = await living_entity(ctx.session, profile.target_entity_id)
        if army is None or target is None or worked >= table.cap:
            continue
        if not ctx.rng(f"rite.army.{army.id}.{ctx.epoch}").chance(table.army_chance):
            continue
        chosen = await choose(ctx, army, hostile=True, protective=False)
        if chosen is None:
            continue
        rite, row = chosen
        casting = await cast(ctx, army, rite, row, target=target, realms=realms)
        if casting is not None:
            worked += 1
            await note(
                ctx,
                f"The war mages of {army.name} worked {rite.name} against {target.name}: {casting.effect}.",
                key="magic.war_mages",
                ids=[army.id, rite.id, target.id],
            )
    return worked


async def enchantments(ctx: TickContext) -> int:
    bound = 0
    wizards = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.WIZARD)
    for caster in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(wizards), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)):
        if not ctx.rng(f"rite.enchant.{caster.id}.{ctx.epoch}").chance(ctx.rules.rites.enchant_chance):
            continue
        owned = await ctx.session.scalar(
            select(BondRow.target_node_id)
            .where(BondRow.source_node_id == caster.id, BondRow.kind == BondKind.OWNS)
            .join(RiteProfileRow, RiteProfileRow.rite_entity_id == BondRow.target_node_id)
            .limit(1)
        )
        rite = await living_entity(ctx.session, owned)
        row = await ctx.session.get(RiteProfileRow, owned) if owned is not None else None
        if rite is not None and row is not None and await enchant(ctx, caster, rite, row) is not None:
            bound += 1
    return bound


async def heresies(ctx: TickContext) -> int:
    marked = 0
    for row in await ctx.session.scalars(select(RiteProfileRow).order_by(RiteProfileRow.rite_entity_id)):
        if "heretical" in row.locked:
            continue
        rite = await living_entity(ctx.session, row.rite_entity_id)
        tenets = await faith_tenets(ctx.session, rite.location_id or 0) if rite is not None else set()
        heretical = row.school in DESPERATE_SCHOOLS or (TenetKind.ANTI_MAGIC in tenets and not row.holy)
        if heretical != row.heretical:
            row.heretical = heretical
            marked += 1
    return marked


async def school_of(ctx: TickContext, rite: EntityRow) -> MagicSchool:
    holder = await living_entity(ctx.session, rite.location_id)
    schools = await schools_for(ctx, holder) if holder is not None else []
    return schools[0] if schools else DEFAULT_SCHOOLS[0]


async def backfill(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, ROW_FIXUP) is not None:
        return 0
    made = 0
    profiled = select(RiteProfileRow.rite_entity_id)
    for rite in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.RITE, EntityRow.status != EntityStatus.REJECTED, EntityRow.id.not_in(profiled))
        )
    ):
        profile_for(ctx, rite, await school_of(ctx, rite), rite.maker_entity_id)
        made += 1
    wizards = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.WIZARD)
    for mortal in list(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(wizards)).order_by(EntityRow.id))):
        if (
            await ctx.session.scalar(
                select(SkillRow.holder_node_id).where(SkillRow.holder_node_id == mortal.id, SkillRow.skill == SkillKind.SPELLCRAFT).limit(1)
            )
            is None
        ):
            await set_skill(ctx.session, mortal.id, SkillKind.SPELLCRAFT, ctx.rules.rites.wizard_skill, epoch=ctx.epoch, source=SkillSource.BACKFILL)
            made += 1
    ctx.session.add(AppliedFixupRow(key=ROW_FIXUP, result={"rites": made}))
    await ctx.session.flush()
    return made


async def dispel(ctx: TickContext, rite_id: int) -> CastingRow | None:
    casting = await ctx.session.scalar(
        select(CastingRow)
        .where(CastingRow.rite_entity_id == rite_id, CastingRow.succeeded.is_(True))
        .order_by(CastingRow.epoch.desc(), CastingRow.id.desc())
        .limit(1)
    )
    if casting is None:
        return None
    caster = await ctx.session.get(EntityRow, casting.caster_entity_id) if casting.caster_entity_id is not None else None
    atlas = await RegionAtlas.load(ctx.session)
    for effect in await effects_of(ctx, rite_id):
        if effect.effect is E.WEATHER_CHANGE and caster is not None:
            region = atlas.top_region(casting.target_entity_id or caster.id)
            await ctx.session.execute(delete(ForcedWeatherRow).where(ForcedWeatherRow.region_entity_id == region, ForcedWeatherRow.from_epoch >= casting.epoch))
        if effect.effect is E.WARD and caster is not None and caster.location_id is not None:
            await remove_flag(ctx.session, caster.location_id, EntityFlag.PROTECTED)
        if effect.effect is E.CURSE and casting.target_entity_id is not None:
            await remove_flag(ctx.session, casting.target_entity_id, EntityFlag.CURSED)
    casting.succeeded = False
    casting.effect = f"{casting.effect} (dispelled)"[:480]
    await ctx.session.flush()
    return casting
