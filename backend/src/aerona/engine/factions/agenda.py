from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.db.tables.polity import ClaimRow, PolityMemberRow
from aerona.db.tables.relations import SocialCircleRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import (
    GUILD_KINDS,
    ROBBER_KINDS,
    SECRET_KINDS,
    FactionActionKind,
    FactionGoalKind,
    FactionKind,
    FactionRank,
    FactionScale,
)
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import LawKind, OfficeKind
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.factions.book import CLASS_OF_KIND, FactionBook, log
from aerona.engine.faith.book import patron_node
from aerona.engine.finance.contraband import OUTLAWS, smuggle_books
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import consider
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.offices import seize_throne
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.renown.currencies import restraint
from aerona.engine.services.war import ongoing_wars

G = FactionGoalKind


@dataclass(frozen=True)
class Move:
    ctx: TickContext
    factions: FactionBook
    realms: RealmBook
    laws: LawBook
    profile: FactionProfileRow
    goal: FactionGoalRow


A = FactionActionKind
DEFIANT = frozenset({A.STRIKE, A.RIOT, A.COUP, A.ASSASSINATE})
ROBBER_STRENGTH = 30
THIN_PURSE = 50
HALF = 50
PRESSING = 30
GOAL_PLANS: dict[FactionKind, tuple[FactionGoalKind, ...]] = {
    FactionKind.MERCHANT_GUILD: (G.LOWER_TAXES, G.MONOPOLY_ON, G.PEACE_WITH),
    FactionKind.CRAFT_GUILD: (G.PROTECT_CRAFT, G.MONOPOLY_ON, G.LOWER_TAXES),
    FactionKind.PRIESTHOOD: (G.CONVERT_REALM, G.ENACT_LAW),
    FactionKind.WARRIOR_ORDER: (G.WAR_ON, G.ENACT_LAW),
    FactionKind.NOBLE_COUNCIL: (G.INSTALL_CLAIMANT, G.ABOLISH_LAW, G.LOWER_TAXES),
    FactionKind.PEASANT_LEAGUE: (G.LOWER_TAXES, G.ABOLISH_LAW),
    FactionKind.REBELS: (G.INDEPENDENCE, G.INSTALL_CLAIMANT),
    FactionKind.BANDITS: (G.LOOT,),
    FactionKind.PIRATES: (G.LOOT,),
    FactionKind.VOID_PIRATES: (G.LOOT,),
    FactionKind.SOCIAL_CIRCLE: (),
    FactionKind.ASSASSINS: (G.INSTALL_CLAIMANT, G.LOOT),
    FactionKind.SCHOLARS_ACADEMY: (G.ENACT_LAW, G.PROTECT_CRAFT),
    FactionKind.SECRET_SOCIETY: (G.INSTALL_CLAIMANT, G.CONVERT_REALM),
    FactionKind.MERCENARY_COMPANY: (G.LOOT, G.WAR_ON),
    FactionKind.INTERWORLD_FEDERATION: (G.PEACE_WITH, G.LOWER_TAXES),
    FactionKind.WANDERING_MARKET: (G.LOWER_TAXES, G.MONOPOLY_ON),
}
LAW_WISHES: dict[FactionKind, tuple[LawKind, dict[str, int | str | bool]]] = {
    FactionKind.PRIESTHOOD: (LawKind.TITHE, {"rate": 10, "enforced": True}),
    FactionKind.WARRIOR_ORDER: (LawKind.VETERAN_PENSION, {"amount": 30}),
    FactionKind.SCHOLARS_ACADEMY: (LawKind.LICENSED_MAGIC, {"fee": 10}),
    FactionKind.CRAFT_GUILD: (LawKind.GUILD_CHARTER, {"monopoly": True}),
    FactionKind.MERCHANT_GUILD: (LawKind.GUILD_CHARTER, {"monopoly": True}),
}
LAW_GRIEVANCES: dict[FactionKind, LawKind] = {
    FactionKind.PEASANT_LEAGUE: LawKind.SERFDOM,
    FactionKind.NOBLE_COUNCIL: LawKind.TAX_RATE,
    FactionKind.MERCHANT_GUILD: LawKind.TOLLS,
}
MONOPOLY_GOODS: dict[FactionKind, CommodityKind] = {
    FactionKind.MERCHANT_GUILD: CommodityKind.LUXURIES,
    FactionKind.CRAFT_GUILD: CommodityKind.TOOLS,
    FactionKind.WANDERING_MARKET: CommodityKind.LUXURIES,
}


