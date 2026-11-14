from sqlalchemy import select

from aerona.catalog.body_plans import PLANS
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.society import AddictionRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission
from aerona.domain.enums.body import MADNESS_CONDITIONS, ConditionKind, DamageType, HarmCause, InjuryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.node import NodeKind
from aerona.engine.body.afflictions import active, afflict, cure, progress
from aerona.engine.body.book import ensure_species_body, injuries_of, recorded_plan, species_of, species_traits
from aerona.engine.body.cohorts import tend_cohorts
from aerona.engine.body.conditions import CONDITION_KEY, condition_of, end_condition, gain_condition
from aerona.engine.body.customs import SUFFERING_DOMAINS, customs_of, ensure_customs, maimed_for_rule, people_of
from aerona.engine.body.digits import backfill_digits
from aerona.engine.body.healing import heal_wounds
from aerona.engine.body.hits import Harm, weighted
from aerona.engine.body.state import has_reader, refresh
from aerona.engine.context import TickContext
from aerona.engine.cosmos.sanity import sanity_of
from aerona.engine.gods.queries import community_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.lifecycle.succession import pass_rule
from aerona.engine.lifecycle.wounds import apply_hits, fatal_injury
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import active_bonds, canon, connect, flags_by_entity, living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import ongoing_wars

VIOLENT_DEATHS: dict[EntityFlag, HarmCause] = {
    EntityFlag.FELL_IN_BATTLE: HarmCause.BATTLE,
    EntityFlag.DIED_IN_SIEGE: HarmCause.BATTLE,
    EntityFlag.SLAIN_IN_CAPTIVITY: HarmCause.TORTURE,
    EntityFlag.DIED_IN_DISASTER: HarmCause.DISASTER,
}
BACKFILL_CAUSE = "fell long ago"
PLAN_FIXUP = "body.species_plans"
EXPOSED_ROLES = frozenset(
    {MortalRole.EXPLORER, MortalRole.WARRIOR, MortalRole.KNIGHT, MortalRole.HUNTER, MortalRole.CAPTAIN, MortalRole.HERO, MortalRole.OFFICER, MortalRole.PILOT}
)
COLD_BANDS = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
HOT_BANDS = frozenset({TemperatureBand.HOT, TemperatureBand.SEARING})


async def at_war(ctx: TickContext, mortal: EntityRow) -> bool:
    return mortal.location_id is not None and bool(await ongoing_wars(ctx.session, mortal.location_id))


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "table.applied_fixups",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.entity_tags",
    "table.entity_traits",
    "table.genomes",
    "table.holder_levels",
    "table.injuries",
    "table.item_profiles",
    "table.mortal_equipment",
    "table.nodes",
    "table.prostheses",
    "table.species_profiles",
    "table.tradition_profiles",
)
@writes("table.applied_fixups", "table.bodies", "table.body_customs", "table.injuries")
async def body_survey(ctx: TickContext) -> None:
    rules = ctx.rules
    ctx.count("digits_named", await backfill_digits(ctx.session, rules))
    known = set(await ctx.session.scalars(select(BodyRow.node_id)))
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        if species.id not in known and not held(species.id):
            await ensure_species_body(ctx.session, species)
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        await ensure_customs(ctx.session, rules, people)
    created = 0
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if mortal.id not in known and not held(mortal.id):
            await refresh(ctx.session, rules, mortal, ctx.epoch)
            created += 1
    for son in await ctx.session.scalars(select(SonRow)):
        if son.id not in known and not held(son.id):
            await refresh(ctx.session, rules, son, ctx.epoch)
            created += 1
    for god in await ctx.session.scalars(select(ForeignGodRow)):
        if god.id not in known and not held(god.id):
            await refresh(ctx.session, rules, god, ctx.epoch)
            created += 1
    ctx.count("bodies", created)
    ctx.count("species_plans_reread", await reread_species_plans(ctx))
    await _backfill_fallen(ctx)


async def killer_cause(ctx: TickContext, killer_id: int) -> HarmCause:
    kind = await NodeRepository(ctx.session).kind_of(killer_id)
    if kind in (NodeKind.SON, NodeKind.FOREIGN_GOD):
        return HarmCause.GOD
    killer = await ctx.session.get(EntityRow, killer_id)
    if killer is None:
        return HarmCause.BATTLE
    if killer.entity_type in (EntityType.SPECIES, EntityType.OUTER_BEING):
        return HarmCause.MONSTER
    if killer.entity_type is EntityType.MORTAL:
        return HarmCause.DUEL
    return HarmCause.PUNISHMENT if killer.entity_type in COMMUNITY_TYPES else HarmCause.BATTLE


