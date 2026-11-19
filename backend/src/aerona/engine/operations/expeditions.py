from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.kinds.resolves import RESOLVES
from aerona.catalog.operations import AFFLICTIONS, QUIRK_ORIGINS, VIRTUES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.operations import STRESS_MAX, ExpeditionLogRow, ExpeditionMemberRow, ExpeditionRow, QuirkRow
from aerona.db.tables.sites import SiteRoomRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import ExpeditionEvent, ExpeditionGround, ExpeditionRole, ExpeditionStatus, QuirkKind, ResolveKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import skill_level
from aerona.engine.mortal.standing import add_renown
from aerona.engine.operations.expedition_record import log_entry
from aerona.engine.operations.fields import keep
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, scaled_cap
from aerona.engine.recording.record import record
from aerona.engine.sites.rooms import Walk, delve, layout_of, rooms_of
from aerona.rules.registry.operations import ExpeditionRules

E = ExpeditionEvent
G = ExpeditionGround
R = ExpeditionRole
Q = QuirkKind
DARK_GROUNDS = frozenset({G.SITE, G.UNDERWORLD, G.REALM})
COLD_BANDS = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
ROLE_SKILLS = (
    (R.SCOUT, SkillKind.TRACKING),
    (R.GUIDE, SkillKind.NAVIGATION),
    (R.HEALER, SkillKind.MEDICINE),
    (R.FIGHTER, SkillKind.TACTICS),
    (R.SCHOLAR, SkillKind.LORE),
)
RAIN_CHANCE = 30
NIGHT_CHANCE = 30
WEARY = 50
AMBUSH_DARK_SHARE = 4


@dataclass
class ExpeditionTally:
    launched: int = 0
    legs: int = 0
    camps: int = 0
    ambushes: int = 0
    afflictions: int = 0
    virtues: int = 0
    quirks: int = 0
    fallen: int = 0
    returned: int = 0
    lost: int = 0
    finds: int = 0


@dataclass
class Party:
    row: ExpeditionRow
    target: EntityRow | None
    members: list[ExpeditionMemberRow]
    people: dict[int, EntityRow]
    quirks: dict[int, set[QuirkKind]]

    @property
    def alive(self) -> list[ExpeditionMemberRow]:
        return [member for member in self.members if not member.fallen]

    def has(self, member: ExpeditionMemberRow, quirk: QuirkKind) -> bool:
        return quirk in self.quirks.get(member.mortal_entity_id, set())

    def count(self, role: ExpeditionRole) -> int:
        return sum(1 for member in self.alive if member.role is role or (role is R.SCOUT and self.has(member, Q.KEEN_EYED)))


async def quirks_of(ctx: TickContext, mortal_id: int) -> set[QuirkKind]:
    return set(await ctx.session.scalars(select(QuirkRow.kind).where(QuirkRow.mortal_entity_id == mortal_id)))


def legs_for(ctx: TickContext, ground: ExpeditionGround) -> int:
    table = ctx.rules.expeditions
    return {G.SITE: table.site_legs, G.WILDS: table.wilds_legs, G.UNDERWORLD: table.underworld_legs, G.REALM: table.realm_legs}[ground]


async def ground_of(ctx: TickContext, target: EntityRow) -> ExpeditionGround:
    if target.entity_type is EntityType.REGION:
        return G.WILDS
    if await ctx.session.scalar(select(AfterlifeStratumRow.id).where(AfterlifeStratumRow.realm_entity_id == target.id).limit(1)) is not None:
        return G.UNDERWORLD
    if await layout_of(ctx, target) is not None or await rooms_of(ctx, target.id):
        return G.SITE
    return G.REALM


async def role_for(ctx: TickContext, mortal_id: int, taken: list[ExpeditionRole]) -> ExpeditionRole:
    best, level = R.PORTER, 0
    for role, skill in ROLE_SKILLS:
        found = await skill_level(ctx.session, mortal_id, skill)
        bonus = PERCENT if role not in taken else 0
        if found > 0 and found + bonus > level:
            best, level = role, found + bonus
    return best


async def log(ctx: TickContext, party: Party, event: ExpeditionEvent, **values: object) -> None:
    await log_entry(ctx, party.row, ExpeditionLogRow(expedition_id=party.row.id, epoch=ctx.epoch, leg=party.row.legs_done, event=event, locked=[], **values))


