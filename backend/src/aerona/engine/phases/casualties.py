from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from aerona.catalog.interventions import DISASTERS
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CommanderTraitRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import Capacity, HarmCause
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, HERO_ROLES, EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.military import CommanderTrait
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.book import bedridden, blow_style, effective
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits, fatal_injury
from aerona.engine.mortal.standing import add_renown
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import DISASTER_KINDS
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.knowledge import KnowledgeMap, known_levels
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, connect, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.records import death_path
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import release_captive, war_event
from aerona.engine.services.war_geography import Neighbourhood
from aerona.rules.registry import Rules

FIGHTER_ROLES = HERO_ROLES | {MortalRole.CAPTAIN, MortalRole.BANDIT, MortalRole.OFFICER, MortalRole.PILOT}
COMMANDER_SUBTYPES = ("commander", "standard bearer", "raider captain", "guard captain")
DECAPITATORS = frozenset({CommanderTrait.BRUTAL, CommanderTrait.AGGRESSIVE_ASSAULTER})
HOLY_COMMANDER_SUBTYPE = "guard captain"
KIND_OF_DISASTER = {kind: disaster for disaster, kind in DISASTER_KINDS.items()}
STAT_KEYS = ("strength", "agility", "intellect", "charisma")
DUEL_DEATH = "fell in a duel"


class FateWrit(StrEnum):
    DOOM = "doom"
    SHIELD = "shield"
    CLEAR = "clear"


@dataclass(frozen=True)
class Clash:
    event: EntityRow
    war_id: int
    winner_id: int
    loser_id: int
    siege: bool
    decisive: bool


@dataclass(frozen=True)
class Marks:
    chosen: set[int]
    commanders: set[int]


@dataclass
class CasualtyCount:
    dead: int = 0
    wounded: int = 0


async def clashes_of(ctx: TickContext) -> list[Clash]:
    found: list[Clash] = []
    for battle in await ctx.session.scalars(select(BattleRow).where(BattleRow.epoch == ctx.epoch).order_by(BattleRow.id)):
        war = await ctx.session.get(WarRow, battle.war_id)
        if war is None:
            continue
        record = await ctx.session.get(EntityRow, battle.record_entity_id) if battle.record_entity_id is not None else None
        event = record or await war_event(ctx.session, war)
        found.append(Clash(event, war.id, battle.winner_entity_id, battle.loser_entity_id, battle.siege_id is not None, record is not None))
    return found


async def fated(ctx: TickContext, mortal: EntityRow, dies: bool) -> bool:
    if await remove_flag(ctx.session, mortal.id, EntityFlag.DOOMED):
        return True
    if dies and await remove_flag(ctx.session, mortal.id, EntityFlag.FATE_SHIELDED):
        await note(ctx, f"{mortal.name} came back from the edge of death; their fate was shielded.", key="casualties.fate_shielded", ids=[mortal.id])
        return False
    return dies


FALL_CAUSES = {EntityFlag.SLAIN_IN_CAPTIVITY: HarmCause.TORTURE, EntityFlag.DIED_IN_DISASTER: HarmCause.DISASTER}
BLOODLESS_FALLS = frozenset({EntityFlag.DIED_OF_PLAGUE})


async def fall(ctx: TickContext, mortal: EntityRow, cause: str, killer_id: int | None, *, event: EntityRow | None, flag: EntityFlag) -> bool:
    killer = await living_entity(ctx.session, killer_id) if killer_id is not None else None
    harm = Harm(
        ctx.rules.casualties.wound_hp,
        FALL_CAUSES.get(flag, HarmCause.BATTLE),
        cause,
        killer_id=killer_id,
        event_entity_id=event.id if event is not None else None,
        style=await blow_style(ctx.session, ctx.rules, killer if killer is not None and killer.entity_type is EntityType.MORTAL else None, mortal),
    )
    if mortal.status is EntityStatus.CANON and flag not in BLOODLESS_FALLS:
        await fatal_injury(ctx, mortal, harm)
    if not await death_path(ctx, mortal, cause, killer_id, cause, event_id=event.id if event is not None else None, manner=DeathCause.BATTLE):
        return False
    await add_flag(ctx.session, mortal.id, flag, ctx.epoch)
    if event is not None and event.id != killer_id:
        await BondRepository(ctx.session).connect(BondDraft(event.id, mortal.id, BondKind.CAUSED, ctx.epoch, cause))
    return True