async def realm_for(book: RealmBook, profile: FactionProfileRow) -> Realm | None:
    return book.realm_of(profile.home_entity_id)


async def plan_goals(ctx: TickContext, factions: FactionBook, realms: RealmBook) -> int:
    table = ctx.rules.factions
    made = 0
    for faction_id, profile in factions.profiles.items():
        if frozen(faction_id) or "goals" in profile.locked or len(factions.goals[faction_id]) >= table.goal_cap:
            continue
        held = {goal.kind for goal in factions.goals[faction_id]}
        for kind in GOAL_PLANS.get(profile.kind, ()):
            if kind in held or len(factions.goals[faction_id]) >= table.goal_cap:
                continue
            target, key = await goal_target(ctx, realms, profile, kind)
            if target is None and key is None:
                continue
            goal = FactionGoalRow(
                faction_entity_id=faction_id,
                kind=kind,
                target_node_id=target,
                target_key=key,
                priority=PERCENT - len(factions.goals[faction_id]) * 20,
                progress=0,
                since_epoch=ctx.epoch,
                set_by_player=False,
                locked=[],
            )
            ctx.session.add(goal)
            factions.goals[faction_id].append(goal)
            made += 1
    await ctx.session.flush()
    return made


async def goal_target(ctx: TickContext, realms: RealmBook, profile: FactionProfileRow, kind: FactionGoalKind) -> tuple[int | None, str | None]:
    realm = await realm_for(realms, profile)
    home = profile.home_entity_id
    found: tuple[int | None, str | None] = (None, None)
    if kind in {G.LOWER_TAXES, G.PROTECT_CRAFT}:
        found = (realm.entity.id if realm is not None else home), None
    elif kind is G.MONOPOLY_ON:
        good = MONOPOLY_GOODS.get(profile.kind)
        found = (home, good.value) if good is not None else (None, None)
    elif kind is G.ENACT_LAW:
        wish = LAW_WISHES.get(profile.kind)
        found = ((realm.entity.id if realm is not None else None), wish[0].value) if wish is not None else (None, None)
    elif kind is G.ABOLISH_LAW:
        grievance = LAW_GRIEVANCES.get(profile.kind)
        found = ((realm.entity.id if realm is not None else None), grievance.value) if grievance is not None else (None, None)
    elif realm is not None:
        found = await realm_goal(ctx, realm, profile, kind)
    elif kind is G.LOOT and home is not None:
        found = home, None
    return found


async def realm_goal(ctx: TickContext, realm: Realm, profile: FactionProfileRow, kind: FactionGoalKind) -> tuple[int | None, str | None]:
    home = profile.home_entity_id
    core = realm.profile.core_entity_id
    if kind is G.INSTALL_CLAIMANT:
        claim = await ctx.session.scalar(
            select(ClaimRow).where(ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.strength.desc()).limit(1)
        )
        return (claim.claimant_entity_id, str(realm.entity.id)) if claim is not None else (None, None)
    if kind is G.CONVERT_REALM and home is not None:
        god = await patron_node(ctx.session, profile.faction_entity_id) or await patron_node(ctx.session, home)
        return (realm.entity.id, str(god)) if god is not None else (None, None)
    if kind in {G.WAR_ON, G.PEACE_WITH} and core is not None:
        wars = await ongoing_wars(ctx.session, core)
        if not wars:
            return None, None
        return (wars[0].defender_id if wars[0].attacker_id == core else wars[0].attacker_id), None
    if kind is G.INDEPENDENCE and home is not None and home != core:
        return home, str(realm.entity.id)
    return (home, None) if kind is G.LOOT and home is not None else (None, None)


