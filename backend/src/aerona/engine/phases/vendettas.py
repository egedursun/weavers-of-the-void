from sqlalchemy import func, select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import DuelContext, FeudAction, FeudParty, FeudStatus
from aerona.domain.enums.mind import ActKind, MemoryKind, TraitKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.storyteller import SpontaneousKind
from aerona.domain.enums.war import WarCause
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.causes import war_cause_incident
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.taboos import forbidden
from aerona.engine.lore.traditions import keeps
from aerona.engine.military.feuds import active_feuds, head_of, peace_mediator, realm_party, sides_of, temper
from aerona.engine.mind.book import traits_of, values_for
from aerona.engine.mind.opinion import mortal_rulers
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.warfare import Theatre, duel
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import move_stat, shift_stat, stat
from aerona.engine.records import death_path
from aerona.engine.services.community_relations import change_relation, end_blood_feud, open_feud, relation, start_blood_feud
from aerona.engine.services.war import declare_war
from aerona.engine.sites.rooms import delve, layout_of, rooms_of
from aerona.engine.storyteller.pace import paced

GRIEF = (MemoryKind.KILLED_KIN, MemoryKind.MAIMED_ME)
INSULTS = (MemoryKind.HUMILIATED_ME, MemoryKind.HARMED_ME, MemoryKind.BETRAYED_ME, MemoryKind.MAIMED_ME, MemoryKind.KILLED_KIN)


async def grief(ctx: TickContext, holder_id: int, subject_id: int) -> int:
    found = await ctx.session.scalar(
        select(func.coalesce(func.sum(MemoryRow.magnitude), 0)).where(
            MemoryRow.holder_node_id == holder_id, MemoryRow.subject_node_id == subject_id, MemoryRow.kind.in_(GRIEF), MemoryRow.magnitude < 0
        )
    )
    return -int(found or 0)


async def target_of(ctx: TickContext, enemy: EntityRow) -> EntityRow | None:
    head = await head_of(ctx, enemy)
    if head is not None:
        return head
    for ruler_id in await mortal_rulers(ctx.session, enemy.id):
        ruler = await living_entity(ctx.session, ruler_id)
        if ruler is not None:
            return ruler
    return None