async def commander_of_side(ctx: TickContext, war_id: int, side_id: int) -> EntityRow | None:
    row = await ctx.session.scalar(
        select(ArmyRow).where(ArmyRow.war_id == war_id, ArmyRow.owner_entity_id == side_id).order_by(ArmyRow.entity_id.desc()).limit(1)
    )
    return await living_entity(ctx.session, row.commander_entity_id) if row is not None else None


async def army_of_side(ctx: TickContext, war_id: int, side_id: int) -> int | None:
    row = await ctx.session.scalar(
        select(ArmyRow).where(ArmyRow.war_id == war_id, ArmyRow.owner_entity_id == side_id).order_by(ArmyRow.entity_id.desc()).limit(1)
    )
    return row.entity_id if row is not None else None


def is_fighter(mortal: EntityRow, marks: Marks) -> bool:
    return mortal.mortal_role in FIGHTER_ROLES or mortal.id in marks.chosen or mortal.id in marks.commanders


def death_chance(rules: Rules, clash: Clash, *, victor: bool, commander: bool, fighter: bool) -> float | None:
    losses = rules.casualties
    if commander:
        won, lost = losses.commander_victor_death, losses.commander_loser_death
    elif fighter:
        won, lost = losses.warrior_victor_death, losses.warrior_loser_death
    elif not victor and clash.decisive:
        return float(losses.civilian_siege_death if clash.siege else losses.civilian_battle_death)
    else:
        return None
    if not clash.decisive:
        return won * losses.indecisive_pct / 100
    return float(won if victor else lost)


async def _killer(ctx: TickContext, clash: Clash, sides: SideIndex, enemy_id: int, marks: Marks) -> EntityRow | None:
    commander = await commander_of_side(ctx, clash.war_id, enemy_id)
    if commander is not None:
        return commander
    fighters = [mortal for mortal in sides.heroes_of(enemy_id) if is_fighter(mortal, marks)]
    if fighters:
        return ctx.rng(seed_of("killer", clash.event.id, enemy_id)).pick(fighters)
    army = await army_of_side(ctx, clash.war_id, enemy_id)
    return await ctx.session.get(EntityRow, army) if army is not None else await living_entity(ctx.session, enemy_id)


