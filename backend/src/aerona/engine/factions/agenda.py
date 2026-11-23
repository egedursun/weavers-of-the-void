from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.estates import PRIVILEGE_WISHES
from aerona.catalog.life.domain import GUILD_KINDS, ROBBER_KINDS, SECRET_KINDS
from aerona.catalog.life.factions import (
    CHOICES,
    CHOOSE_FACTION_GOAL_KINDS,
    CHOOSE_FACTION_GOAL_KINDS_2,
    CLASS_OF_KIND,
    GOAL_PLANS,
    GOAL_TARGET_FACTION_GOAL_KINDS,
    GOAL_WEIGHTS,
    LAW_GRIEVANCES,
    LAW_WISHES,
    MONOPOLY_GOODS,
    PETITION_TERMS_FACTION_GOAL_KINDS,
    REALM_GOAL_FACTION_GOAL_KINDS,
)
from aerona.catalog.life.finance import OUTLAWS
from aerona.catalog.life_traits import FACTION_ACTION_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.record_context import Term
from aerona.db.tables.communication import APPROVAL_MAX, APPROVAL_MIN, PublicOpinionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstateProfileRow
from aerona.db.tables.factions import FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.db.tables.polity import ClaimRow, PolityMemberRow
from aerona.db.tables.relations import SocialCircleRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import EstatePrivilege, FactionActionKind, FactionGoalKind, FactionKind, FactionRank, FactionScale
from aerona.domain.enums.life_traits import FactionActionKindTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import CoupCause, LawKind, OfficeKind
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.factions.book import FactionBook, log
from aerona.engine.factions.estates import grant
from aerona.engine.factions.offshoots import found_offshoot
from aerona.engine.faith.book import patron_node
from aerona.engine.finance.contraband import smuggle_books
from aerona.engine.labour.walkouts import strike_as_body
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.memories import remember
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import consider
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.offices import KEPT_OFFICES, appoint, seize_throne
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import StepDraft
from aerona.engine.recording.record import record as record_incident
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
DEFIANT = having(FACTION_ACTION_KIND_TRAITS, FactionActionKindTrait.DEFIANT)
ROBBER_STRENGTH = 30
THIN_PURSE = 50
HALF = 50
PRESSING = 30


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
                priority=clamp_int(getattr(table, GOAL_WEIGHTS[kind]) - len(factions.goals[faction_id]) * 20, 0, PERCENT),
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
    if kind in GOAL_TARGET_FACTION_GOAL_KINDS:
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
    elif kind is G.RUIN_RIVAL:
        found = (await rival_of(ctx, profile), None)
    elif kind is G.GAIN_PRIVILEGE and realm is not None:
        privilege = privilege_wish(profile)
        found = (realm.entity.id, privilege) if privilege is not None else (None, None)
    elif kind is G.WIN_OFFICE and realm is not None:
        office = next((row for row in realm.offices if row.kind not in KEPT_OFFICES and row.holder_entity_id is not None), None)
        found = (realm.entity.id, office.kind.value) if office is not None else (None, None)
    elif realm is not None:
        found = await realm_goal(ctx, realm, profile, kind)
    elif kind is G.LOOT and home is not None:
        found = home, None
    return found