async def choose(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> FeudAction | None:
    table = ctx.rules.vendetta
    rng = ctx.rng(f"vendetta.{avenger.id}.{enemy.id}.{ctx.epoch}")
    values = await values_for(ctx.session, avenger.id)
    if values.get(ValueAxis.PIETY, 0) > 0 and values.get(ValueAxis.MERCY, 0) > 0 and rng.chance(table.mediation_chance):
        return None
    if await law_param(ctx.session, avenger.id, LawKind.BLOOD_FEUD, "wergild_allowed") and rng.chance(table.wergild_chance):
        return FeudAction.DEMAND_WERGILD
    if rng.chance(table.escalate_chance):
        return FeudAction.ESCALATE
    if rng.chance(table.assassinate_chance):
        return FeudAction.ASSASSINATE
    if rng.chance(await paced(ctx, avenger.world_id, SpontaneousKind.RAID, table.raid_chance)):
        return FeudAction.RAID
    return FeudAction.REST


async def mediate(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    await end_blood_feud(ctx.session, avenger.id, enemy.id, epoch=ctx.epoch, status=FeudStatus.MEDIATED)
    return f"Priests of {avenger.name} mediated an end to its blood feud with {enemy.name}."


async def wergild(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    price = ctx.rules.treaties.wergild_value
    move_stat(enemy, avenger, "wealth", price // 10)
    await end_blood_feud(ctx.session, avenger.id, enemy.id, epoch=ctx.epoch)
    await change_relation(ctx, avenger.id, enemy.id, price // 3, MemoryKind.GIFTED_ME, note="wergild")
    return f"{enemy.name} paid {avenger.name} wergild and the blood feud was laid to rest."


async def escalate(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    first, second = await realm_party(ctx.session, avenger), await realm_party(ctx.session, enemy)
    if first != second and await declare_war(ctx, first, second, "the blood feud", cause=WarCause.VENDETTA):
        return f"The blood feud between {avenger.name} and {enemy.name} flared into open war."
    return None


async def assassinate(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    victim = await target_of(ctx, enemy)
    if victim is None:
        return None
    await death_path(
        ctx, victim, f"murdered in the blood feud with {avenger.name}", avenger.id, "feud killing", forced=True, harm=HarmCause.BATTLE, manner=DeathCause.MURDER
    )
    if enemy.entity_type is EntityType.HOUSE or avenger.entity_type is EntityType.HOUSE:
        await open_feud(ctx.session, ctx.rules, enemy.id, avenger.id, epoch=ctx.epoch, cause=f"the murder of {victim.name}", party=FeudParty.HOUSE)
    else:
        await start_blood_feud(ctx, enemy.id, avenger.id, f"the murder of {victim.name}")
    return f"An avenger of {avenger.name} murdered {victim.name} of {enemy.name}."


async def raid(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    hp = ctx.rules.vendetta.raid_hp
    victim = await target_of(ctx, enemy)
    if victim is not None:
        harm = Harm(hp, HarmCause.BATTLE, f"wounded in a feud raid by {avenger.name}", killer_id=avenger.id)
        await apply_hits(ctx, victim, harm, lethal=False)
    shift_stat(enemy, "prosperity", -hp // 5)
    walked = await walk_raided(ctx, avenger, enemy)
    return f"Kinsmen of {avenger.name} raided {enemy.name} to avenge their dead{walked}."


async def walk_raided(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str:
    leader = await target_of(ctx, avenger)
    if leader is None or frozen(leader.id) or (await layout_of(ctx, enemy) is None and not await rooms_of(ctx, enemy.id)):
        return ""
    walk = await delve(ctx, leader, enemy, ctx.rules.sites.raid_company)
    return f", and {leader.name} led them through {walk.cleared} of its halls"


async def rest(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    return None


ACTIONS = {
    FeudAction.DEMAND_WERGILD: wergild,
    FeudAction.ESCALATE: escalate,
    FeudAction.ASSASSINATE: assassinate,
    FeudAction.RAID: raid,
    FeudAction.REST: rest,
}


async def act(ctx: TickContext, action: FeudAction | None, avenger: EntityRow, enemy: EntityRow) -> str | None:
    return await (mediate if action is None else ACTIONS[action])(ctx, avenger, enemy)


async def feuds(ctx: TickContext) -> int:
    table = ctx.rules.vendetta
    acted = 0
    for row in await active_feuds(ctx.session):
        if acted >= table.cap:
            break
        pair = await sides_of(ctx, row)
        if pair is None:
            row.status, row.ended_epoch = FeudStatus.ENDED, ctx.epoch
            continue
        first, second = pair
        hatred = -await relation(ctx.session, ctx.rules, first.id, second.id) if row.party is FeudParty.COMMUNITY else row.grievance
        sides = [(await grief(ctx, first.id, second.id), first, second), (await grief(ctx, second.id, first.id), second, first)]
        pain, avenger, enemy = sorted(sides, key=lambda item: -item[0])[0]
        intensity = await temper(ctx, row, first, second, max(pain, hatred))
        if row.status is FeudStatus.FADED:
            await end_blood_feud(ctx.session, first.id, second.id, epoch=ctx.epoch, status=FeudStatus.FADED)
            await note(ctx, f"The old feud between {first.name} and {second.name} faded with the generations.", key="vendetta.faded", ids=[first.id, second.id])
            continue
        if intensity < table.grievance:
            continue
        mediated = await peace_mediator(ctx, first, second) and ctx.rng(f"peace_tenet.{row.id}.{ctx.epoch}").chance(table.peace_tenet_mediation)
        action = None if mediated else await choose(ctx, avenger, enemy)
        row.last_action, row.last_epoch = (action.value if action is not None else "mediated"), ctx.epoch
        text = await act(ctx, action, avenger, enemy)
        ctx.count(f"feud_{action.value if action is not None else 'mediated'}")
        if text is not None:
            acted += 1
            cause = await war_cause_incident(ctx.session, WarCause.VENDETTA, avenger.id, enemy.id, ctx.epoch)
            key = f"vendetta.{action.value if action is not None else 'mediated'}"
            roles = {avenger.id: IncidentRole.ACTOR, enemy.id: IncidentRole.TARGET}
            await note(ctx, text, key=key, ids=[avenger.id, enemy.id], kind=ChronicleKind.WAR, roles=roles, cause_incident_id=cause)
    return acted


async def honour_duels(ctx: TickContext) -> int:
    table = ctx.rules.duels
    statement = (
        select(MemoryRow.holder_node_id, MemoryRow.subject_node_id, func.sum(MemoryRow.magnitude).label("total"))
        .where(MemoryRow.kind.in_(INSULTS), MemoryRow.magnitude < 0)
        .group_by(MemoryRow.holder_node_id, MemoryRow.subject_node_id)
        .having(func.sum(MemoryRow.magnitude) <= -table.honour_grievance)
        .order_by(func.sum(MemoryRow.magnitude), MemoryRow.holder_node_id, MemoryRow.subject_node_id)
    )
    theatre: Theatre | None = None
    fought = 0
    seen: set[int] = set()
    for holder_id, subject_id, _ in (await ctx.session.execute(statement)).all():
        if fought >= table.honour_cap:
            break
        if holder_id in seen or subject_id in seen:
            continue
        holder, subject = await living_entity(ctx.session, holder_id), await living_entity(ctx.session, subject_id)
        if holder is None or subject is None or holder.entity_type is not EntityType.MORTAL or subject.entity_type is not EntityType.MORTAL:
            continue
        if holder.status is not EntityStatus.CANON or frozen(holder_id, subject_id):
            continue
        customary = holder.location_id is not None and await keeps(ctx, holder.location_id, TraditionKind.DUEL_CUSTOM)
        wrathful = TraitKind.WRATHFUL in await traits_of(ctx.session, holder.id)
        if not customary and not wrathful and (await values_for(ctx.session, holder.id)).get(ValueAxis.HONOUR, 0) <= 0:
            continue
        if stat(holder, "hp") == 0 or holder.location_id != subject.location_id:
            continue
        if await forbidden(ctx, holder.id, ActKind.DUELLING):
            continue
        theatre = theatre or await Theatre.load(ctx)
        text = await duel(ctx, theatre, holder, subject, war=None, anchor_id=None, context=DuelContext.HONOUR)
        await note(ctx, f"{holder.name} called {subject.name} out to settle a matter of honour.{text}", key="duel.honour", ids=[holder.id, subject.id])
        seen.update({holder.id, subject.id})
        fought += 1
    return fought


@reads(
    "item.damage",
    "item.might",
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
    "table.army_officers",
    "table.assistive_aids",
    "table.avatars",
    "table.beast_profiles",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.calendars",
    "table.captives",
    "table.claims",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.creator_taboos",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_values",
    "table.currencies",
    "table.deed_claims",
    "table.deeds",
    "table.districts",
    "table.divine_wounds",
    "table.entity_flags",
    "table.entity_tags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.feuds",
    "table.forced_weather",
    "table.geasa",
    "table.genomes",
    "table.goods",
    "table.holder_levels",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incubating_ideas",
    "table.injuries",
    "table.inspirations",
    "table.item_enchantments",
    "table.item_profiles",
    "table.kinship_systems",
    "table.law_profiles",
    "table.laws",
    "table.learned_tactics",
    "table.loans",
    "table.marriages",
    "table.memories",
    "table.mercenary_contracts",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.node_materials",
    "table.nodes",
    "table.nutrition_scores",
    "table.offices",
    "table.passions",
    "table.peace_terms",
    "table.personality_values",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.prostheses",
    "table.region_environment",
    "table.reputations",
    "table.routes",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.spirit_profiles",
    "table.spy_agents",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_profiles",
    "table.unit_designs",
    "table.vessel_profiles",
    "table.war_sides",
    "table.workshops",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "mortal.charisma",
    "mortal.death_year",
    "mortal.hp",
    "people.wealth",
    "settlement.wealth",
    "table.applied_fixups",
    "table.army_officers",
    "table.battle_casualties",
    "table.battle_stacks",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_stocks",
    "table.currencies",
    "table.deed_claims",
    "table.deeds",
    "table.districts",
    "table.entities",
    "table.epoch_year_cursors",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.item_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.offices",
    "table.peace_terms",
    "table.personality_values",
    "table.polity_profiles",
    "table.region_environment",
    "table.reputations",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.spy_agents",
    "table.spy_networks",
    "table.thoughts",
    "table.treaty_breaches",
    "table.vessel_profiles",
)
async def vendetta_cycles(ctx: TickContext) -> None:
    ctx.count("feud_actions", await feuds(ctx))
    ctx.count("honour_duels", await honour_duels(ctx))


PHASES = (Phase("vendetta_cycles", vendetta_cycles),)