async def _backfill_fallen(ctx: TickContext) -> None:
    wounded = set(await ctx.session.scalars(select(InjuryRow.bearer_node_id).distinct()))
    killed = await ctx.session.execute(select(BondRow.target_node_id, BondRow.source_node_id).where(BondRow.kind == BondKind.KILLED).order_by(BondRow.id))
    killers = {victim: killer for victim, killer in killed}
    flagged: dict[int, HarmCause] = {}
    for flag, cause in VIOLENT_DEATHS.items():
        for mortal_id in await flags_by_entity(ctx.session, flag):
            flagged.setdefault(mortal_id, cause)
    for mortal_id in sorted(set(flagged) | set(killers)):
        if mortal_id in wounded:
            continue
        mortal = await ctx.session.get(EntityRow, mortal_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is EntityStatus.CANON:
            continue
        killer_id = killers.get(mortal_id)
        cause = flagged.get(mortal_id) or (await killer_cause(ctx, killer_id) if killer_id is not None else HarmCause.BATTLE)
        harm = Harm(ctx.rules.casualties.wound_hp, cause, BACKFILL_CAUSE, killer_id=killer_id, event_entity_id=mortal.death_event_entity_id)
        await fatal_injury(ctx, mortal, harm)
        wounded.add(mortal_id)
        ctx.count("backfilled")


async def reread_species_plans(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, PLAN_FIXUP) is not None:
        return 0
    wounded = set(await ctx.session.scalars(select(InjuryRow.bearer_node_id).distinct()))
    changed = 0
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        body = await ctx.session.get(BodyRow, species.id)
        if body is None or "plan" in body.locked:
            continue
        plan = await recorded_plan(ctx.session, species, await species_traits(ctx.session, species.id))
        if plan is body.plan:
            continue
        body.plan, body.height_class, body.build = plan, PLANS[plan].height, PLANS[plan].build
        changed += 1
        for mortal in await members_of(ctx, species):
            kin = await ctx.session.get(BodyRow, mortal.id)
            if kin is not None and mortal.id not in wounded and "plan" not in kin.locked:
                kin.plan = plan
    ctx.session.add(AppliedFixupRow(key=PLAN_FIXUP, result={"species": changed}))
    await ctx.session.flush()
    return changed


async def members_of(ctx: TickContext, species: EntityRow) -> list[EntityRow]:
    found: list[EntityRow] = []
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        kind = await species_of(ctx.session, mortal)
        if kind is not None and kind.id == species.id:
            found.append(mortal)
    return found


@reads(
    "cult.zeal",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "settlement.population",
    "table.avatars",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.cosmos",
    "table.crime_cases",
    "table.cult_doctrines",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.designated_heirs",
    "table.divine_wounds",
    "table.endemic_diseases",
    "table.entity_flags",
    "table.entity_tags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.goods_flows",
    "table.griefs",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.prostheses",
    "table.region_environment",
    "table.routes",
    "table.sacraments",
    "table.skills",
    "table.spirit_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.world_domain_hooks",
    "table.world_maps",
)
@writes(
    "mortal.death_year",
    "mortal.hp",
    "mortal.lifespan",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.conditions",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.griefs",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.item_history",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.personality_values",
    "table.sacraments",
    "table.skills",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
)
async def body_healing(ctx: TickContext) -> None:
    await heal_wounds(ctx)


def _madness_weights(ctx: TickContext) -> dict[ConditionKind, float]:
    table = ctx.rules.conditions
    return {
        ConditionKind.PARANOIA: table.paranoia_weight,
        ConditionKind.VISIONS: table.visions_weight,
        ConditionKind.RAGE: table.rage_weight,
        ConditionKind.MELANCHOLY: table.melancholy_weight,
    }


async def _exposure(ctx: TickContext, mortal: EntityRow, atlas: RegionAtlas, grounds: dict[int, RegionEnvironmentRow]) -> bool:
    if mortal.mortal_role not in EXPOSED_ROLES and not await at_war(ctx, mortal):
        return False
    region = atlas.top_region(mortal.id)
    ground = grounds.get(region) if region is not None else None
    if ground is None or ground.temperature_band not in COLD_BANDS | HOT_BANDS:
        return False
    table = ctx.rules.injury
    if not ctx.rng(seed_of("exposure", mortal.id, ctx.epoch)).chance(table.exposure_chance):
        return False
    cold = ground.temperature_band in COLD_BANDS
    harm = Harm(
        table.exposure_cold_hp if cold else table.exposure_heat_hp,
        HarmCause.EXPOSURE,
        "died of the bitter cold" if cold else "died of the burning heat",
        damage_type=DamageType.COLD if cold else DamageType.FIRE,
    )
    await apply_hits(ctx, mortal, harm, lethal=False)
    return True


async def _senses(ctx: TickContext, mortal: EntityRow) -> None:
    table = ctx.rules.conditions
    age, lifespan = stat(mortal, "age"), stat(mortal, "lifespan")
    if age is None or not lifespan:
        return
    share = age * PERCENT / lifespan
    if share >= table.age_blind_onset_pct:
        await gain_condition(ctx, mortal, ConditionKind.AGE_BLINDNESS, HarmCause.AGE, chance=table.age_blind_chance)
    if share >= table.age_deaf_onset_pct:
        await gain_condition(ctx, mortal, ConditionKind.AGE_DEAFNESS, HarmCause.AGE, chance=table.age_deaf_chance)


async def _madness(ctx: TickContext, mortal: EntityRow) -> None:
    table = ctx.rules.conditions
    sanity = sanity_of(ctx.rules, mortal)
    madness = [kind for kind in MADNESS_CONDITIONS if await condition_of(ctx, mortal.id, kind) is not None]
    if sanity >= table.madness_recover_sanity:
        rng = ctx.rng(seed_of("sane", mortal.id))
        for kind in madness:
            if rng.chance(table.madness_recover_chance):
                await end_condition(ctx, mortal, kind)
        return
    if sanity >= table.madness_sanity or madness:
        return
    rng = ctx.rng(seed_of("mad", mortal.id))
    if not rng.chance(table.madness_chance):
        return
    form = weighted(rng, _madness_weights(ctx))
    if form is not None:
        severity = 1 + (table.madness_sanity - sanity) // table.madness_severity_step
        await gain_condition(ctx, mortal, form, HarmCause.CURSE if sanity <= table.void_taint_sanity else HarmCause.AGE, severity=severity)


async def _addiction(ctx: TickContext, mortal: EntityRow, addicted: dict[int, AddictionRow]) -> None:
    table = ctx.rules.conditions
    community = await community_of(ctx.session, mortal)
    row = addicted.get(community.id) if community is not None else None
    addiction = await condition_of(ctx, mortal.id, ConditionKind.ADDICTION)
    dependence = next((item for item in await active(ctx.session, mortal.id) if item.package is PackageKind.DRUG_DEPENDENCE), None)
    if row is None or row.addicted_since_epoch is None:
        if dependence is not None and ctx.rng(seed_of("clean", mortal.id)).chance(table.addiction_recover_chance):
            await cure(ctx, mortal, dependence, CureKind.TIME)
        elif addiction is not None and dependence is None and ctx.rng(seed_of("clean", mortal.id)).chance(table.addiction_recover_chance):
            await end_condition(ctx, mortal, ConditionKind.ADDICTION)
        return
    if dependence is not None or addiction is not None:
        if addiction is not None and row.withdrawal_since_epoch is not None and table.withdrawal_severity:
            await gain_condition(
                ctx, mortal, ConditionKind.ADDICTION, HarmCause.POISON, severity=addiction.severity + table.withdrawal_severity, announce=False
            )
        return
    if ctx.rng(seed_of("condition", mortal.id, ConditionKind.ADDICTION.value)).chance(table.addiction_chance):
        await afflict(ctx, mortal, PackageKind.DRUG_DEPENDENCE, Transmission.INGESTION, source_node_id=row.resource_entity_id)


async def _marks(ctx: TickContext, mortal: EntityRow, flags: set[EntityFlag]) -> None:
    table = ctx.rules.conditions
    carried = {item.package: item for item in await active(ctx.session, mortal.id)}
    blessing = carried.get(PackageKind.DIVINE_BLESSING)
    if EntityFlag.CHOSEN in flags and blessing is None:
        patron = await living_patron(ctx.session, mortal)
        await afflict(ctx, mortal, PackageKind.DIVINE_BLESSING, Transmission.RITE, source_node_id=patron.id if patron else None)
    elif EntityFlag.CHOSEN not in flags and blessing is not None and blessing.transmission is Transmission.RITE:
        await cure(ctx, mortal, blessing, None)
    if EntityFlag.BLOODLINE_CURSE in flags and ctx.rng(seed_of("condition", mortal.id, ConditionKind.ENDLESS_HUNGER.value)).chance(table.hunger_curse_chance):
        await afflict(ctx, mortal, PackageKind.HUNGER_CURSE, Transmission.CURSE)
    injuries = await injuries_of(ctx.session, mortal.id)
    touched = [row for row in injuries if row.kind is InjuryKind.VOID_TOUCH]
    if touched and sanity_of(ctx.rules, mortal) <= table.void_taint_sanity:
        await afflict(ctx, mortal, PackageKind.VOID_TAINT, Transmission.CONTACT, source_node_id=touched[-1].cause_node_id)
    brands = [row for row in injuries if row.kind is InjuryKind.DIVINE_BRAND]
    if brands and await condition_of(ctx, mortal.id, ConditionKind.DIVINE_BRAND) is None:
        await gain_condition(
            ctx, mortal, ConditionKind.DIVINE_BRAND, HarmCause.GOD, severity=max(row.severity for row in brands), source_node_id=brands[-1].cause_node_id
        )
    illness = await condition_of(ctx, mortal.id, ConditionKind.CHRONIC_ILLNESS)
    if illness is not None and illness.source is HarmCause.DISASTER and ctx.rng(seed_of("illness", mortal.id)).chance(table.illness_recover_chance):
        await end_condition(ctx, mortal, ConditionKind.CHRONIC_ILLNESS)


SCHOLAR_ROLES = frozenset({MortalRole.SAGE, MortalRole.SCRIBE, MortalRole.SEER, MortalRole.PRIEST, MortalRole.SCIENTIST})


async def seek_reader(ctx: TickContext, scholar: EntityRow) -> EntityRow | None:
    body = await ctx.session.get(BodyRow, scholar.id)
    if scholar.mortal_role not in SCHOLAR_ROLES or body is None or body.scholarship >= ctx.rules.capacities.reader_sought_below_pct:
        return None
    if await has_reader(ctx.session, scholar):
        return None
    home = scholar.location_id
    if home is None:
        return None
    candidates = [
        mortal
        for mortal in await canon(ctx.session, [EntityType.MORTAL])
        if mortal.id != scholar.id and mortal.location_id == home and (stat(mortal, "age") or 0) < (stat(scholar, "age") or 0)
    ]
    if not candidates:
        return None
    reader = max(candidates, key=lambda mortal: (stat(mortal, "intellect") or 0, -mortal.id))
    await connect(ctx.session, reader.id, scholar.id, BondKind.APPRENTICE_OF, ctx.epoch, description="reads aloud to the blind master")
    await refresh(ctx.session, ctx.rules, scholar, ctx.epoch)
    await ctx.chronicle(
        ChronicleKind.LINEAGE,
        f"Blinded, {scholar.name} took {reader.name} as a reader; the young voice now carries the old books.",
        template_key="body.reader_taken",
        entity_ids=[scholar.id, reader.id],
        world_id=scholar.world_id,
    )
    return reader


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.addictions",
    "table.afflictions",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.conditions",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.entity_tags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.holder_levels",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.mind_attributes",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.prostheses",
    "table.region_environment",
    "table.tradition_profiles",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "mortal.hp",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.mortal_profiles",
    "table.traits",
)
async def body_conditions(ctx: TickContext) -> None:
    mortals = [mortal for mortal in await canon(ctx.session, [EntityType.MORTAL]) if mortal.status is EntityStatus.CANON]
    addicted = {row.community_entity_id: row for row in await ctx.session.scalars(select(AddictionRow))}
    repository = EntityRepository(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    exposed = 0
    for mortal in mortals:
        exposed += 1 if await _exposure(ctx, mortal, atlas, grounds) else 0
        if blocked(mortal.id, CONDITION_KEY):
            continue
        flags = await repository.flags(mortal.id)
        await seek_reader(ctx, mortal)
        await _senses(ctx, mortal)
        await _madness(ctx, mortal)
        await _marks(ctx, mortal, flags)
        if is_notable(ctx.rules, mortal, flags):
            await _addiction(ctx, mortal, addicted)
    ctx.count("weather_wounds", exposed)


async def _wholeness(ctx: TickContext) -> None:
    for bond in await active_bonds(ctx.session, [BondKind.RULES]):
        ruler = await living_entity(ctx.session, bond.source_node_id)
        if ruler is None or ruler.entity_type is not EntityType.MORTAL:
            continue
        custom = await customs_of(ctx.session, ctx.rules, ruler)
        if not maimed_for_rule(custom, await injuries_of(ctx.session, ruler.id)):
            continue
        heir = await pass_rule(ctx, ruler)
        if heir is None:
            continue
        people = await people_of(ctx.session, ruler)
        law = f"the law of {people.name}" if people is not None else "the law"
        await note(
            ctx,
            f"{ruler.name} was set aside, for {law} demands a ruler whole in body; {heir.name} took the throne.",
            key="body.ruler_set_aside",
            ids=[ruler.id, heir.id],
        )
        ctx.count("set_aside")


async def _recruit(ctx: TickContext) -> None:
    table = ctx.rules.body_customs
    cults = []
    for cult in await canon(ctx.session, [EntityType.CULT]):
        patron = await living_patron(ctx.session, cult)
        sanctified = await ctx.session.get(CultTenetRow, (cult.id, TenetKind.SACRED_SUFFERING)) is not None
        if sanctified or (patron is not None and set(patron.domains) & SUFFERING_DOMAINS):
            cults.append(cult)
    if not cults:
        return
    maimed = set(
        await ctx.session.scalars(select(InjuryRow.bearer_node_id).where(InjuryRow.kind.in_([InjuryKind.SEVERED, InjuryKind.GOUGED, InjuryKind.DESTROYED])))
    )
    for mortal_id in sorted(maimed):
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL:
            continue
        rng = ctx.rng(seed_of("maimed_cult", mortal.id))
        local = [cult for cult in cults if cult.world_id == mortal.world_id]
        if not local or await active_bonds(ctx.session, [BondKind.MEMBER_OF], sources=[mortal.id], targets=[cult.id for cult in local]):
            continue
        if rng.chance(table.maimed_cult_recruit):
            cult = rng.pick(local)
            await connect(ctx.session, mortal.id, cult.id, BondKind.MEMBER_OF, ctx.epoch, description="found holiness in their wounds")
            await note(
                ctx, f"{mortal.name}, maimed, found a welcome in {cult.name}, which holds suffering sacred.", key="body.maimed_cult", ids=[mortal.id, cult.id]
            )


@reads(
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.cult_tenets",
    "table.culture_values",
    "table.injuries",
    "table.maimed_cohorts",
    "table.nodes",
    "table.tradition_profiles",
)
@writes("people.prosperity", "settlement.prosperity", "table.body_customs", "table.entities", "table.maimed_cohorts")
async def body_society(ctx: TickContext) -> None:
    await tend_cohorts(ctx)
    await _wholeness(ctx)
    await _recruit(ctx)
    body_count = len(list(await ctx.session.scalars(select(BodyRow.node_id))))
    ctx.count("bodies_known", body_count)


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.sanity",
    "mortal.strength",
    "mortal.willpower",
    "table.afflictions",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.entities",
    "table.entity_flags",
    "table.genomes",
    "table.hero_quests",
    "table.holder_levels",
    "table.holder_techniques",
    "table.injuries",
    "table.item_profiles",
    "table.memories",
    "table.minds",
    "table.mortal_equipment",
    "table.needs",
    "table.nodes",
    "table.personality_values",
    "table.prostheses",
    "table.tradition_profiles",
    "table.traits",
    "table.worlds",
)
@writes(
    "mortal.sanity",
    "table.afflictions",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.injuries",
    "table.memories",
    "table.needs",
    "table.personality_values",
    "table.traits",
)
async def body_afflictions(ctx: TickContext) -> None:
    for key, value in (await progress(ctx)).items():
        ctx.count(f"afflictions_{key}", value)


PHASES = (
    Phase("body_survey", body_survey),
    Phase("body_healing", body_healing),
    Phase("body_conditions", body_conditions),
    Phase("body_afflictions", body_afflictions),
    Phase("body_society", body_society),
)