CHOICES: dict[FactionGoalKind, FactionActionKind] = {
    G.ENACT_LAW: A.LOBBY,
    G.ABOLISH_LAW: A.LOBBY,
    G.CONVERT_REALM: A.LOBBY,
    G.WAR_ON: A.FUND_WAR,
    G.INDEPENDENCE: A.RIOT,
    G.PEACE_WITH: A.LOBBY,
}


def choose(profile: FactionProfileRow, goal: FactionGoalRow, faction: EntityRow) -> FactionActionKind:
    strength = stat(faction, "strength") or 0
    kind = goal.kind
    action = CHOICES.get(kind, A.RECRUIT)
    if kind is G.INSTALL_CLAIMANT:
        action = A.ASSASSINATE if profile.kind in SECRET_KINDS else A.COUP if profile.armed else A.BRIBE
    elif kind is G.LOOT:
        action = A.RAID if profile.kind in ROBBER_KINDS and strength >= ROBBER_STRENGTH else A.SMUGGLE
    elif kind in {G.LOWER_TAXES, G.PROTECT_CRAFT}:
        action = A.PETITION if profile.treasury < THIN_PURSE else A.LOBBY
        if goal.progress >= HALF and profile.kind in GUILD_KINDS:
            action = A.STRIKE
        elif goal.progress >= HALF and profile.kind is FactionKind.PEASANT_LEAGUE:
            action = A.RIOT
    elif kind in {G.ENACT_LAW, G.ABOLISH_LAW, G.CONVERT_REALM} and goal.progress >= PRESSING:
        action = A.PETITION
    elif kind is G.MONOPOLY_ON:
        action = A.BRIBE if profile.treasury >= THIN_PURSE else A.PETITION
    return action


async def dues(ctx: TickContext, factions: FactionBook) -> None:
    table = ctx.rules.factions
    for faction_id, profile in factions.profiles.items():
        faction = factions.entities[faction_id]
        members = factions.members[faction_id]
        if "treasury" not in profile.locked:
            profile.treasury += len(members) * table.dues_per_member + (stat(faction, "wealth") or 0) // 10 * table.wealth_dues
        if "scale" not in profile.locked:
            reach = len(profile.influence_over)
            profile.scale = (
                FactionScale.NETWORK
                if reach >= table.network_influence
                else FactionScale.ORGANISATION
                if len(members) >= table.company_members
                else FactionScale.COMPANY
                if len(members) >= table.band_members
                else FactionScale.BAND
            )
        leader = next((row for row in members if row.rank is FactionRank.LEADER), None)
        if leader is None and members and "leader" not in profile.locked:
            best = max(members, key=lambda row: (row.rank is FactionRank.OFFICER, -row.joined_epoch, -row.mortal_entity_id))
            best.rank = FactionRank.LEADER
            leader = best
        if "leader" not in profile.locked:
            profile.leader_entity_id = leader.mortal_entity_id if leader is not None else None
        profile.updated_epoch = ctx.epoch