async def _side_losses(ctx: TickContext, clash: Clash, sides: SideIndex, side_id: int, *, count: CasualtyCount, marks: Marks) -> int:
    losses = ctx.rules.casualties
    victor = side_id == clash.winner_id
    enemy_id = clash.loser_id if victor else clash.winner_id
    side_commander = await commander_of_side(ctx, clash.war_id, side_id)
    rng = ctx.rng(seed_of("clash", clash.event.id, side_id))
    hunted = await decapitation(ctx, clash.war_id, enemy_id)
    fallen = 0
    for mortal in sides.heroes_of(side_id):
        if fallen >= losses.clash_cap or count.dead >= losses.epoch_cap:
            break
        if mortal.status is not EntityStatus.CANON:
            continue
        if bedridden(ctx.rules, mortal):
            continue
        commander = side_commander is not None and side_commander.id == mortal.id
        fighter = commander or is_fighter(mortal, marks)
        chance = death_chance(ctx.rules, clash, victor=victor, commander=commander, fighter=fighter)
        if chance is None:
            continue
        if commander and hunted:
            chance = min(100.0, chance * ctx.rules.standing.decapitation_exposure_pct / 100)
        killer = await _killer(ctx, clash, sides, enemy_id, marks)
        killer_id = killer.id if killer is not None else None
        against = f" facing {killer.name}" if killer is not None and fighter else ""
        if await fated(ctx, mortal, rng.chance(chance)):
            cause = f"fell in {clash.event.name}{against}" if fighter else f"died in {clash.event.name}{' in the besieged city' if clash.siege else ''}"
            if await fall(ctx, mortal, cause, killer_id, event=clash.event, flag=EntityFlag.DIED_IN_SIEGE if clash.siege else EntityFlag.FELL_IN_BATTLE):
                fallen += 1
                count.dead += 1
        elif fighter and rng.chance(losses.wound_chance):
            harm = Harm(
                losses.wound_hp,
                HarmCause.BATTLE,
                f"died of the wounds taken in {clash.event.name}",
                killer_id=killer_id,
                event_entity_id=clash.event.id,
                style=await blow_style(ctx.session, ctx.rules, killer if killer is not None and killer.entity_type is EntityType.MORTAL else None, mortal),
            )
            outcome = (await apply_hits(ctx, mortal, harm)).outcome
            if outcome is WoundOutcome.DIED:
                await add_flag(ctx.session, mortal.id, EntityFlag.FELL_IN_BATTLE, ctx.epoch)
                fallen += 1
                count.dead += 1
            elif outcome is WoundOutcome.WOUNDED:
                count.wounded += 1
        elif fighter and victor:
            await add_renown(ctx.session, mortal.id, ctx.rules.standing.glory_renown, ctx.epoch, rules=ctx.rules)
    return fallen


async def decapitation(ctx: TickContext, war_id: int, enemy_id: int) -> bool:
    commander = await commander_of_side(ctx, war_id, enemy_id)
    if commander is None:
        return False
    traits = set(await ctx.session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == commander.id)))
    return bool(traits & DECAPITATORS)


async def _captive_chaos(ctx: TickContext, clash: Clash, count: CasualtyCount) -> None:
    losses = ctx.rules.casualties
    holder = await living_entity(ctx.session, clash.loser_id)
    rows = await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.captor_entity_id == clash.loser_id, CaptiveRow.status == CaptiveStatus.HELD))
    rng = ctx.rng(seed_of("captive_chaos", clash.event.id))
    for row in list(rows):
        if count.dead >= losses.epoch_cap:
            return
        captive = await living_entity(ctx.session, row.captive_entity_id)
        if captive is None or not await fated(ctx, captive, rng.chance(losses.captive_chaos_death)):
            continue
        await release_captive(ctx, row, CaptiveStatus.EXECUTED)
        holder_name = holder.name if holder is not None else "their captors"
        cause = f"was killed by {holder_name} in the chaos of the defeat at {clash.event.name}"
        if await fall(ctx, captive, cause, clash.loser_id, event=clash.event, flag=EntityFlag.SLAIN_IN_CAPTIVITY):
            count.dead += 1


async def war_dead(ctx: TickContext, clashes: list[Clash]) -> CasualtyCount:
    count = CasualtyCount()
    if not clashes:
        return count
    sides = await SideIndex.load(ctx.session, await Neighbourhood.load(ctx.session, ctx.rules))
    commanders = {
        row for row in await ctx.session.scalars(select(ArmyRow.commander_entity_id).where(ArmyRow.commander_entity_id.is_not(None))) if row is not None
    }
    marks = Marks(await flags_by_entity(ctx.session, EntityFlag.CHOSEN), commanders)
    for clash in clashes:
        if count.dead >= ctx.rules.casualties.epoch_cap:
            break
        for side_id in (clash.loser_id, clash.winner_id):
            await _side_losses(ctx, clash, sides, side_id, count=count, marks=marks)
        if clash.decisive:
            await _captive_chaos(ctx, clash, count)
    return count