async def grant_quirk(ctx: TickContext, mortal_id: int, kind: QuirkKind, *, source_id: int | None, expedition_id: int | None) -> QuirkRow:
    row = await ctx.session.scalar(select(QuirkRow).where(QuirkRow.mortal_entity_id == mortal_id, QuirkRow.kind == kind))
    if row is None:
        row = QuirkRow(mortal_entity_id=mortal_id, kind=kind, source_entity_id=source_id, expedition_id=expedition_id, gained_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    else:
        keep(row, "strength", min(3, row.strength + 1))
    return row


async def maybe_quirk(ctx: TickContext, party: Party, event: ExpeditionEvent, tally: ExpeditionTally) -> None:
    pair = QUIRK_ORIGINS.get(event)
    if pair is None or not party.alive:
        return
    rng = ctx.rng(f"quirk.{party.row.id}.{party.row.legs_done}.{event.value}.{ctx.epoch}")
    if not rng.chance(ctx.rules.expeditions.quirk_chance):
        return
    member = rng.pick(party.alive)
    if held(member.mortal_entity_id):
        return
    kind = pair[rng.below(len(pair))]
    await grant_quirk(ctx, member.mortal_entity_id, kind, source_id=party.row.target_entity_id, expedition_id=party.row.id)
    party.quirks.setdefault(member.mortal_entity_id, set()).add(kind)
    await log(ctx, party, E.QUIRK, member_entity_id=member.mortal_entity_id, quirk=kind)
    tally.quirks += 1


async def harm(ctx: TickContext, party: Party, member: ExpeditionMemberRow, damage: int, *, cause: HarmCause, reason: str, tally: ExpeditionTally) -> None:
    mortal = party.people.get(member.mortal_entity_id)
    if mortal is None or held(mortal.id):
        return
    await apply_hits(ctx, mortal, Harm(damage, cause, reason))
    stress(ctx, party, member, ctx.rules.expeditions.harm_stress)
    if mortal.status is not EntityStatus.CANON and "fallen" not in member.locked:
        member.fallen = True
        await log(ctx, party, E.FALLEN, member_entity_id=mortal.id)
        tally.fallen += 1


def stress(ctx: TickContext, party: Party, member: ExpeditionMemberRow, amount: int) -> None:
    keep(member, "stress", clamp_int(member.stress + amount, 0, STRESS_MAX))


async def launch(
    ctx: TickContext, leader: EntityRow, target: EntityRow, companions: list[EntityRow], *, sponsor_id: int | None, tally: ExpeditionTally
) -> ExpeditionRow:
    table = ctx.rules.expeditions
    ground = await ground_of(ctx, target)
    knows = Q.KNOWS_WAYS in await quirks_of(ctx, leader.id)
    roles: list[ExpeditionRole] = []
    for mortal in [leader, *companions]:
        roles.append(await role_for(ctx, mortal.id, roles))
    porters = sum(1 for role in roles if role is R.PORTER)
    row = ExpeditionRow(
        name=f"Expedition of {leader.name} into {target.name}",
        leader_entity_id=leader.id,
        sponsor_node_id=sponsor_id,
        target_entity_id=target.id,
        ground=ground,
        legs_total=max(1, legs_for(ctx, ground) - (1 if knows else 0)),
        provisions=table.provisions_per_member * len(roles) + table.porter_provisions * porters,
        light=table.light_stock if ground in DARK_GROUNDS else 0,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    for mortal, role in zip([leader, *companions], roles, strict=True):
        ctx.session.add(ExpeditionMemberRow(expedition_id=row.id, mortal_entity_id=mortal.id, role=role, locked=[]))
    await log_entry(ctx, row, ExpeditionLogRow(expedition_id=row.id, epoch=ctx.epoch, leg=0, event=E.SETOUT, member_entity_id=leader.id, locked=[]))
    tally.launched += 1
    await record(
        ctx,
        "expedition.set_out",
        roles={
            IncidentRole.LEADER: leader.id,
            IncidentRole.DESTINATION: target.id,
            IncidentRole.MEMBER: [mortal.id for mortal in companions],
            IncidentRole.PATRON: sponsor_id,
        },
        facts={"ground": ground, "companions": len(companions), "legs": row.legs_total, "provisions": row.provisions, "light": row.light},
        place=target.id,
        cause=row.incident_id,
    )
    return row


async def party_of(ctx: TickContext, row: ExpeditionRow) -> Party:
    members = list(await ctx.session.scalars(select(ExpeditionMemberRow).where(ExpeditionMemberRow.expedition_id == row.id).order_by(ExpeditionMemberRow.id)))
    people = {member.mortal_entity_id: person for member in members if (person := await ctx.session.get(EntityRow, member.mortal_entity_id)) is not None}
    for member in members:
        person = people.get(member.mortal_entity_id)
        if (person is None or person.status is not EntityStatus.CANON) and "fallen" not in member.locked:
            member.fallen = True
    quirks = {member.mortal_entity_id: await quirks_of(ctx, member.mortal_entity_id) for member in members}
    target = await ctx.session.get(EntityRow, row.target_entity_id) if row.target_entity_id is not None else None
    return Party(row, target, members, people, quirks)


async def climate_of(ctx: TickContext, party: Party) -> RegionEnvironmentRow | None:
    if party.target is None:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(party.target.id)
    return await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None


def ration(party: Party, member: ExpeditionMemberRow) -> int:
    if party.has(member, Q.EATS_ANYTHING):
        return 0
    return RESOLVES[member.resolve].ration


def eat(ctx: TickContext, party: Party) -> None:
    need = sum(ration(party, member) for member in party.alive)
    if party.row.provisions >= need:
        keep(party.row, "provisions", party.row.provisions - need)
        return
    keep(party.row, "provisions", 0)
    for member in party.alive:
        keep(member, "hunger", clamp_int(member.hunger + ctx.rules.expeditions.hunger_step, 0, PERCENT))


def light(ctx: TickContext, party: Party) -> None:
    table = ctx.rules.expeditions
    if party.row.ground in DARK_GROUNDS:
        if party.row.light > 0:
            keep(party.row, "light", max(0, party.row.light - table.light_per_leg))
            keep(party.row, "darkness", 0)
        else:
            keep(party.row, "darkness", PERCENT)
        return
    night = ctx.rng(f"night_leg.{party.row.id}.{party.row.legs_done}.{ctx.epoch}").chance(NIGHT_CHANCE)
    keep(party.row, "darkness", PERCENT // 2 if night else 0)


def danger_of(ctx: TickContext, party: Party) -> int:
    table = ctx.rules.expeditions
    sighted = any(party.has(member, Q.DARK_SIGHTED) for member in party.alive)
    dark = 0 if sighted else party.row.darkness * table.dark_danger_pct // PERCENT
    eyes = (party.count(R.SCOUT) + party.count(R.GUIDE) + sum(1 for member in party.alive if RESOLVES[member.resolve].keeps_watch)) * table.scout_danger
    tooled = table.tool_danger if party.row.ground in DARK_GROUNDS and party.row.tools > 0 else 0
    return clamp_int(party.row.danger + dark - eyes - tooled, 0, PERCENT)


def others_pressure(table: ExpeditionRules, member: ExpeditionMemberRow) -> int:
    spec = RESOLVES[member.resolve]
    return spec.others_sign * int(getattr(table, spec.others_rule)) if spec.others_rule is not None else 0


def strain(ctx: TickContext, party: Party) -> None:
    table = ctx.rules.expeditions
    pressure = {member.mortal_entity_id: others_pressure(table, member) for member in party.alive}
    whole = sum(pressure.values())
    thieves = sum(1 for member in party.alive if party.has(member, Q.LIGHT_FINGERED))
    for member in party.alive:
        amount = table.leg_stress + (table.dark_stress if party.row.darkness >= PERCENT // 2 else 0) * (2 if party.has(member, Q.FEARS_DARK) else 1)
        if party.has(member, Q.STEADY_NERVES):
            amount //= 2
        if party.has(member, Q.HOMESICK):
            amount += table.leg_stress // 2
        spec = RESOLVES[member.resolve]
        amount = amount * spec.stress_pct // PERCENT
        others_thieving = thieves - party.has(member, Q.LIGHT_FINGERED)
        amount += whole - pressure[member.mortal_entity_id] + others_thieving * table.abusive_stress // 2
        if spec.own_relief_rule is not None:
            amount -= int(getattr(table, spec.own_relief_rule))
        stress(ctx, party, member, amount)


async def expose(ctx: TickContext, party: Party, land: RegionEnvironmentRow | None, tally: ExpeditionTally) -> None:
    table = ctx.rules.expeditions
    cold = land is not None and land.temperature_band in COLD_BANDS
    rain = party.row.ground is G.WILDS and ctx.rng(f"rain_leg.{party.row.id}.{party.row.legs_done}.{ctx.epoch}").chance(RAIN_CHANCE)
    healer = party.count(R.HEALER) > 0 and party.row.medicine > 0
    if healer:
        keep(party.row, "medicine", party.row.medicine - 1)
    for member in party.alive:
        scale = PERCENT
        if party.has(member, Q.HARDY):
            scale //= 2
        else:
            scale = scale * RESOLVES[member.resolve].exposure_pct // PERCENT
        if party.has(member, Q.FRAIL):
            scale = scale * 3 // 2
        relief = table.healer_relief if healer else 0
        keep(member, "cold", clamp_int(member.cold + (table.cold_per_leg * scale // PERCENT if cold else 0) - relief, 0, PERCENT))
        keep(member, "wet", clamp_int(member.wet + (table.wet_per_leg * scale // PERCENT if rain else 0) - relief, 0, PERCENT))
        keep(member, "fatigue", clamp_int(member.fatigue + table.leg_fatigue * scale // PERCENT, 0, PERCENT))
        if max(member.cold, member.wet, member.hunger, member.fatigue) >= table.exposure_harm:
            await log(ctx, party, E.EXPOSURE, member_entity_id=member.mortal_entity_id)
            await harm(ctx, party, member, table.exposure_hp, cause=HarmCause.EXPOSURE, reason="died of exposure on an expedition", tally=tally)
            await maybe_quirk(ctx, party, E.EXPOSURE, tally)


async def test_resolve(ctx: TickContext, party: Party, tally: ExpeditionTally) -> None:
    table = ctx.rules.expeditions
    for member in party.alive:
        if member.stress >= table.breaking_stress:
            await harm(ctx, party, member, table.breaking_hp, cause=HarmCause.EXPOSURE, reason="who gave out from exhaustion on an expedition", tally=tally)
            keep(member, "stress", table.resolve_at)
            continue
        if member.stress < table.resolve_at or member.resolve is not ResolveKind.STEADY or "resolve" in member.locked:
            continue
        rng = ctx.rng(f"resolve.{party.row.id}.{member.mortal_entity_id}.{party.row.legs_done}.{ctx.epoch}")
        lead = await skill_level(ctx.session, member.mortal_entity_id, SkillKind.LEADERSHIP)
        virtue = rng.chance(table.virtue_chance + lead // 4)
        member.resolve = rng.pick(sorted(VIRTUES if virtue else AFFLICTIONS))
        await log(ctx, party, E.VIRTUE if virtue else E.AFFLICTION, member_entity_id=member.mortal_entity_id, resolve=member.resolve, stress=member.stress)
        if virtue:
            tally.virtues += 1
            keep(member, "stress", member.stress // 2)
        else:
            tally.afflictions += 1


async def camp(ctx: TickContext, party: Party, tally: ExpeditionTally, *, force: bool = False) -> None:
    table = ctx.rules.expeditions
    alive = party.alive
    tired = sum(member.fatigue for member in alive) // max(1, len(alive))
    if not alive or (tired < WEARY and not force) or any(RESOLVES[member.resolve].refuses_rest for member in alive) or party.row.provisions < len(alive):
        return
    keep(party.row, "provisions", party.row.provisions - len(alive))
    keep(party.row, "status", ExpeditionStatus.CAMPED)
    for member in alive:
        keep(member, "fatigue", clamp_int(member.fatigue - table.camp_fatigue, 0, PERCENT))
        stress(ctx, party, member, -table.camp_stress)
    await log(ctx, party, E.CAMP, provisions_used=len(alive))
    tally.camps += 1
    await maybe_quirk(ctx, party, E.CAMP, tally)
    rng = ctx.rng(f"ambush.{party.row.id}.{party.row.legs_done}.{ctx.epoch}")
    if rng.chance(table.ambush_chance + party.row.darkness // AMBUSH_DARK_SHARE):
        victim = rng.pick(alive)
        guard = min(PERCENT, party.count(R.FIGHTER) * table.fighter_guard_pct)
        await log(ctx, party, E.AMBUSH, member_entity_id=victim.mortal_entity_id)
        tally.ambushes += 1
        await harm(
            ctx,
            party,
            victim,
            ctx.rules.sites.delve_hp * (PERCENT - guard) // PERCENT,
            cause=HarmCause.QUEST,
            reason="fell in a night ambush on an expedition",
            tally=tally,
        )
        for member in party.alive:
            if party.has(member, Q.JUMPY):
                stress(ctx, party, member, table.harm_stress)
        await maybe_quirk(ctx, party, E.AMBUSH, tally)
    keep(party.row, "status", ExpeditionStatus.UNDERWAY)


async def arrive(ctx: TickContext, party: Party, tally: ExpeditionTally) -> Walk | None:
    leader = party.people.get(party.row.leader_entity_id or 0)
    if leader is None or leader.status is not EntityStatus.CANON:
        leader = next((party.people[member.mortal_entity_id] for member in party.alive if member.mortal_entity_id in party.people), None)
    walk = None
    found = party.count(R.SCHOLAR) * ctx.rules.expeditions.scholar_find + sum(1 for member in party.alive if party.has(member, Q.LIGHT_FINGERED))
    if party.row.ground is G.SITE and party.target is not None and leader is not None:
        walk = await delve(ctx, leader, party.target, max(0, len(party.alive) - 1))
        found += len(walk.loot) + (1 if walk.reached_heart else 0)
    keep(party.row, "found", party.row.found + found)
    tally.finds += found
    if leader is not None and found > 0 and not held(leader.id):
        await give_coin(ctx.session, ctx.rules, leader, found * ctx.rules.expeditions.find_coin)
    return walk


async def leg(ctx: TickContext, party: Party, land: RegionEnvironmentRow | None, tally: ExpeditionTally) -> Walk | None:
    table = ctx.rules.expeditions
    keep(party.row, "legs_done", party.row.legs_done + 1)
    before = party.row.provisions
    lit = party.row.light
    eat(ctx, party)
    light(ctx, party)
    await log(
        ctx,
        party,
        E.ROOM if party.row.ground is G.SITE else E.LEG,
        provisions_used=max(0, before - party.row.provisions),
        light_used=max(0, lit - party.row.light),
    )
    rng = ctx.rng(f"leg.{party.row.id}.{party.row.legs_done}.{ctx.epoch}")
    danger = danger_of(ctx, party)
    if party.row.ground in DARK_GROUNDS and party.row.tools > 0:
        keep(party.row, "tools", party.row.tools - 1)
    if party.alive and rng.chance(danger):
        await harm(ctx, party, rng.pick(party.alive), ctx.rules.sites.delve_hp, cause=HarmCause.QUEST, reason="fell on an expedition", tally=tally)
    strain(ctx, party)
    await expose(ctx, party, land, tally)
    await test_resolve(ctx, party, tally)
    await maybe_quirk(ctx, party, E.ROOM if party.row.ground is G.SITE else E.LEG, tally)
    tally.legs += 1
    if party.row.legs_done >= party.row.legs_total:
        return await arrive(ctx, party, tally) or Walk()
    await camp(ctx, party, tally)
    hungry = party.row.provisions <= 0 and any(member.hunger >= table.exposure_harm for member in party.alive)
    return Walk() if hungry else None


async def finish(ctx: TickContext, party: Party, tally: ExpeditionTally) -> None:
    if not party.alive:
        keep(party.row, "status", ExpeditionStatus.LOST)
        party.row.ended_epoch = ctx.epoch
        await log(ctx, party, E.LOSS)
        tally.lost += 1
        await record(
            ctx,
            "expedition.lost",
            roles={IncidentRole.LEADER: party.row.leader_entity_id, IncidentRole.DESTINATION: party.row.target_entity_id},
            facts={"members": len(party.members), "legs_done": party.row.legs_done},
            place=party.row.target_entity_id,
            cause=party.row.incident_id,
        )
        return
    keep(party.row, "status", ExpeditionStatus.RETURNED)
    party.row.ended_epoch = ctx.epoch
    await log(ctx, party, E.RETURN)
    tally.returned += 1
    for member in party.alive:
        await add_renown(ctx.session, member.mortal_entity_id, ctx.rules.sites.delve_renown, ctx.epoch, rules=ctx.rules)
        if member.resolve in AFFLICTIONS and "resolve" not in member.locked:
            member.resolve = ResolveKind.STEADY
    await maybe_quirk(ctx, party, E.RETURN, tally)
    await record(
        ctx,
        "expedition.returned",
        roles={
            IncidentRole.LEADER: party.row.leader_entity_id,
            IncidentRole.MEMBER: [member.mortal_entity_id for member in party.alive if member.mortal_entity_id != party.row.leader_entity_id],
            IncidentRole.DESTINATION: party.row.target_entity_id,
        },
        facts={"finds": party.row.found, "returned": len(party.alive), "members": len(party.members), "renown": ctx.rules.sites.delve_renown},
        place=party.row.target_entity_id,
        cause=party.row.incident_id,
    )


async def advance(ctx: TickContext, row: ExpeditionRow, tally: ExpeditionTally, legs: int) -> Walk | None:
    if row.status in {ExpeditionStatus.RETURNED, ExpeditionStatus.LOST} or held(*(item for item in (row.leader_entity_id, row.target_entity_id) if item)):
        return None
    party = await party_of(ctx, row)
    land = await climate_of(ctx, party)
    walk = None
    for _ in range(legs):
        if not party.alive:
            break
        walk = await leg(ctx, party, land, tally)
        if walk is not None:
            break
    if not party.alive or walk is not None:
        await finish(ctx, party, tally)
    return walk


async def quest_expedition(ctx: TickContext, hero: EntityRow, target: EntityRow, companions: list[EntityRow]) -> Walk:
    tally = ExpeditionTally()
    row = await launch(ctx, hero, target, companions, sponsor_id=None, tally=tally)
    walk = await advance(ctx, row, tally, row.legs_total)
    return walk or Walk()


async def on_expedition(ctx: TickContext) -> set[int]:
    rows = await ctx.session.scalars(
        select(ExpeditionMemberRow.mortal_entity_id)
        .join(ExpeditionRow, ExpeditionRow.id == ExpeditionMemberRow.expedition_id)
        .where(ExpeditionRow.status.in_([ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED]))
    )
    return set(rows)


async def destinations(ctx: TickContext, world_id: int) -> list[EntityRow]:
    sites = await ctx.session.scalars(
        select(EntityRow)
        .join(SiteRoomRow, SiteRoomRow.site_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, SiteRoomRow.cleared_epoch.is_(None))
        .distinct()
        .order_by(EntityRow.id)
    )
    realms = await ctx.session.scalars(
        select(EntityRow)
        .join(AfterlifeStratumRow, AfterlifeStratumRow.realm_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .distinct()
        .order_by(EntityRow.id)
    )
    wilds = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [*sites, *realms, *wilds]


async def keep_expeditions(ctx: TickContext, tally: ExpeditionTally) -> None:
    table = ctx.rules.expeditions
    for row in list(await ctx.session.scalars(select(ExpeditionRow).where(ExpeditionRow.status.in_([ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED])))):
        await advance(ctx, row, tally, table.legs_per_epoch)
    away = await on_expedition(ctx)
    leaders = await ctx.session.scalars(
        select(BondRow.source_node_id).where(BondRow.kind == BondKind.COMPANION, BondRow.state == BondState.ACTIVE).distinct().order_by(BondRow.source_node_id)
    )
    launched = 0
    candidates = ctx.rng("expedition.order").shuffled(list(leaders))
    limit = scaled_cap(table.launches, table.launches_leader_divisor, len(candidates))
    for leader_id in candidates:
        if launched >= limit or leader_id in away or held(leader_id):
            continue
        leader = await ctx.session.get(EntityRow, leader_id)
        if leader is None or leader.entity_type is not EntityType.MORTAL or leader.status is not EntityStatus.CANON:
            continue
        quirks = await quirks_of(ctx, leader.id)
        chance = table.launch_chance * (2 if Q.RESTLESS in quirks else 1) // (2 if Q.HOMESICK in quirks else 1)
        rng = ctx.rng(f"expedition.launch.{leader.id}.{ctx.epoch}")
        if not rng.chance(chance):
            continue
        places = await destinations(ctx, leader.world_id)
        if not places:
            continue
        target = rng.pick(places)
        companions = await companions_for(ctx, leader, away)
        row = await launch(ctx, leader, target, companions, sponsor_id=None, tally=tally)
        away.update({leader.id, *(mortal.id for mortal in companions)})
        await advance(ctx, row, tally, table.legs_per_epoch)
        launched += 1


async def companions_for(ctx: TickContext, leader: EntityRow, away: set[int]) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(BondRow).where(
            BondRow.kind == BondKind.COMPANION,
            BondRow.state == BondState.ACTIVE,
            (BondRow.source_node_id == leader.id) | (BondRow.target_node_id == leader.id),
        )
    )
    found: list[EntityRow] = []
    for bond in rows:
        other = await ctx.session.get(EntityRow, bond.other_end(leader.id))
        if other is not None and other.status is EntityStatus.CANON and other.id not in away and not held(other.id):
            found.append(other)
        if len(found) >= ctx.rules.expeditions.party_size:
            break
    return found
