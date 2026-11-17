from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civics import LAW_GATES
from aerona.catalog.kinds.governance import DECISION_RULES
from aerona.catalog.laws import LAW_PARAMS, LAW_TITLES, defaults_for
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.read_memo import memoized
from aerona.db.tables.affairs import CouncilSeatRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.justice import LawProposalRow, ProposalStanceRow
from aerona.db.tables.polity import LawProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import EstatePrivilege, FactionGoalKind
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand
from aerona.domain.enums.justice import ProposalEvent, ProposalStance, ProposalState
from aerona.domain.enums.polity import DecisionRule, LawKind, LegitimacyBasis, OfficeKind
from aerona.engine.communication.opinion import mean_approval
from aerona.engine.context import TickContext
from aerona.engine.intrigue.favours import hook_on, owe, use_hook
from aerona.engine.lore.civics import realm_allows
from aerona.engine.mind.book import Values, values_for
from aerona.engine.mortal.standing import add_renown
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import enact, law_reading, validate
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat

COUNCIL = frozenset(
    {
        OfficeKind.CHANCELLOR,
        OfficeKind.MARSHAL,
        OfficeKind.TREASURER,
        OfficeKind.HIGH_JUDGE,
        OfficeKind.SPYMASTER,
        OfficeKind.REGENT,
        OfficeKind.CHAPLAIN,
        OfficeKind.HEAD_OF_GOVERNMENT,
        OfficeKind.MINISTER,
        OfficeKind.GENERAL,
        OfficeKind.SPEAKER,
    }
)
FOR = frozenset({ProposalStance.SUPPORT})
AGAINST = frozenset({ProposalStance.OPPOSE, ProposalStance.OBSTRUCT})
PROGRESS = "progress"
SUPPORT = "support"
OPPOSITION = "opposition"
PARAMS = "params"
STATE = "state"
DONE = 100


@dataclass
class EnactmentTally:
    passed: int = 0
    failed: int = 0
    withdrawn: int = 0
    events: int = 0
    hooked: int = 0


@dataclass
class Stand:
    stance: ProposalStance
    weight: int
    hooked: bool = False


@dataclass
class Hearing:
    realm: Realm
    row: LawProposalRow
    stands: dict[int, Stand] = field(default_factory=dict)


def law_title(kind: LawKind) -> str:
    return LAW_TITLES.get(kind, f"the {spoken(kind)} law")


async def debating(ctx: TickContext, polity_id: int) -> list[LawProposalRow]:
    return list(
        await ctx.session.scalars(
            select(LawProposalRow)
            .where(LawProposalRow.polity_entity_id == polity_id, LawProposalRow.state == ProposalState.DEBATING)
            .order_by(LawProposalRow.id)
        )
    )


async def pending_kind(ctx: TickContext, polity_id: int, kind: LawKind) -> LawProposalRow | None:
    return next((row for row in await debating(ctx, polity_id) if row.kind is kind), None)