async def _veterans(ctx: TickContext, row: ArmyRow) -> int:
    losses = ctx.rules.casualties
    best = 0
    others = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.owner_entity_id == row.owner_entity_id, ArmyRow.entity_id != row.entity_id))
    for other in others:
        army = await ctx.session.get(EntityRow, other.entity_id)
        if army is None:
            continue
        ended = other.disbanded_epoch if other.disbanded_epoch is not None else army.end_epoch
        if army.status is EntityStatus.CANON and other.disbanded_epoch is None:
            continue
        if ended is not None and ended >= ctx.epoch - losses.veteran_epochs:
            best = max(best, stat(army, "experience") or 0)
    return round_half_up(best * losses.veteran_share_pct / 100)


async def raise_commander(ctx: TickContext, army: EntityRow, row: ArmyRow) -> EntityRow | None:
    losses = ctx.rules.casualties
    community = await living_entity(ctx.session, row.owner_entity_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES or row.war_id is None:
        return None
    rng = ctx.rng(seed_of("commander", army.id))
    subtype = HOLY_COMMANDER_SUBTYPE if community.entity_type is EntityType.CULT else rng.pick(COMMANDER_SUBTYPES)
    lifespan = losses.commander_lifespan + rng.die(losses.commander_lifespan_die)
    stats = {key: clamp_int(losses.commander_stat_base + rng.die(losses.commander_stat_die), 0, 100) for key in STAT_KEYS}
    name = await Namer(ctx.session, ctx.rules).person([community], seed_of(army.id, ctx.epoch, "commander"), community.world_id)
    warfare = (await known_levels(ctx.session, [community.id])).get(community.id, {}).get(KnowledgeBranch.WARFARE, 0)
    commander = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.MORTAL,
            name=name or f"{army.name} Commander",
            body=f"Rose from the ranks of {community.name} to lead {army.name}.",
            stats=MortalStats(hp=losses.commander_hp, age=round_half_up(lifespan * losses.commander_age_pct / 100), lifespan=lifespan, **stats),
            power=max(1, community.power_level - 1),
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            world_id=community.world_id,
            subtype=subtype,
            mortal_role=MortalRole.OFFICER if warfare >= losses.officer_warfare_level else MortalRole.WARRIOR,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if name else (),
        ),
    )
    row.commander_entity_id = commander.id
    bonds = BondRepository(ctx.session)
    await connect(ctx.session, commander.id, community.id, BondKind.PROTECTS, ctx.epoch)
    await connect(ctx.session, commander.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch)
    await connect(ctx.session, commander.id, army.id, BondKind.COMMANDS, ctx.epoch, description="commands")
    await bind_language_and_faith(ctx, commander, source=community)
    war = await ctx.session.get(WarRow, row.war_id)
    if war is not None:
        await bonds.connect(BondDraft(war.event_entity_id, commander.id, BondKind.PARTY_TO, ctx.epoch, "commander", role=BondRole.COMMANDER, war_id=war.id))
    await note(
        ctx,
        f"{commander.name} rose from the ranks of {community.name} to lead {army.name}.",
        key="casualties.commander_risen",
        ids=[commander.id, army.id, community.id],
    )
    return commander


async def army_experience(ctx: TickContext, clashes: list[Clash]) -> int:
    losses = ctx.rules.casualties
    fought = {clash.war_id for clash in clashes}
    inherited = 0
    rows = list(await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)))
    for row in rows:
        army = await living_entity(ctx.session, row.entity_id)
        if army is None or held(army.id):
            continue
        before = stat(army, "experience") or 0
        after = before
        if row.raised_epoch == ctx.epoch:
            veterans = await _veterans(ctx, row)
            if veterans > after:
                after = veterans
                inherited += 1
                await note(
                    ctx,
                    f"Veterans of old wars joined {army.name}; the army was seasoned from its first day.",
                    key="casualties.veterans",
                    ids=[army.id, row.owner_entity_id],
                )
        elif row.war_id is not None and row.war_id in fought:
            commander = await living_entity(ctx.session, row.commander_entity_id)
            if (
                commander is not None
                and await effective(ctx.session, commander, "intellect", capacity=Capacity.COMMAND, rules=ctx.rules) >= losses.commander_min_intellect
            ):
                after = before + losses.commander_experience
        elif row.war_id is not None:
            after = max(min(before, losses.rust_floor), before - losses.rust)
        set_stats(army, experience=clamp_int(after, 0, 100))
        if (
            row.war_id is not None
            and await living_entity(ctx.session, row.commander_entity_id) is None
            and ctx.rng(seed_of("commander_rise", army.id)).chance(losses.commander_rise_chance)
        ):
            await raise_commander(ctx, army, row)
    ctx.count("veterans", inherited)
    return inherited