async def rival_of(ctx: TickContext, profile: FactionProfileRow) -> int | None:
    if profile.home_entity_id is None:
        return None
    return await ctx.session.scalar(
        select(FactionProfileRow.faction_entity_id)
        .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
        .where(
            FactionProfileRow.home_entity_id == profile.home_entity_id,
            FactionProfileRow.faction_entity_id != profile.faction_entity_id,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by((FactionProfileRow.kind == profile.kind).desc(), FactionProfileRow.faction_entity_id)
        .limit(1)
    )


def privilege_wish(profile: FactionProfileRow) -> str | None:
    social_class = CLASS_OF_KIND.get(profile.kind)
    wishes = PRIVILEGE_WISHES[social_class] if social_class is not None else ()
    return wishes[0].value if wishes else None


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
    if kind in REALM_GOAL_FACTION_GOAL_KINDS and core is not None:
        wars = await ongoing_wars(ctx.session, core)
        if not wars:
            return None, None
        return wars[0].foe_id, None
    if kind is G.INDEPENDENCE and home is not None and home != core:
        return home, str(realm.entity.id)
    return (home, None) if kind is G.LOOT and home is not None else (None, None)


def choose(profile: FactionProfileRow, goal: FactionGoalRow, faction: EntityRow) -> FactionActionKind:
    strength = stat(faction, "strength") or 0
    kind = goal.kind
    action = CHOICES.get(kind, A.RECRUIT)
    if kind is G.INSTALL_CLAIMANT:
        action = A.ASSASSINATE if profile.kind in SECRET_KINDS else A.COUP if profile.armed else A.BRIBE
    elif kind is G.LOOT:
        action = A.RAID if profile.kind in ROBBER_KINDS and strength >= ROBBER_STRENGTH else A.SMUGGLE
    elif kind in CHOOSE_FACTION_GOAL_KINDS:
        action = A.PETITION if profile.treasury < THIN_PURSE else A.LOBBY
        if goal.progress >= HALF and profile.kind in GUILD_KINDS:
            action = A.STRIKE
        elif goal.progress >= HALF and profile.kind is FactionKind.PEASANT_LEAGUE:
            action = A.RIOT
    elif kind in CHOOSE_FACTION_GOAL_KINDS_2 and goal.progress >= PRESSING:
        action = A.PETITION
    elif kind is G.MONOPOLY_ON:
        action = A.BRIBE if profile.treasury >= THIN_PURSE else A.PETITION
    elif kind is G.RUIN_RIVAL and profile.kind in ROBBER_KINDS and strength >= ROBBER_STRENGTH:
        action = A.RAID
    elif kind is G.GAIN_PRIVILEGE and goal.progress >= HALF:
        action = A.PROPAGANDA
    return action


async def dues(ctx: TickContext, factions: FactionBook) -> None:
    table = ctx.rules.factions
    for faction_id, profile in factions.profiles.items():
        faction = factions.entities[faction_id]
        members = factions.members[faction_id]
        if "treasury" not in profile.locked:
            profile.treasury += len(members) * table.dues_per_member
            profile.treasury += (stat(faction, "wealth") or 0) // 10 * table.wealth_dues
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
    limit = scaled_cap(table.act_cap, table.act_cap_faction_divisor, len(factions.profiles))
    for faction_id, profile in ctx.rng("faction_act.order").shuffled(sorted(factions.profiles.items())):
        if acts >= limit:
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
        if success:
            await record_incident(
                ctx,
                "faction.acted",
                roles={IncidentRole.ACTOR: faction_id, IncidentRole.TARGET: goal.target_node_id},
                facts={"action": action, "goal": goal.kind},
            )
        if success and "progress" not in goal.locked:
            goal.progress = clamp_int(goal.progress + table.progress_step, 0, PERCENT)
            if goal.progress >= PERCENT and goal.achieved_epoch is None:
                goal.achieved_epoch = ctx.epoch
                profile.cohesion = clamp_int(profile.cohesion + table.progress_step, 0, PERCENT)
                await goal_met(Move(ctx, factions, realms, laws, profile, goal))
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
        A.PROPAGANDA: propaganda,
        A.BOYCOTT: boycott,
    }
    return await handlers[action](move)


async def propaganda(move: Move) -> bool:
    ctx, profile, goal = move.ctx, move.profile, move.goal
    realm = await realm_for(move.realms, profile)
    shift = ctx.rules.factions.propaganda_shift
    if realm is None or goal.target_node_id is None:
        log(ctx, profile.faction_entity_id, A.PROPAGANDA, goal=goal, success=False, note="no one to sway")
        return False
    gain_influence(profile, realm.entity.id, shift)
    rows = await ctx.session.scalars(
        select(PublicOpinionRow).where(PublicOpinionRow.community_node_id.in_(list(realm.members)), PublicOpinionRow.subject_node_id == goal.target_node_id)
    )
    for row in list(rows):
        if "approval" not in (row.locked or []) and not frozen(row.community_node_id):
            row.approval = clamp_int(row.approval + shift, APPROVAL_MIN, APPROVAL_MAX)
    log(ctx, profile.faction_entity_id, A.PROPAGANDA, target=goal.target_node_id, goal=goal, amount=shift)
    return True


async def boycott(move: Move) -> bool:
    ctx, profile, goal = move.ctx, move.profile, move.goal
    target = await living_entity(ctx.session, goal.target_node_id) if goal.target_node_id is not None else None
    if target is None or frozen(target.id):
        log(ctx, profile.faction_entity_id, A.BOYCOTT, goal=goal, success=False, note="no one to shun")
        return False
    cut = ctx.rules.collective.boycott_income_cut_pct
    shift_stat(target, "wealth", -(stat(target, "wealth") or 0) * cut / PERCENT)
    rival = await ctx.session.get(FactionProfileRow, target.id)
    if rival is not None and "cohesion" not in rival.locked:
        rival.cohesion = clamp_int(rival.cohesion - ctx.rules.factions.ruin_cohesion, 0, PERCENT)
    log(ctx, profile.faction_entity_id, A.BOYCOTT, target=target.id, goal=goal, amount=cut)
    return True