async def pursue(ctx: TickContext, factions: FactionBook, realms: RealmBook, laws: LawBook) -> int:
    table = ctx.rules.factions
    acts = 0
    for faction_id, profile in sorted(factions.profiles.items()):
        if acts >= table.act_cap:
            break
        if frozen(faction_id):
            continue
        goals = sorted(factions.goals[faction_id], key=lambda goal: (-goal.priority, goal.id))
        realm = await realm_for(realms, profile)
        suppress, press = await restraint(ctx, realm.entity.id if realm is not None else None)
        if not goals or not ctx.rng(f"faction_act.{faction_id}.{ctx.epoch}").chance(table.act_chance * press):
            if goals and "cohesion" not in profile.locked:
                profile.cohesion = clamp_int(profile.cohesion - table.cohesion_drift, 0, PERCENT)
            continue
        goal = goals[0]
        faction = factions.entities[faction_id]
        action = choose(profile, goal, faction)
        if action in DEFIANT and not ctx.rng(f"faction_dare.{faction_id}.{ctx.epoch}").chance(PERCENT * suppress):
            continue
        success = await act(Move(ctx, factions, realms, laws, profile, goal), action)
        if success and "progress" not in goal.locked:
            goal.progress = clamp_int(goal.progress + table.progress_step, 0, PERCENT)
            if goal.progress >= PERCENT:
                goal.achieved_epoch = ctx.epoch
                profile.cohesion = clamp_int(profile.cohesion + table.progress_step, 0, PERCENT)
        acts += 1
    return acts


async def act(move: Move, action: FactionActionKind) -> bool:
    handlers = {
        A.LOBBY: lobby,
        A.BRIBE: bribe,
        A.PETITION: petition,
        A.STRIKE: strike,
        A.RIOT: riot,
        A.COUP: coup,
        A.ASSASSINATE: assassinate,
        A.SMUGGLE: smuggle,
        A.RAID: raid,
        A.FUND_WAR: fund_war,
        A.RECRUIT: recruit,
    }
    return await handlers[action](move)


async def holder_of(realm: Realm | None, *kinds: OfficeKind) -> int | None:
    if realm is None:
        return None
    for kind in kinds:
        office = realm.office(kind)
        if office is not None and office.holder_entity_id is not None:
            return office.holder_entity_id
    return None


def gain_influence(profile: FactionProfileRow, realm_id: int, amount: int) -> None:
    if "influence_over" in profile.locked:
        return
    key = str(realm_id)
    profile.influence_over = {**profile.influence_over, key: clamp_int(profile.influence_over.get(key, 0) + amount, 0, PERCENT)}


async def lobby(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    table = ctx.rules.factions
    realm = await realm_for(realms, profile)
    target = await holder_of(realm, OfficeKind.CHANCELLOR, OfficeKind.RULER)
    if realm is None or target is None or profile.treasury < table.lobby_cost:
        log(ctx, profile.faction_entity_id, A.LOBBY, goal=goal, success=False, note="no ear at court")
        return False
    profile.treasury -= table.lobby_cost
    gain_influence(profile, realm.entity.id, table.lobby_influence)
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=target,
        subject_id=profile.faction_entity_id,
        kind=MemoryKind.GOODWILL,
        magnitude=table.lobby_influence,
        epoch=ctx.epoch,
        note="lobbied at court",
    )
    log(ctx, profile.faction_entity_id, A.LOBBY, target=target, goal=goal, amount=table.lobby_cost)
    return True


async def bribe(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    factions = move.factions
    table = ctx.rules.factions
    realm = await realm_for(realms, profile)
    target = await holder_of(realm, OfficeKind.TREASURER, OfficeKind.HIGH_JUDGE, OfficeKind.RULER)
    if realm is None or target is None or profile.treasury < table.bribe_cost:
        log(ctx, profile.faction_entity_id, A.BRIBE, goal=goal, success=False, note="no one to buy")
        return False
    profile.treasury -= table.bribe_cost
    gain_influence(profile, realm.entity.id, table.bribe_influence)
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=target,
        subject_id=profile.faction_entity_id,
        kind=MemoryKind.GIFTED_ME,
        magnitude=table.bribe_opinion,
        epoch=ctx.epoch,
        note="a purse in the dark",
    )
    if goal.kind is G.MONOPOLY_ON and goal.target_key is not None and "monopoly" not in profile.locked:
        profile.monopoly = goal.target_key
    await exposed(ctx, factions, profile, "bribed the officers of the realm")
    log(ctx, profile.faction_entity_id, A.BRIBE, target=target, goal=goal, amount=table.bribe_cost)
    return True


