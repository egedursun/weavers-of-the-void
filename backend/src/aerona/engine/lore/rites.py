from collections.abc import Awaitable, Callable

from sqlalchemy import select

from aerona.catalog.lore import DESPERATE_SCHOOLS, DOMAIN_SCHOOLS, RITE_TEMPLATES
from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import CastingRow, ItemEnchantmentRow, RiteEffectRow, RiteProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.faith import PossessionRow, SpiritProfileRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import HarmCause, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import BacklashKind, MagicSchool, MagicSource, RiteEffectKind, Technique
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.faith import AfterlifeState, BindingKind, SpiritAlignment, TenetKind
from aerona.domain.enums.military import SpyCover
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.entity_stats import RiteStats, SpiritStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.environment.control import force_weather
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.faith.souls import exorcise, seal_with, soul_near, unseal_with
from aerona.engine.gods.interventions import apply_abundance
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import values_for
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, set_stats, stat

S = MagicSchool
E = RiteEffectKind
SCHOOL_TECHNIQUES = {S.WARDING: Technique.WARDING, S.SUMMONING: Technique.SUMMONING, S.DEATH: Technique.NECROMANCY, S.BINDING: Technique.SUMMONING}
SCHOOL_WEATHER = {S.ELEMENTAL_WATER: WeatherKind.RAIN, S.STORM: WeatherKind.STORM, S.ILLUSION: WeatherKind.FOG, S.ELEMENTAL_FIRE: WeatherKind.HEAT_WAVE}
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
DEFAULT_SCHOOLS = (S.DIVINATION, S.EARTH, S.LIFE)
SPIRIT_STATS = "spirit"


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
        inventor_entity_id=inventor.id,
        locked=[],
    )
    row.cost = cost_of(ctx, row, priced=False)
    ctx.session.add(row)
    for effect, magnitude in template.effects:
        ctx.session.add(RiteEffectRow(rite_entity_id=rite.id, effect=effect, magnitude=magnitude))
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


async def pay_blood(ctx: TickContext, caster: EntityRow, amount: int) -> bool:
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


async def lawful(ctx: TickContext, caster: EntityRow, row: RiteProfileRow, realms: RealmBook) -> str | None:
    home = caster.location_id or 0
    tenets = await faith_tenets(ctx.session, home)
    if TenetKind.ANTI_MAGIC in tenets and not row.holy:
        return "the faith forbids it"
    level = await law_param(ctx.session, home, LawKind.RITE_RESTRICTIONS, "level")
    if level is not None and row.power * 10 > PERCENT - int(level):
        return "the law restricts so strong a rite"
    if row.heretical and TenetKind.SANCTIFIED_MAGIC in tenets:
        return "the church brands it heresy"
    if not await licence(ctx, caster, realms):
        return "no licence"
    return None


async def pay(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> bool:
    for key, amount in cost_of(ctx, row, priced=await priced(ctx, caster)).items():
        if not await PAYMENTS[key](ctx, caster, amount):
            return False
    return True


async def gain_intel(ctx: TickContext, owner_id: int, target_id: int, amount: int) -> None:
    found = await ctx.session.scalar(
        select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == owner_id, SpyNetworkRow.target_entity_id == target_id).order_by(SpyNetworkRow.id).limit(1)
    )
    if found is None:
        found = SpyNetworkRow(
            owner_entity_id=owner_id,
            target_entity_id=target_id,
            agents=0,
            agent_ids=[],
            depth=0,
            exposure=0,
            cover=SpyCover.BEGGAR,
            since_epoch=ctx.epoch,
            intel=0,
        )
        ctx.session.add(found)
    found.intel = clamp_int(found.intel + amount, 0, PERCENT)
    found.last_operation, found.last_epoch = "scrying", ctx.epoch