async def mark_duel_dead(ctx: TickContext, clashes: list[Clash]) -> int:
    marked = 0
    for clash in clashes:
        for bond in await BondRepository(ctx.session).outgoing(clash.event.id, BondKind.CAUSED, active_only=False):
            fallen = await ctx.session.get(EntityRow, bond.target_node_id)
            if bond.description == DUEL_DEATH and fallen is not None and fallen.status is EntityStatus.DEAD:
                marked += int(await add_flag(ctx.session, fallen.id, EntityFlag.FELL_IN_BATTLE, ctx.epoch))
    return marked


@reads(
    "army.experience",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "table.armies",
    "table.avatars",
    "table.battles",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.captives",
    "table.commander_traits",
    "table.community_societies",
    "table.conditions",
    "table.cosmos",
    "table.creator_taboos",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_values",
    "table.designated_heirs",
    "table.divine_wounds",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.geasa",
    "table.genomes",
    "table.griefs",
    "table.holder_levels",
    "table.house_members",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.language_profiles",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_materials",
    "table.nodes",
    "table.passions",
    "table.people_biology",
    "table.people_culture",
    "table.personality_values",
    "table.prostheses",
    "table.routes",
    "table.skills",
    "table.spirit_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.wars",
    "table.world_domain_hooks",
    "table.world_maps",
)
@writes(
    "army.experience",
    "mortal.death_year",
    "mortal.hp",
    "table.armies",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.griefs",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.personality_values",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
)
async def war_casualties(ctx: TickContext) -> None:
    clashes = await clashes_of(ctx)
    ctx.count("duel_dead", await mark_duel_dead(ctx, clashes))
    count = await war_dead(ctx, clashes)
    ctx.count("clashes", len(clashes))
    ctx.count("dead", count.dead)
    ctx.count("wounded", count.wounded)
    await army_experience(ctx, clashes)
    await ctx.session.flush()


async def mark_disaster_dead(ctx: TickContext, event: EntityRow, flag: EntityFlag, phrase: str) -> int:
    marked = 0
    for mortal in await ctx.session.scalars(select(EntityRow).where(EntityRow.death_event_entity_id == event.id, EntityRow.entity_type == EntityType.MORTAL)):
        if mortal.status is not EntityStatus.DEAD:
            continue
        if not await BondRepository(ctx.session).exists_between(event.id, mortal.id, BondKind.KILLED):
            await connect(ctx.session, event.id, mortal.id, BondKind.KILLED, event.birth_epoch, description=phrase)
            marked += 1
        if await add_flag(ctx.session, mortal.id, flag, event.birth_epoch):
            marked += 1
    return marked