async def propose(
    ctx: TickContext,
    realm: Realm,
    kind: LawKind,
    params: dict[str, int | str | bool],
    *,
    champion_id: int | None,
    basis: LegitimacyBasis,
    law_id: int | None = None,
) -> LawProposalRow | None:
    if held(realm.entity.id) or (champion_id is not None and held(champion_id)):
        return None
    if not await realm_allows(ctx.session, realm, LAW_GATES.get(kind)):
        return None
    if await pending_kind(ctx, realm.entity.id, kind) is not None or len(await debating(ctx, realm.entity.id)) >= ctx.rules.enactment.open_cap:
        return None
    row = LawProposalRow(
        polity_entity_id=realm.entity.id,
        kind=kind,
        params=validate(kind, params),
        champion_node_id=champion_id,
        law_entity_id=law_id,
        basis=basis,
        proposed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    champion = await living_entity(ctx.session, champion_id) if champion_id is not None else None
    who = champion.name if champion is not None else "the needs of the hour"
    await note(
        ctx,
        f"{who} brought {law_title(kind)} before {realm.entity.name}.",
        key="polity.law_proposed",
        ids=[realm.entity.id, *([champion.id] if champion is not None else [])],
        kind=ChronicleKind.CIVILIZATION,
    )
    return row


def stand_from(rules_threshold: int, reading: int, weight: int) -> Stand | None:
    if weight <= 0:
        return None
    if reading >= rules_threshold:
        return Stand(ProposalStance.SUPPORT, weight)
    if reading <= -rules_threshold:
        return Stand(ProposalStance.OPPOSE, weight)
    return None


async def judge_values(ctx: TickContext, row: LawProposalRow, values: Values) -> int:
    return law_reading(row.kind, row.params, values)


async def hear_ruler(ctx: TickContext, hearing: Hearing) -> None:
    table = ctx.rules.enactment
    ruler = hearing.realm.ruler_id
    if ruler is None or held(ruler):
        return
    rule = hearing.realm.profile.decision_rule
    weight = table.ruler_weight // DECISION_RULES[rule].ruler_divisor
    stand = stand_from(table.stance_threshold, await judge_values(ctx, hearing.row, await values_for(ctx.session, ruler)), weight)
    if stand is not None:
        hearing.stands[ruler] = stand


async def hear_council(ctx: TickContext, hearing: Hearing) -> None:
    table = ctx.rules.enactment
    rule = hearing.realm.profile.decision_rule
    weight = table.council_weight // DECISION_RULES[rule].council_divisor
    for office in hearing.realm.offices:
        holder = office.holder_entity_id
        if office.kind not in COUNCIL or holder is None or holder in hearing.stands or held(holder):
            continue
        stand = stand_from(table.stance_threshold, await judge_values(ctx, hearing.row, await values_for(ctx.session, holder)), weight)
        if stand is not None:
            hearing.stands[holder] = stand


async def hear_people(ctx: TickContext, hearing: Hearing) -> None:
    table = ctx.rules.enactment
    profile = hearing.realm.profile
    if profile.decision_rule is DecisionRule.ASSEMBLY and profile.core_entity_id is not None and not held(profile.core_entity_id):
        reading = await judge_values(ctx, hearing.row, await values_for(ctx.session, profile.core_entity_id))
        approval = await mean_approval(ctx, list(hearing.realm.members), hearing.row.champion_node_id)
        stand = stand_from(table.stance_threshold, round_half_up(reading + approval / 2), table.assembly_weight)
        if stand is not None:
            hearing.stands[profile.core_entity_id] = stand
    church = profile.state_religion_id
    if profile.decision_rule is DecisionRule.DIVINE and church is not None and not held(church):
        stand = stand_from(table.stance_threshold, await judge_values(ctx, hearing.row, await values_for(ctx.session, church)), table.church_weight)
        if stand is not None:
            hearing.stands[church] = stand


async def faction_reading(ctx: TickContext, hearing: Hearing, faction_id: int) -> int:
    goals = list(await ctx.session.scalars(select(FactionGoalRow).where(FactionGoalRow.faction_entity_id == faction_id)))
    if any(goal.kind is FactionGoalKind.ENACT_LAW and goal.target_key == hearing.row.kind.value for goal in goals):
        return PERCENT
    if hearing.row.law_entity_id is not None and any(
        goal.kind is FactionGoalKind.ABOLISH_LAW and goal.target_node_id == hearing.row.law_entity_id for goal in goals
    ):
        return -PERCENT
    return await judge_values(ctx, hearing.row, await values_for(ctx.session, faction_id))


async def estates_have_rights(ctx: TickContext, realm: Realm) -> bool:
    charter = await ctx.session.scalar(
        select(LawProfileRow.params)
        .join(EntityRow, EntityRow.id == LawProfileRow.law_entity_id)
        .where(LawProfileRow.kind == LawKind.CONSTITUTION, EntityRow.location_id == realm.entity.id, EntityRow.status == EntityStatus.CANON)
        .limit(1)
    )
    return charter is None or bool(charter.get("estates_rights", True))


@memoized(FactionProfileRow)
async def faction_profiles(session: AsyncSession) -> tuple[FactionProfileRow, ...]:
    return tuple(await session.scalars(select(FactionProfileRow).order_by(FactionProfileRow.faction_entity_id)))


async def hear_factions(ctx: TickContext, hearing: Hearing) -> None:
    table = ctx.rules.enactment
    key = str(hearing.realm.entity.id)
    seated = set(
        await ctx.session.scalars(
            select(EstatePrivilegeRow.estate_entity_id)
            .join(EstateProfileRow, EstateProfileRow.faction_entity_id == EstatePrivilegeRow.estate_entity_id)
            .where(EstateProfileRow.polity_entity_id == hearing.realm.entity.id, EstatePrivilegeRow.privilege == EstatePrivilege.COUNCIL_SEAT)
        )
    )
    for profile in await faction_profiles(ctx.session):
        sway = int((profile.influence_over or {}).get(key, 0))
        faction_id = profile.faction_entity_id
        if sway <= 0 or faction_id in hearing.stands or held(faction_id):
            continue
        weight = round_half_up(sway * table.faction_weight_pct / PERCENT)
        stand = stand_from(table.stance_threshold, await faction_reading(ctx, hearing, faction_id), weight)
        if stand is None:
            continue
        if stand.stance is ProposalStance.OPPOSE and faction_id in seated and await estates_have_rights(ctx, hearing.realm):
            stand = Stand(ProposalStance.OBSTRUCT, round_half_up(sway * table.estate_obstruct_pct / PERCENT))
        hearing.stands[faction_id] = stand


async def hear_seats(ctx: TickContext, hearing: Hearing) -> None:
    table = ctx.rules.enactment
    rows = list(await ctx.session.scalars(select(CouncilSeatRow).where(CouncilSeatRow.polity_entity_id == hearing.realm.entity.id)))
    total = sum(row.seats for row in rows)
    for row in rows:
        holder = row.holder_node_id
        if total <= 0 or row.seats <= 0 or held(holder):
            continue
        weight = round_half_up(table.council_weight * row.seats / total * ctx.rules.affairs.seat_weight_pct / PERCENT * len(rows))
        stand = stand_from(table.stance_threshold, await faction_reading(ctx, hearing, holder), weight)
        if stand is None:
            continue
        found = hearing.stands.get(holder)
        hearing.stands[holder] = Stand(
            stand.stance, clamp_int(weight + (found.weight if found is not None and found.stance is stand.stance else 0), 0, PERCENT)
        )


async def hear_champion(ctx: TickContext, hearing: Hearing) -> None:
    champion = hearing.row.champion_node_id
    if champion is not None and not held(champion):
        hearing.stands[champion] = Stand(ProposalStance.SUPPORT, ctx.rules.enactment.council_weight)


async def lean_on(ctx: TickContext, hearing: Hearing, tally: EnactmentTally) -> None:
    champion = hearing.row.champion_node_id
    ruler = hearing.realm.ruler_id
    if champion is not None and ruler is not None and champion != ruler and not held(ruler):
        stand = hearing.stands.get(ruler)
        hook = await hook_on(ctx, champion, ruler) if stand is None or stand.stance is not ProposalStance.SUPPORT else None
        if hook is not None and await use_hook(ctx, hook, HookDemand.LAW):
            hearing.stands[ruler] = Stand(ProposalStance.SUPPORT, ctx.rules.enactment.ruler_weight, hooked=True)
            tally.hooked += 1
    backers = [node for node, stand in hearing.stands.items() if stand.stance in FOR]
    foes = [node for node, stand in hearing.stands.items() if stand.stance in AGAINST]
    for node, stand in list(hearing.stands.items()):
        if held(node) or stand.hooked:
            continue
        side = backers if stand.stance in AGAINST else foes
        for leaner in side:
            hook = await hook_on(ctx, leaner, node)
            if hook is None or not await use_hook(ctx, hook, HookDemand.VOTE):
                continue
            turned = ProposalStance.SUPPORT if stand.stance in AGAINST else ProposalStance.OPPOSE
            hearing.stands[node] = Stand(turned, stand.weight, hooked=True)
            tally.hooked += 1
            break


async def record_stances(ctx: TickContext, hearing: Hearing) -> None:
    kept = {row.node_id: row for row in await ctx.session.scalars(select(ProposalStanceRow).where(ProposalStanceRow.proposal_id == hearing.row.id))}
    for node, row in kept.items():
        if row.locked or held(node):
            hearing.stands[node] = Stand(row.stance, row.weight, row.hooked)
        elif node not in hearing.stands:
            await ctx.session.delete(row)
    for node, stand in hearing.stands.items():
        found = kept.get(node)
        if found is None:
            ctx.session.add(
                ProposalStanceRow(
                    proposal_id=hearing.row.id, node_id=node, stance=stand.stance, weight=clamp_int(stand.weight, 0, PERCENT), hooked=stand.hooked
                )
            )
        elif not found.locked and not held(node):
            found.stance, found.weight, found.hooked = stand.stance, clamp_int(stand.weight, 0, PERCENT), stand.hooked
    await ctx.session.flush()


async def hear(ctx: TickContext, realm: Realm, row: LawProposalRow, tally: EnactmentTally) -> Hearing:
    hearing = Hearing(realm, row)
    await hear_champion(ctx, hearing)
    await hear_ruler(ctx, hearing)
    await hear_council(ctx, hearing)
    await hear_people(ctx, hearing)
    await hear_factions(ctx, hearing)
    await hear_seats(ctx, hearing)
    await lean_on(ctx, hearing, tally)
    await record_stances(ctx, hearing)
    return hearing


def soften(row: LawProposalRow) -> bool:
    defaults = defaults_for(row.kind)
    spec = LAW_PARAMS[row.kind]
    params = dict(row.params)
    for key, value in params.items():
        default = defaults.get(key)
        if value == default or isinstance(value, bool):
            continue
        if isinstance(value, int) and isinstance(default, int):
            params[key] = round_half_up((value + default) / 2)
        elif spec[key].choices and isinstance(default, str):
            params[key] = default
        else:
            continue
        row.params = params
        return True
    return False


async def stir(ctx: TickContext, hearing: Hearing, tally: EnactmentTally) -> None:
    table = ctx.rules.enactment
    row, realm = hearing.row, hearing.realm
    if not ctx.rng(f"enactment.event.{row.id}.{ctx.epoch}").chance(table.event_pct):
        return
    obstructed = any(stand.stance is ProposalStance.OBSTRUCT for stand in hearing.stands.values())
    capital = await ctx.session.get(SettlementProfileRow, realm.profile.capital_entity_id or -1)
    event: ProposalEvent | None = None
    text = ""
    if obstructed:
        event, text = ProposalEvent.OBSTRUCTION, f"The estates of {realm.entity.name} used their seats to stall {law_title(row.kind)}."
    elif row.support > row.opposition and realm.profile.decision_rule in {DecisionRule.ASSEMBLY, DecisionRule.COUNCIL}:
        if PROGRESS not in row.locked:
            row.progress = clamp_int(row.progress + table.debate_progress, 0, PERCENT)
        event, text = ProposalEvent.DEBATE, f"{realm.entity.name} gathered to debate {law_title(row.kind)}, and the speeches carried it on."
    elif row.opposition > row.support and capital is not None and "unrest" not in (capital.locked or []):
        capital.unrest = clamp_int(capital.unrest + table.riot_unrest, 0, PERCENT)
        event, text = ProposalEvent.RIOT, f"Crowds rioted in the streets of {realm.entity.name} against {law_title(row.kind)}."
    elif row.opposition > 0 and not row.amended and PARAMS not in row.locked and soften(row):
        row.amended = True
        event, text = ProposalEvent.COMPROMISE, f"The backers of {law_title(row.kind)} softened its terms to win over {realm.entity.name}."
    if event is None:
        return
    row.last_event = event
    await note(ctx, text, key=f"enactment.{event.value}", ids=[realm.entity.id], kind=ChronicleKind.CIVILIZATION)
    tally.events += 1


async def carry(ctx: TickContext, hearing: Hearing) -> EntityRow | None:
    row, realm = hearing.row, hearing.realm
    current = await ctx.session.get(LawProfileRow, row.law_entity_id) if row.law_entity_id is not None else None
    if current is not None:
        if "params" not in (current.locked or []):
            current.params = dict(row.params)
            current.enacted_by_entity_id = row.champion_node_id if row.champion_node_id is not None else current.enacted_by_entity_id
        return await ctx.session.get(EntityRow, current.law_entity_id)
    champion = row.champion_node_id if row.champion_node_id is not None else realm.ruler_id
    law = await enact(ctx, realm.entity, row.kind, row.params, by_id=champion, basis=row.basis)
    row.law_entity_id = law.id
    return law


async def reward(ctx: TickContext, hearing: Hearing) -> None:
    champion = hearing.row.champion_node_id
    if champion is None:
        return
    for node, stand in hearing.stands.items():
        if node != champion and stand.stance in FOR and not stand.hooked:
            await owe(ctx, champion, node, FavourOrigin.VOTE, ctx.rules.enactment.favour_magnitude)


async def fail(ctx: TickContext, hearing: Hearing) -> None:
    row, realm = hearing.row, hearing.realm
    row.state, row.resolved_epoch = ProposalState.FAILED, ctx.epoch
    champion = await living_entity(ctx.session, row.champion_node_id) if row.champion_node_id is not None else None
    cost = ctx.rules.enactment.champion_cost
    if champion is not None and not held(champion.id):
        if champion.entity_type is EntityType.MORTAL:
            await add_renown(ctx.session, champion.id, -cost, ctx.epoch, rules=ctx.rules)
        else:
            shift_stat(champion, "sway", -cost)
    who = f", and {champion.name} lost face" if champion is not None else ""
    await note(
        ctx,
        f"{law_title(row.kind).capitalize()} stalled in {realm.entity.name} and failed{who}.",
        key="enactment.failed",
        ids=[realm.entity.id, *([champion.id] if champion is not None else [])],
        kind=ChronicleKind.CIVILIZATION,
    )


async def advance(ctx: TickContext, realm: Realm, row: LawProposalRow, tally: EnactmentTally) -> None:
    table = ctx.rules.enactment
    champion = await ctx.session.get(EntityRow, row.champion_node_id) if row.champion_node_id is not None else None
    if champion is not None and champion.status is not EntityStatus.CANON and STATE not in row.locked:
        row.state, row.resolved_epoch = ProposalState.WITHDRAWN, ctx.epoch
        tally.withdrawn += 1
        return
    hearing = await hear(ctx, realm, row, tally)
    bonus = table.compromise_support if row.amended else 0
    if SUPPORT not in row.locked:
        row.support = clamp_int(sum(stand.weight for stand in hearing.stands.values() if stand.stance in FOR) + bonus, 0, PERCENT)
    if OPPOSITION not in row.locked:
        row.opposition = clamp_int(sum(stand.weight for stand in hearing.stands.values() if stand.stance in AGAINST), 0, PERCENT)
    pace = ctx.rules.affairs.constitution_pct if row.kind is LawKind.CONSTITUTION else PERCENT
    gain = round_half_up((row.support - row.opposition) * table.progress_pct / PERCENT * pace / PERCENT)
    if PROGRESS not in row.locked:
        row.progress = clamp_int(row.progress + max(0, gain), 0, PERCENT)
    row.stalled_epochs = 0 if gain > 0 else row.stalled_epochs + 1
    await stir(ctx, hearing, tally)
    if STATE in row.locked:
        return
    if row.progress >= DONE:
        law = await carry(ctx, hearing)
        row.state, row.resolved_epoch = ProposalState.PASSED, ctx.epoch
        await reward(ctx, hearing)
        await note(
            ctx,
            f"{realm.entity.name} passed {law.name if law is not None else law_title(row.kind)}.",
            key="polity.law_enacted",
            ids=[realm.entity.id, *([law.id] if law is not None else [])],
            kind=ChronicleKind.CIVILIZATION,
        )
        tally.passed += 1
    elif row.stalled_epochs >= table.stall_epochs:
        await fail(ctx, hearing)
        tally.failed += 1


async def tend_proposals(ctx: TickContext, tally: EnactmentTally) -> None:
    book = await RealmBook.load(ctx.session)
    for row in list(await ctx.session.scalars(select(LawProposalRow).where(LawProposalRow.state == ProposalState.DEBATING).order_by(LawProposalRow.id))):
        realm = book.realms.get(row.polity_entity_id)
        if realm is None or held(row.polity_entity_id) or (row.champion_node_id is not None and held(row.champion_node_id)):
            continue
        await advance(ctx, realm, row, tally)


async def pass_now(ctx: TickContext, row: LawProposalRow) -> EntityRow | None:
    book = await RealmBook.load(ctx.session)
    realm = book.realms.get(row.polity_entity_id)
    if realm is None:
        return None
    stands = {
        stance.node_id: Stand(stance.stance, stance.weight, stance.hooked)
        for stance in await ctx.session.scalars(select(ProposalStanceRow).where(ProposalStanceRow.proposal_id == row.id))
    }
    hearing = Hearing(realm, row, stands)
    law = await carry(ctx, hearing)
    row.progress, row.state, row.resolved_epoch = DONE, ProposalState.PASSED, ctx.epoch
    await reward(ctx, hearing)
    return law


async def pledge(ctx: TickContext, holder_id: int, target_id: int, *, weight: int) -> int:
    pledged = 0
    for row in await ctx.session.scalars(select(LawProposalRow).where(LawProposalRow.state == ProposalState.DEBATING).order_by(LawProposalRow.id)):
        mine = await ctx.session.get(ProposalStanceRow, (row.id, holder_id))
        side = ProposalStance.SUPPORT if row.champion_node_id == holder_id or (mine is not None and mine.stance in FOR) else None
        side = side or (ProposalStance.OPPOSE if mine is not None and mine.stance in AGAINST else None)
        if side is None or held(target_id):
            continue
        theirs = await ctx.session.get(ProposalStanceRow, (row.id, target_id))
        if theirs is None:
            ctx.session.add(ProposalStanceRow(proposal_id=row.id, node_id=target_id, stance=side, weight=weight, hooked=True))
        elif not theirs.locked:
            theirs.stance, theirs.hooked = side, True
        pledged += 1
    await ctx.session.flush()
    return pledged


async def pledge_vote(ctx: TickContext, holder_id: int, target_id: int) -> int:
    return await pledge(ctx, holder_id, target_id, weight=ctx.rules.enactment.council_weight)


async def back_law(ctx: TickContext, holder_id: int, ruler_id: int) -> int:
    return await pledge(ctx, holder_id, ruler_id, weight=ctx.rules.enactment.ruler_weight)
