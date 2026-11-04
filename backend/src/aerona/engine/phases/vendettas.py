from sqlalchemy import func, select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import DuelContext, FeudAction
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.war import WarCause
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.causes import war_cause_incident
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.traditions import keeps
from aerona.engine.mind.book import values_for
from aerona.engine.mind.opinion import mortal_rulers
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.warfare import Theatre, duel
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.records import death_path
from aerona.engine.services.community_relations import blood_feud_pairs, change_relation, end_blood_feud, relation, start_blood_feud
from aerona.engine.services.war import declare_war

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
    if rng.chance(table.raid_chance):
        return FeudAction.RAID
    return FeudAction.REST


async def mediate(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    await end_blood_feud(ctx.session, avenger.id, enemy.id)
    return f"Priests of {avenger.name} mediated an end to its blood feud with {enemy.name}."


async def wergild(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    price = ctx.rules.treaties.wergild_value
    shift_stat(enemy, "wealth", -price // 10)
    shift_stat(avenger, "wealth", price // 10)
    await end_blood_feud(ctx.session, avenger.id, enemy.id)
    await change_relation(ctx, avenger.id, enemy.id, price // 3, MemoryKind.GIFTED_ME, note="wergild")
    return f"{enemy.name} paid {avenger.name} wergild and the blood feud was laid to rest."


async def escalate(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    if await declare_war(ctx, avenger.id, enemy.id, "the blood feud", cause=WarCause.VENDETTA):
        return f"The blood feud between {avenger.name} and {enemy.name} flared into open war."
    return None


async def assassinate(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    victim = await target_of(ctx, enemy)
    if victim is None:
        return None
    await death_path(ctx, victim, f"murdered in the blood feud with {avenger.name}", avenger.id, "feud killing", forced=True, harm=HarmCause.BATTLE)
    await start_blood_feud(ctx, enemy.id, avenger.id, f"the murder of {victim.name}")
    return f"An avenger of {avenger.name} murdered {victim.name} of {enemy.name}."


async def raid(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> str | None:
    hp = ctx.rules.vendetta.raid_hp
    victim = await target_of(ctx, enemy)
    if victim is not None:
        harm = Harm(hp, HarmCause.BATTLE, f"wounded in a feud raid by {avenger.name}", killer_id=avenger.id)
        await apply_hits(ctx, victim, harm, lethal=False)
    shift_stat(enemy, "prosperity", -hp // 5)
    return f"Kinsmen of {avenger.name} raided {enemy.name} to avenge their dead."


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
    for first_id, second_id in sorted(await blood_feud_pairs(ctx.session)):
        if acted >= table.cap:
            break
        first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
        if first is None or second is None:
            continue
        hatred = -await relation(ctx.session, ctx.rules, first.id, second.id)
        sides = [(await grief(ctx, first.id, second.id), first, second), (await grief(ctx, second.id, first.id), second, first)]
        pairs = sorted(sides, key=lambda item: -item[0])
        pain, avenger, enemy = pairs[0]
        if max(pain, hatred) < table.grievance:
            continue
        action = await choose(ctx, avenger, enemy)
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
        if holder.status is not EntityStatus.CANON:
            continue
        customary = holder.location_id is not None and await keeps(ctx, holder.location_id, TraditionKind.DUEL_CUSTOM)
        if not customary and (await values_for(ctx.session, holder.id)).get(ValueAxis.HONOUR, 0) <= 0:
            continue
        if stat(holder, "hp") == 0 or holder.location_id != subject.location_id:
            continue
        theatre = theatre or await Theatre.load(ctx)
        text = await duel(ctx, theatre, holder, subject, war=None, anchor_id=None, context=DuelContext.HONOUR)
        await note(ctx, f"{holder.name} called {subject.name} out to settle a matter of honour.{text}", key="duel.honour", ids=[holder.id, subject.id])
        seen.update({holder.id, subject.id})
        fought += 1
    return fought


@reads("table.community_relations", "table.laws", "table.memories", "table.minds")
@writes("table.chronicle", "table.community_relations", "table.injuries", "table.memories")
async def vendetta_cycles(ctx: TickContext) -> None:
    ctx.count("feud_actions", await feuds(ctx))
    ctx.count("honour_duels", await honour_duels(ctx))


PHASES = (Phase("vendetta_cycles", vendetta_cycles),)