@reads(
    "event.severity",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "table.avatars",
    "table.bodies",
    "table.bonds",
    "table.captives",
    "table.community_societies",
    "table.cosmos",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.designated_heirs",
    "table.divine_wounds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.geasa",
    "table.griefs",
    "table.holder_levels",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incorporeal_rights",
    "table.injuries",
    "table.item_profiles",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.offices",
    "table.passions",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.reputations",
    "table.routes",
    "table.spirit_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.world_domain_hooks",
    "table.world_maps",
)
@writes(
    "mortal.death_year",
    "mortal.lifespan",
    "table.bodies",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.griefs",
    "table.house_profiles",
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
    "table.reputations",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
)
async def disaster_casualties(ctx: TickContext) -> None:
    losses = ctx.rules.casualties
    session = ctx.session
    events = list(await EntityRepository(session).with_flag(EntityFlag.DISASTER, status=None))
    struck_events = [
        (event, KIND_OF_DISASTER[event.engine_kind]) for event in events if event.birth_epoch == ctx.epoch and event.engine_kind in KIND_OF_DISASTER
    ]
    if not struck_events:
        return
    sides = await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules))
    knowledge = await KnowledgeMap.load(session)
    dead = 0
    for event, disaster in struck_events:
        plague = event.engine_kind is EngineKind.PLAGUE
        flag = EntityFlag.DIED_OF_PLAGUE if plague else EntityFlag.DIED_IN_DISASTER
        phrase = DISASTERS[disaster].death_phrase
        ctx.count("marked", await mark_disaster_dead(ctx, event, flag, phrase))
        if dead >= losses.disaster_epoch_cap:
            continue
        struck = [
            entity
            for entity in [await living_entity(session, bond.target_node_id) for bond in await BondRepository(session).outgoing(event.id, BondKind.CAUSED)]
            if entity is not None and entity.entity_type in COMMUNITY_TYPES
        ]
        struck_ids = {community.id for community in struck}
        severity = (stat(event, "severity") or 0) / 100
        rng = ctx.rng(seed_of("disaster_dead", event.id))
        this_event = 0
        for community in struck:
            base = (
                losses.plague_death * (losses.medicine_kept_pct / 100 if knowledge.knows(community.id, KnowledgeBranch.MEDICINE) else 1)
                if plague
                else losses.disaster_death
            )
            for mortal in sides.heroes_of(community.id):
                if this_event >= losses.disaster_event_cap or dead >= losses.disaster_epoch_cap:
                    break
                if mortal.status is not EntityStatus.CANON or mortal.location_id in struck_ids:
                    continue
                if not await fated(ctx, mortal, rng.chance(base * severity)):
                    continue
                if await fall(ctx, mortal, phrase, event.id, event=None, flag=flag):
                    this_event += 1
                    dead += 1
        if this_event:
            await note(ctx, f"{event.name} took {this_event} more named lives.", key="casualties.disaster_dead", ids=[event.id], feed=FeedCategory.DISASTER)
    ctx.count("dead", dead)
    await session.flush()


async def write_fate(ctx: TickContext, mortal_id: int, writ: FateWrit) -> EntityRow:
    mortal = await living_entity(ctx.session, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("A fate can only be written for a living mortal.")
    flags = await EntityRepository(ctx.session).flags(mortal.id)
    if writ is FateWrit.CLEAR:
        if not flags & {EntityFlag.DOOMED, EntityFlag.FATE_SHIELDED}:
            raise ValidationFailedError(f"No fate is written for {mortal.name}.")
        await remove_flag(ctx.session, mortal.id, EntityFlag.DOOMED)
        await remove_flag(ctx.session, mortal.id, EntityFlag.FATE_SHIELDED)
        return mortal
    wanted, other = (EntityFlag.DOOMED, EntityFlag.FATE_SHIELDED) if writ is FateWrit.DOOM else (EntityFlag.FATE_SHIELDED, EntityFlag.DOOMED)
    if wanted in flags:
        raise ValidationFailedError(f"That fate is already written for {mortal.name}.")
    await remove_flag(ctx.session, mortal.id, other)
    await add_flag(ctx.session, mortal.id, wanted, ctx.epoch)
    return mortal


WAR_PHASES = (Phase("war_casualties", war_casualties),)
DISASTER_PHASES = (Phase("disaster_casualties", disaster_casualties),)
PHASES = WAR_PHASES + DISASTER_PHASES