async def goal_met(move: Move) -> None:
    ctx, profile, goal = move.ctx, move.profile, move.goal
    realm = await realm_for(move.realms, profile)
    if goal.kind is G.GAIN_PRIVILEGE and realm is not None and goal.target_key is not None:
        estate = await ctx.session.scalar(
            select(EstateProfileRow).where(
                EstateProfileRow.polity_entity_id == realm.entity.id, EstateProfileRow.social_class == CLASS_OF_KIND.get(profile.kind)
            )
        )
        if estate is not None and not frozen(estate.faction_entity_id):
            await grant(ctx, estate, EstatePrivilege(goal.target_key))
    elif goal.kind is G.WIN_OFFICE and realm is not None and goal.target_key is not None and profile.leader_entity_id is not None:
        office = realm.office(OfficeKind(goal.target_key))
        leader = await living_entity(ctx.session, profile.leader_entity_id)
        if office is not None and leader is not None and not frozen(leader.id) and office.holder_entity_id != leader.id:
            await appoint(ctx, realm, office, leader, by_id=realm.ruler_id, reason="won by a faction")
    await record_incident(
        ctx,
        "faction.goal_met",
        roles={IncidentRole.ACTOR: profile.faction_entity_id, IncidentRole.TARGET: goal.target_node_id},
        facts={"goal": goal.kind},
    )


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
        log(ctx, profile.faction_entity_id, A.LOBBY, goal=goal, success=False, note="no hearing at court")
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
        note="a secret bribe",
    )
    if goal.kind is G.MONOPOLY_ON and goal.target_key is not None and "monopoly" not in profile.locked:
        profile.monopoly = goal.target_key
    await exposed(ctx, profile, A.BRIBE, target)
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
    log(ctx, profile.faction_entity_id, A.PETITION, target=realm.entity.id, goal=goal, success=proposal is not None, note=f"asked for {spoken(kind)}")
    return proposal is not None


def petition_terms(laws: LawBook, realm: Realm, profile: FactionProfileRow, goal: FactionGoalRow) -> tuple[LawKind | None, dict[str, int | str | bool]]:
    if goal.kind in PETITION_TERMS_FACTION_GOAL_KINDS:
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
    await strike_as_body(ctx, profile.faction_entity_id, place)
    await record_incident(
        ctx,
        "faction.strike",
        roles={IncidentRole.ACTOR: profile.faction_entity_id, IncidentRole.PLACE: place.id},
        facts={"unrest": table.strike_unrest, "prosperity_lost": table.strike_prosperity},
        place=place.id,
        terms=[Term("rules.factions.strike_unrest", table.strike_unrest), Term("rules.factions.strike_prosperity", -table.strike_prosperity)],
        steps=(StepDraft(StepAction.STRIKE_WORK, actor=profile.faction_entity_id, target=place.id, amount=table.strike_prosperity, unit=FactUnit.PERCENT),),
    )
    return True


async def riot(move: Move) -> bool:
    ctx, profile, goal = move.ctx, move.profile, move.goal
    table = ctx.rules.factions
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id or -1)
    if town is None:
        return False
    if "public_order" not in town.locked:
        town.public_order = clamp_int(town.public_order - table.riot_order, 0, PERCENT)
    profile.reputation = clamp_int(profile.reputation - table.reputation_step, 0, PERCENT) if "reputation" not in profile.locked else profile.reputation
    log(ctx, profile.faction_entity_id, A.RIOT, target=profile.home_entity_id, goal=goal)
    await record_incident(
        ctx,
        "faction.riot",
        roles={IncidentRole.ACTOR: profile.faction_entity_id, IncidentRole.PLACE: profile.home_entity_id},
        facts={"order_lost": table.riot_order},
        place=profile.home_entity_id,
        terms=[Term("rules.factions.riot_order", -table.riot_order)],
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
    seized = await seize_throne(ctx, realm, claimant, CoupCause.FACTION, backer_id=faction.id)
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
                f"killed by the assassins of {factions.entities[profile.faction_entity_id].name}",
                killer_id=profile.faction_entity_id,
            ),
        )
    await exposed(ctx, profile, A.ASSASSINATE, mark.id)
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
    await record_incident(
        ctx,
        "faction.raid",
        roles={IncidentRole.ACTOR: profile.faction_entity_id, IncidentRole.VICTIM: victim.id},
        facts={"loot": table.raid_loot, "prosperity_lost": table.raid_prosperity},
        place=victim.id,
        terms=[Term("rules.banditry.raid_loot", table.raid_loot)],
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
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [profile.home_entity_id])
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


async def exposed(ctx: TickContext, profile: FactionProfileRow, deed: FactionActionKind, target: int | None) -> bool:
    table = ctx.rules.intrigue
    chance = table.exposure_pct * (PERCENT - profile.secrecy) / PERCENT
    if not ctx.rng(f"exposed.{profile.faction_entity_id}.{ctx.epoch}").chance(chance):
        return False
    if "reputation" not in profile.locked:
        profile.reputation = clamp_int(profile.reputation - table.exposure_reputation, 0, PERCENT)
    await record_incident(
        ctx,
        "faction.exposed",
        roles={IncidentRole.ACCUSED: profile.faction_entity_id, IncidentRole.TARGET: target},
        facts={"deed": deed, "reputation_lost": table.exposure_reputation},
        terms=[Term("rules.intrigue.exposure_pct", chance)],
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
        child = await found_offshoot(
            ctx,
            parent,
            profile,
            name=f"the true {parent.name.removeprefix('the ')}",
            body=f"Those who left {parent.name}, saying it had strayed from its aims.",
            share_pct=PERCENT // 2,
            leaving=members[len(members) // 2 :],
        )
        log(ctx, faction_id, A.SCHISM, target=child.id)
        await record_incident(
            ctx,
            "faction.schism",
            roles={IncidentRole.PREDECESSOR: faction_id, IncidentRole.PRODUCT: child.id},
            facts={
                "members_left": len(members) - len(members) // 2,
            },
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