async def petition(move: Move) -> bool:
    ctx, factions, realms, laws, profile, goal = move.ctx, move.factions, move.realms, move.laws, move.profile, move.goal
    realm = await realm_for(realms, profile)
    if realm is None:
        return False
    sway = profile.influence_over.get(str(realm.entity.id), 0) + (stat(factions.entities[profile.faction_entity_id], "sway") or 0) // 2
    kind, params = petition_terms(laws, realm, profile, goal)
    if kind is None:
        log(ctx, profile.faction_entity_id, A.PETITION, goal=goal, success=False, note="nothing to ask")
        return False
    proposal = await consider(ctx, realm, laws, kind, params, sponsor_id=profile.faction_entity_id, sway=sway)
    log(ctx, profile.faction_entity_id, A.PETITION, target=realm.entity.id, goal=goal, success=proposal is not None, note=kind.value)
    return proposal is not None


def petition_terms(laws: LawBook, realm: Realm, profile: FactionProfileRow, goal: FactionGoalRow) -> tuple[LawKind | None, dict[str, int | str | bool]]:
    if goal.kind in {G.LOWER_TAXES, G.PROTECT_CRAFT}:
        rate = laws.param(realm.entity.id, LawKind.TAX_RATE, "rate")
        return LawKind.TAX_RATE, {"rate": max(0, int(rate or 10) - 5)}
    if goal.kind is G.ENACT_LAW and goal.target_key is not None:
        wish = LAW_WISHES.get(profile.kind)
        params = dict(wish[1]) if wish is not None else {}
        if LawKind(goal.target_key) is LawKind.GUILD_CHARTER:
            params["guild_id"] = profile.faction_entity_id
        if LawKind(goal.target_key) is LawKind.FRANCHISE:
            params = {"voters": "all"}
        return LawKind(goal.target_key), params
    if goal.kind is G.ABOLISH_LAW and goal.target_key is not None:
        kind = LawKind(goal.target_key)
        relief: dict[LawKind, dict[str, int | str | bool]] = {
            LawKind.SERFDOM: {"allowed": False},
            LawKind.TAX_RATE: {"rate": 5},
            LawKind.TOLLS: {"rate": 0},
            LawKind.SLAVERY: {"status": "banned"},
        }
        return kind, relief.get(kind, {})
    if goal.kind is G.CONVERT_REALM:
        return LawKind.RELIGIOUS_TOLERANCE, {"level": "free"}
    if goal.kind is G.MONOPOLY_ON:
        return LawKind.GUILD_CHARTER, {"guild_id": profile.faction_entity_id, "monopoly": True}
    return None, {}


async def strike(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    factions = move.factions
    table = ctx.rules.factions
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id or -1)
    place = await living_entity(ctx.session, profile.home_entity_id) if profile.home_entity_id is not None else None
    if town is None or place is None:
        return False
    if "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest + table.strike_unrest, 0, PERCENT)
    shift_stat(place, "prosperity", -table.strike_prosperity, ctx.rules.society.default_stat)
    realm = await realm_for(realms, profile)
    if realm is not None:
        gain_influence(profile, realm.entity.id, table.lobby_influence)
    log(ctx, profile.faction_entity_id, A.STRIKE, target=place.id, goal=goal)
    await note(
        ctx,
        f"{factions.entities[profile.faction_entity_id].name} laid down its tools; {place.name} stood still.",
        key="faction.strike",
        ids=[profile.faction_entity_id, place.id],
        kind=ChronicleKind.CIVILIZATION,
    )
    return True