async def victim_in(ctx: TickContext, place_id: int) -> EntityRow | None:
    statement = select(EntityRow).where(EntityRow.location_id == place_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    return await ctx.session.scalar(statement.order_by(EntityRow.id).limit(1))


async def wandering_near(ctx: TickContext, place_id: int) -> SpiritProfileRow | None:
    mortals = select(EntityRow.id).where(EntityRow.location_id == place_id, EntityRow.entity_type == EntityType.MORTAL)
    statement = select(SpiritProfileRow).where(
        SpiritProfileRow.state == AfterlifeState.WANDERING, SpiritProfileRow.binding == BindingKind.NONE, SpiritProfileRow.origin_mortal_id.in_(mortals)
    )
    return await ctx.session.scalar(statement.order_by(SpiritProfileRow.spirit_entity_id).limit(1))


async def do_damage(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    victim = target if target is not None and target.entity_type is EntityType.MORTAL else (await victim_in(ctx, target.id) if target is not None else None)
    if victim is None:
        return None
    harm = Harm(
        damage=magnitude * ctx.rules.rites.damage_per_power,
        cause=HarmCause.CURSE,
        death_cause="struck down by a rite",
        killer_id=caster.id,
        source_node_id=caster.id,
    )
    await apply_hits(ctx, victim, harm)
    return f"struck {victim.name}"


async def do_heal(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    place = caster.location_id or 0
    mortals = select(EntityRow.id).where(EntityRow.location_id == place, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    wounds = list(
        await ctx.session.scalars(
            select(InjuryRow)
            .where(InjuryRow.bearer_node_id.in_(mortals), InjuryRow.state != InjuryState.LETHAL, InjuryRow.function_loss > 0)
            .order_by(InjuryRow.id)
        )
    )
    restore = magnitude * ctx.rules.rites.heal_per_power
    for wound in wounds[:magnitude]:
        wound.function_loss = max(0, wound.function_loss - restore)
    return f"mended {min(len(wounds), magnitude)} wounds" if wounds else None


async def do_weather(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    if row.power < ctx.rules.rites.weather_power:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    region = await ctx.session.get(EntityRow, atlas.top_region(caster.id) or 0)
    kind = SCHOOL_WEATHER.get(row.school, WeatherKind.RAIN)
    if region is None or region.entity_type is not EntityType.REGION:
        return None
    await force_weather(ctx.session, region, kind, from_epoch=ctx.epoch, epochs=1, season_position=None)
    return f"called {kind.value.replace('_', ' ')} over {region.name}"


async def do_curse(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    if target is None:
        return None
    await add_flag(ctx.session, target.id, EntityFlag.CURSED, ctx.epoch)
    await connect(ctx.session, caster.id, target.id, BondKind.CURSED, ctx.epoch, description=f"by the rite {row.school.value}")
    return f"cursed {target.name}"


async def do_bless(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    home = await living_entity(ctx.session, caster.location_id)
    if home is None:
        return None
    await connect(ctx.session, caster.id, home.id, BondKind.BLESSED, ctx.epoch, description="by a rite")
    if stat(home, "prosperity") is not None:
        set_stats(home, prosperity=clamp_int((stat(home, "prosperity") or 0) + magnitude, 0, PERCENT))
    return f"blessed {home.name}"


async def do_ward(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    home = await living_entity(ctx.session, caster.location_id)
    if home is None:
        return None
    defense = stat(home, "defense")
    if defense is not None:
        set_stats(home, defense=clamp_int(defense + ctx.rules.intervention_effects.protection_defense_gain, 0, PERCENT))
    await add_flag(ctx.session, home.id, EntityFlag.PROTECTED, ctx.epoch)
    return f"warded {home.name}"


async def do_scry(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    if target is None or caster.location_id is None:
        return None
    await gain_intel(ctx, caster.location_id, target.id, magnitude * ctx.rules.rites.scry_intel)
    return f"scried the secrets of {target.name}"


async def do_bind(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    spirit = await wandering_near(ctx, caster.location_id or 0)
    if spirit is None:
        return None
    if "binding" in spirit.locked:
        return None
    spirit.binding, spirit.bound_entity_id, spirit.alignment = BindingKind.PLACE, caster.location_id, SpiritAlignment.GUARDIAN
    return "bound a wandering spirit as a guardian"


async def do_summon(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    servant = await create_record(
        ctx,
        RecordSpec(
            name=f"Servant of {caster.name}",
            entity_type=EntityType.SPIRIT,
            stats=SpiritStats(),
            body=f"A spirit called across the veil by {caster.name}.",
            power=max(1, magnitude),
            world_id=caster.world_id,
            location_id=caster.location_id,
        ),
    )
    ctx.session.add(
        SpiritProfileRow(
            spirit_entity_id=servant.id,
            origin_mortal_id=caster.id,
            binding=BindingKind.PERSON,
            bound_entity_id=caster.id,
            alignment=SpiritAlignment.GUARDIAN,
            state=AfterlifeState.WANDERING,
        )
    )
    await connect(ctx.session, caster.id, servant.id, BondKind.COMMANDS, ctx.epoch, description="summoned")
    return f"summoned {servant.name}"


async def do_raise(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    spirit = await wandering_near(ctx, caster.location_id or 0)
    if spirit is None:
        return None
    if "binding" in spirit.locked:
        return None
    spirit.binding, spirit.bound_entity_id, spirit.alignment = BindingKind.PERSON, caster.id, SpiritAlignment.VENGEFUL
    await connect(ctx.session, caster.id, spirit.spirit_entity_id, BondKind.COMMANDS, ctx.epoch, description="raised from the dead")
    return "raised a dead soul to serve"


async def do_fertility(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    home = await living_entity(ctx.session, caster.location_id)
    if home is None or not headcount(home):
        return None
    born = round_half_up(headcount(home) * magnitude / PERCENT / 10)
    if born <= 0:
        return None
    with flowing(FlowCategory.BIRTH):
        put_stat(ctx.rules, home, headcount_key(home), headcount(home) + born)
    return f"quickened {born} births"


async def do_harvest(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    home = await living_entity(ctx.session, caster.location_id)
    if home is None:
        return None
    await apply_abundance(ctx, home)
    return f"blessed the fields of {home.name}"


async def do_seal(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
    spirit_id = target.id if target is not None and target.entity_type is EntityType.SPIRIT else None
    if spirit_id is None:
        found = await soul_near(ctx, caster.location_id, sealed=False)
        spirit_id = found.spirit_entity_id if found is not None else None
    if spirit_id is None or not await seal_with(ctx, spirit_id, row.power):
        return None
    spirit = await ctx.session.get(EntityRow, spirit_id)
    return f"sealed {spirit.name if spirit is not None else 'a soul'} against return"


async def do_unseal(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
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


async def do_exorcise(ctx: TickContext, caster: EntityRow, target: EntityRow | None, magnitude: int, row: RiteProfileRow) -> str | None:
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
    statement = select(EntityRow).where(EntityRow.location_id == place_id, EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(hosts))
    return await ctx.session.scalar(statement.order_by(EntityRow.id).limit(1))


EFFECTS: dict[RiteEffectKind, Callable[[TickContext, EntityRow, EntityRow | None, int, RiteProfileRow], Awaitable[str | None]]] = {
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


async def backlash(ctx: TickContext, caster: EntityRow, row: RiteProfileRow) -> BacklashKind:
    table = ctx.rules.backlash
    kind = row.backlash
    if row.power >= table.phenomenon_power:
        kind = BacklashKind.PHENOMENON
    if kind is BacklashKind.INJURY:
        await apply_hits(ctx, caster, Harm(damage=table.injury_hp, cause=HarmCause.MAGIC_BACKLASH, death_cause="consumed by a rite gone wrong"))
    elif kind is BacklashKind.MADNESS:
        shift_sanity(ctx.rules, caster, -table.injury_hp)
    elif kind is BacklashKind.LEAK:
        world = await ctx.session.get(WorldRow, caster.world_id or 0)
        if world is not None:
            world.leakage = clamp_int(world.leakage + table.leak_gain, 0, PERCENT)
    elif kind is BacklashKind.ESCAPE:
        bound = await ctx.session.scalar(select(SpiritProfileRow).where(SpiritProfileRow.bound_entity_id == caster.id).limit(1))
        if bound is not None:
            bound.binding, bound.bound_entity_id, bound.alignment = BindingKind.NONE, None, SpiritAlignment.VENGEFUL
    else:
        atlas = await RegionAtlas.load(ctx.session)
        region = await ctx.session.get(EntityRow, atlas.top_region(caster.id) or 0)
        if region is not None and region.entity_type is EntityType.REGION:
            await force_weather(ctx.session, region, WeatherKind.MAGIC_STORM, from_epoch=ctx.epoch, epochs=1, season_position=None)
    return kind


def wanted(row: RiteProfileRow, effects: list[RiteEffectRow], target: EntityRow | None) -> bool:
    if target is None:
        return not all(effect.effect in HOSTILE for effect in effects)
    return any(effect.effect in HOSTILE for effect in effects) or row.school in DESPERATE_SCHOOLS


async def cast(
    ctx: TickContext, caster: EntityRow, rite: EntityRow, row: RiteProfileRow, *, target: EntityRow | None, realms: RealmBook, forced: bool = False
) -> CastingRow | None:
    if not forced and (await lawful(ctx, caster, row, realms) is not None or not await pay(ctx, caster, row)):
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
    if rng.chance(row.backlash_chance):
        casting.succeeded, casting.backlash = False, await backlash(ctx, caster, row)
        casting.effect = f"the rite turned on {caster.name} ({casting.backlash.value})"
    else:
        done = [await EFFECTS[effect.effect](ctx, caster, target, effect.magnitude, row) for effect in await effects_of(ctx, rite.id)]
        casting.effect = "; ".join(text for text in done if text)[:480] or "the rite was worked to no end"
    set_stats(rite, castings=(stat(rite, "castings") or 0) + 1)
    ctx.session.add(casting)
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
        if rng.chance(ctx.rules.rites.invention_chance):
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