async def riot(move: Move) -> bool:
    ctx, factions, profile, goal = move.ctx, move.factions, move.profile, move.goal
    table = ctx.rules.factions
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id or -1)
    if town is None:
        return False
    if "public_order" not in town.locked:
        town.public_order = clamp_int(town.public_order - table.riot_order, 0, PERCENT)
    profile.reputation = clamp_int(profile.reputation - table.reputation_step, 0, PERCENT) if "reputation" not in profile.locked else profile.reputation
    log(ctx, profile.faction_entity_id, A.RIOT, target=profile.home_entity_id, goal=goal)
    await note(
        ctx,
        f"{factions.entities[profile.faction_entity_id].name} took to the streets.",
        key="faction.riot",
        ids=[profile.faction_entity_id],
        kind=ChronicleKind.CIVILIZATION,
    )
    return True


async def coup(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    factions = move.factions
    table = ctx.rules.intrigue
    faction = factions.entities[profile.faction_entity_id]
    realm = await realm_for(realms, profile)
    claimant = await living_entity(ctx.session, goal.target_node_id) if goal.target_node_id is not None else None
    if realm is None or claimant is None or claimant.entity_type is not EntityType.MORTAL or (stat(faction, "strength") or 0) < table.coup_strength:
        log(ctx, faction.id, A.COUP, goal=goal, success=False, note="not strong enough")
        return False
    if not ctx.rng(f"faction_coup.{faction.id}.{ctx.epoch}").chance(table.coup_chance):
        log(ctx, faction.id, A.COUP, target=claimant.id, goal=goal, success=False, note="the guard held")
        shift_stat(faction, "strength", -table.coup_strength // 2, ctx.rules.society.default_stat)
        return False
    seized = await seize_throne(ctx, realm, claimant, f"{faction.name} raised its swords for {claimant.name}", backer_id=faction.id)
    log(ctx, faction.id, A.COUP, target=claimant.id, goal=goal, success=seized)
    if seized:
        goal.progress = PERCENT
    return seized


async def assassinate(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    factions = move.factions
    table = ctx.rules.intrigue
    realm = await realm_for(realms, profile)
    mark_id = realm.ruler_id if realm is not None and goal.kind is G.INSTALL_CLAIMANT else None
    mark = await living_entity(ctx.session, mark_id) if mark_id is not None else None
    if mark is None:
        log(ctx, profile.faction_entity_id, A.ASSASSINATE, goal=goal, success=False, note="no mark")
        return False
    struck = ctx.rng(f"assassin.{profile.faction_entity_id}.{ctx.epoch}").chance(table.assassinate_chance)
    if struck:
        await apply_hits(
            ctx,
            mark,
            Harm(
                table.assassinate_hp,
                HarmCause.POISON,
                f"slain by the knives of {factions.entities[profile.faction_entity_id].name}",
                killer_id=profile.faction_entity_id,
            ),
        )
    await exposed(ctx, factions, profile, f"plotted the death of {mark.name}")
    log(ctx, profile.faction_entity_id, A.ASSASSINATE, target=mark.id, goal=goal, success=struck)
    return struck


async def smuggle(move: Move) -> bool:
    ctx, profile, goal = move.ctx, move.profile, move.goal
    table = ctx.rules.banditry
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id or -1)
    if town is not None and "crime" not in town.locked:
        town.crime = clamp_int(town.crime + table.smuggle_crime, 0, PERCENT)
    profile.treasury += table.smuggle_loot
    if profile.kind in OUTLAWS:
        await smuggle_books(ctx, profile)
    log(ctx, profile.faction_entity_id, A.SMUGGLE, target=profile.home_entity_id, goal=goal, amount=table.smuggle_loot)
    return True


async def raid(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    factions = move.factions
    table = ctx.rules.banditry
    charter = profile.chartered_by_entity_id
    victim = await living_entity(ctx.session, goal.target_node_id or profile.home_entity_id) if (goal.target_node_id or profile.home_entity_id) else None
    if victim is None:
        return False
    if charter is not None and realms.realm_of(victim.id) is not None and realms.realm_of(victim.id) is realms.realms.get(charter):
        log(ctx, profile.faction_entity_id, A.RAID, target=victim.id, goal=goal, success=False, note="spared the charterer")
        return False
    shift_stat(victim, "prosperity", -table.raid_prosperity, ctx.rules.society.default_stat)
    profile.treasury += table.raid_loot
    log(ctx, profile.faction_entity_id, A.RAID, target=victim.id, goal=goal, amount=table.raid_loot)
    await note(
        ctx,
        f"{factions.entities[profile.faction_entity_id].name} raided {victim.name}.",
        key="faction.raid",
        ids=[profile.faction_entity_id, victim.id],
        kind=ChronicleKind.CIVILIZATION,
    )
    return True


async def fund_war(move: Move) -> bool:
    ctx, realms, profile, goal = move.ctx, move.realms, move.profile, move.goal
    table = ctx.rules.factions
    realm = await realm_for(realms, profile)
    if realm is None or goal.target_node_id is None or profile.treasury <= 0:
        return False
    given = round_half_up(profile.treasury * table.fund_war_share_pct / PERCENT)
    profile.treasury -= given
    realm.profile.war_chest += given
    gain_influence(profile, realm.entity.id, table.lobby_influence)
    log(ctx, profile.faction_entity_id, A.FUND_WAR, target=realm.entity.id, goal=goal, amount=given)
    return given > 0


async def circle_folk(ctx: TickContext, home_id: int | None) -> set[int]:
    if home_id is None:
        return set()
    circles = select(SocialCircleRow.faction_entity_id).where(SocialCircleRow.meeting_place_id == home_id)
    return set(await ctx.session.scalars(select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id.in_(circles))))


async def recruit(move: Move) -> bool:
    ctx, factions, profile, goal = move.ctx, move.factions, move.profile, move.goal
    table = ctx.rules.factions
    social = CLASS_OF_KIND.get(profile.kind)
    held = {row.mortal_entity_id for row in factions.members[profile.faction_entity_id]}
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == profile.home_entity_id
    )
    if social is not None:
        statement = statement.where(EntityRow.social_class == social)
    joined = 0
    circled = await circle_folk(ctx, profile.home_entity_id) if profile.kind is not FactionKind.SOCIAL_CIRCLE else set()
    cap = table.recruit_members + round(table.recruit_members * ctx.rules.circles.recruit_pct / PERCENT) if circled else table.recruit_members
    candidates = sorted(await ctx.session.scalars(statement), key=lambda mortal: (mortal.id not in circled, mortal.id))
    for mortal in candidates:
        limit = cap if mortal.id in circled else table.recruit_members
        if joined >= limit or mortal.id in held:
            continue
        row = FactionMembershipRow(
            faction_entity_id=profile.faction_entity_id, mortal_entity_id=mortal.id, rank=FactionRank.NOVICE, joined_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        factions.members[profile.faction_entity_id].append(row)
        joined += 1
    if social is not None and "cohort_share" not in profile.locked:
        share = profile.cohort_share.get(social.value, 0.0)
        profile.cohort_share = {**profile.cohort_share, social.value: min(float(PERCENT), share + table.recruit_share)}
    log(ctx, profile.faction_entity_id, A.RECRUIT, target=profile.home_entity_id, goal=goal, amount=joined)
    return True


async def exposed(ctx: TickContext, factions: FactionBook, profile: FactionProfileRow, deed: str) -> bool:
    table = ctx.rules.intrigue
    chance = table.exposure_pct * (PERCENT - profile.secrecy) / PERCENT
    if not ctx.rng(f"exposed.{profile.faction_entity_id}.{ctx.epoch}").chance(chance):
        return False
    if "reputation" not in profile.locked:
        profile.reputation = clamp_int(profile.reputation - table.exposure_reputation, 0, PERCENT)
    await note(
        ctx,
        f"It came out that {factions.entities[profile.faction_entity_id].name} {deed}.",
        key="faction.exposed",
        ids=[profile.faction_entity_id],
        kind=ChronicleKind.CIVILIZATION,
    )
    return True


async def schisms(ctx: TickContext, factions: FactionBook) -> int:
    table = ctx.rules.factions
    split = 0
    for faction_id, profile in list(factions.profiles.items()):
        members = factions.members[faction_id]
        if profile.cohesion >= table.schism_cohesion or len(members) < 2 or "schism" in profile.locked:
            continue
        if not ctx.rng(f"schism.{faction_id}.{ctx.epoch}").chance(table.schism_chance):
            continue
        parent = factions.entities[faction_id]
        child = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.FACTION,
                name=f"the true {parent.name.removeprefix('the ')}",
                body=f"Those who left {parent.name}, saying it had lost its way.",
                stats=FactionStats(
                    strength=(stat(parent, "strength") or 0) // 2, wealth=(stat(parent, "wealth") or 0) // 2, sway=(stat(parent, "sway") or 0) // 2
                ),
                power=max(1, parent.power_level - 1),
                location_id=parent.location_id,
                world_id=parent.world_id,
                subtype=parent.subtype,
                engine_kind=parent.engine_kind,
                affiliated_entity_id=parent.affiliated_entity_id,
                pending=False,
            ),
        )
        twin = FactionProfileRow(
            faction_entity_id=child.id,
            kind=profile.kind,
            scale=FactionScale.BAND,
            treasury=profile.treasury // 2,
            cohesion=80,
            secrecy=profile.secrecy,
            armed=profile.armed,
            reputation=profile.reputation,
            influence_over={},
            cohort_share={},
            home_entity_id=profile.home_entity_id,
            outlawed=profile.outlawed,
            pay=profile.pay,
            loyalty=50,
            unpaid_epochs=0,
            founded_epoch=ctx.epoch,
            updated_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(twin)
        profile.treasury -= profile.treasury // 2
        profile.cohesion = clamp_int(profile.cohesion + 30, 0, PERCENT)
        for row in members[len(members) // 2 :]:
            row.faction_entity_id = child.id
        log(ctx, faction_id, A.SCHISM, target=child.id)
        await note(
            ctx,
            f"{parent.name} split; the discontented founded {child.name}.",
            key="faction.schism",
            ids=[faction_id, child.id],
            kind=ChronicleKind.CIVILIZATION,
        )
        split += 1
    return split


async def monopolies(ctx: TickContext, factions: FactionBook, laws: LawBook) -> int:
    table = ctx.rules.factions
    held = 0
    for faction_id, profile in factions.profiles.items():
        charter: int | None = None
        for law_id, row in laws.profiles.items():
            if row.kind is LawKind.GUILD_CHARTER and int(row.params.get("guild_id", 0)) == faction_id and bool(row.params.get("monopoly")):
                charter = law_id
        if charter is not None and profile.monopoly is None and "monopoly" not in profile.locked:
            profile.monopoly = MONOPOLY_GOODS.get(profile.kind, CommodityKind.LUXURIES).value
        if profile.monopoly is None:
            continue
        town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id or -1)
        if town is not None and "crime" not in town.locked:
            town.crime = clamp_int(town.crime + table.monopoly_crime, 0, PERCENT)
        held += 1
    return held


async def influence_from_members(ctx: TickContext, factions: FactionBook) -> None:
    for profile in factions.profiles.values():
        polity = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == profile.home_entity_id).limit(1))
        if polity is None or "influence_over" in profile.locked:
            continue
        key = str(polity)
        society = await ctx.session.get(CommunitySocietyRow, profile.home_entity_id or -1)
        social = CLASS_OF_KIND.get(profile.kind)
        base = round_half_up(society.share(social) * profile.cohort_share.get(social.value, 0.0) / PERCENT) if society is not None and social is not None else 0
        profile.influence_over = {**profile.influence_over, key: clamp_int(max(profile.influence_over.get(key, 0), base), 0, PERCENT)}
