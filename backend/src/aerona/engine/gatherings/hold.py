from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.commodities import FOOD_KINDS
from aerona.catalog.gatherings import CONTEST_KINDS, GATHERING_COLLECTIONS, GATHERING_THOUGHTS, GUEST_ROLES, HONOURED_ROLES, HOST_ROLES, HOSTED_FEASTS
from aerona.catalog.kinds.gathering_outcomes import GATHERING_RESULTS
from aerona.catalog.life.gatherings import HOLD_GATHERING_KINDS
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.grammar import spoken
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.repositories.chronicle import scoped_cause
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import CommemorationRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.intrigue import SchemeRow, SecretRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import CrowdFeeling
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.gathering import AttendanceReason, CollectionRole, GatheringKind, GatheringOutcome, GatheringStatus, GuestRole
from aerona.domain.enums.intrigue import PlotKind, SchemePhase
from aerona.domain.enums.mind import ActKind, EthicalStance, MemoryKind, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind, TreatyKind
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepOutcome
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.moment import Moment, latest
from aerona.engine.body.hits import Harm
from aerona.engine.collective.feelings import stir_feelings
from aerona.engine.context import TickContext
from aerona.engine.customs.time_budgets import leisure_odds
from aerona.engine.economy.purse import take_coin
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.faith.book import patron_node
from aerona.engine.folkways.purity import apart_at_table, unclean
from aerona.engine.gatherings.occasions import Guest, Occasion, household_of
from aerona.engine.happenings.profile import season_for, year_at
from aerona.engine.history.collections import open_collection
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.intrigue.schemes import SchemeTally, execute
from aerona.engine.intrigue.secrets import learn
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.taboos import kept
from aerona.engine.lore.traditions import cohere
from aerona.engine.military.units import stacks_of, take
from aerona.engine.mind.ethics import conscience, culture_of, ethics_of
from aerona.engine.mind.memories import remember as mind_remember
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kin import betrothed_of, spouses_of
from aerona.engine.mortal.kinship import betroth
from aerona.engine.mortal.life import adult
from aerona.engine.mortal.standing import add_honour, add_infamy, add_renown, add_stress, add_wealth
from aerona.engine.polity.treaties import sign_derived
from aerona.engine.powers.society import test_people
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_among, present_among
from aerona.engine.primitives.levies import demobilise
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, shift_stat, stat, stat_or
from aerona.engine.recording.births import born_floor
from aerona.engine.recording.moments import incident_moment, moment_for
from aerona.engine.recording.record import FactInput, StepDraft, kind_of, record
from aerona.engine.relations.book import ensure_relation, relation, relations_of, shift

G = GatheringKind
MINGLE_GROUP = 10
OUTCOME_ORDER = (GatheringOutcome.CONVIVIAL, GatheringOutcome.UNEVENTFUL, GatheringOutcome.QUARRELSOME, GatheringOutcome.VIOLENT, GatheringOutcome.MASSACRE)


@dataclass
class Holding:
    row: GatheringRow
    host: NodeRow
    attendees: list[int] = field(default_factory=list)
    guests: dict[int, GatheringGuestRow] = field(default_factory=dict)
    outcome: GatheringOutcome = GatheringOutcome.CONVIVIAL
    harmed: list[int] = field(default_factory=list)
    steps: list[StepDraft] = field(default_factory=list)
    facts: dict[str, FactInput] = field(default_factory=dict)

    def worsen(self, outcome: GatheringOutcome) -> None:
        if OUTCOME_ORDER.index(outcome) > OUTCOME_ORDER.index(self.outcome):
            self.outcome = outcome


@dataclass
class GatheringTally:
    planned: int = 0
    held: int = 0
    attended: int = 0
    romances: int = 0
    betrothals: int = 0
    secrets: int = 0
    strikes: int = 0
    massacres: int = 0
    treaties: int = 0


def rng(ctx: TickContext, row: GatheringRow, key: str) -> SeededRandom:
    return ctx.rng(f"gathering.{row.id}.{key}.{ctx.epoch}")


async def plan(ctx: TickContext, occasion: Occasion, *, by_player: bool = False) -> GatheringRow | None:
    if held(occasion.host_id):
        return None
    place = occasion.place_id if occasion.place_id is not None and not held(occasion.place_id) else None
    row = GatheringRow(
        host_node_id=occasion.host_id,
        kind=occasion.kind,
        status=GatheringStatus.PLANNED,
        milestone=occasion.milestone,
        place_entity_id=place,
        world_id=occasion.world_id,
        honoured_node_id=occasion.honoured_id,
        tradition_entity_id=occasion.tradition_id,
        epoch=ctx.epoch,
        by_player=by_player,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    floor = await rite_floor(ctx, row)
    row.year = max(0, year_at(ctx, ctx.epoch, f"gathering_year.{row.id}"), floor.year if floor is not None else 0)
    row.season = await season_of(ctx, row)
    await invite(ctx, row, occasion.guests)
    return row


async def death_moment_of(ctx: TickContext, node: int | None) -> Moment | None:
    found = await ctx.session.get(EntityRow, node) if node is not None else None
    if found is None or found.status is not EntityStatus.DEAD:
        return None
    year = stat(found, "death_year")
    return Moment(int(year)) if year is not None else None


async def rite_floor(ctx: TickContext, row: GatheringRow) -> Moment | None:
    births = await born_floor(ctx.session, [node for node in (row.host_node_id, row.honoured_node_id, row.place_entity_id) if node is not None])
    return latest(births, await death_moment_of(ctx, row.honoured_node_id))


async def season_of(ctx: TickContext, row: GatheringRow) -> int | None:
    profile = await ctx.session.get(TraditionProfileRow, row.tradition_entity_id) if row.tradition_entity_id is not None else None
    if profile is not None and profile.season_position is not None:
        return profile.season_position
    return await season_for(ctx, row.world_id, None, f"gathering_season.{row.id}")


async def candidates(ctx: TickContext, row: GatheringRow) -> list[Guest]:
    found: list[Guest] = []
    host = await ctx.session.get(EntityRow, row.host_node_id)
    if row.honoured_node_id is not None and row.honoured_node_id != row.host_node_id:
        role = HONOURED_ROLES.get(row.kind, GuestRole.HONOURED)
        found.append(Guest(row.honoured_node_id, role, AttendanceReason.KIN))
    if host is not None and host.entity_type is EntityType.MORTAL:
        found.extend(Guest(kin, GuestRole.GUEST, AttendanceReason.KIN) for kin in await household_of(ctx, host))
    friends = sorted(await relations_of(ctx.session, row.host_node_id), key=lambda tie: (-tie.friendship, tie.subject_node_id))
    found.extend(Guest(tie.subject_node_id, GuestRole.GUEST, AttendanceReason.FRIEND) for tie in friends if tie.friendship > 0)
    place = row.place_entity_id or (host.location_id if host is not None else None)
    homes = [home for home in (place, host.id if host is not None and host.entity_type is not EntityType.MORTAL else None) if home is not None]
    if homes:
        neighbours = await ctx.session.scalars(
            select(EntityRow.id)
            .where(await folk_among(ctx.session, homes), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
        found.extend(Guest(int(node), GuestRole.GUEST, AttendanceReason.NEIGHBOUR) for node in neighbours)
    patron = await patron_node(ctx.session, place) if place is not None else None
    if patron is not None:
        faithful = await ctx.session.scalars(
            select(BondRow.source_node_id)
            .join(EntityRow, EntityRow.id == BondRow.source_node_id)
            .where(BondRow.target_node_id == patron, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, EntityRow.world_id == row.world_id)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
            .order_by(BondRow.source_node_id)
        )
        found.extend(Guest(int(node), GuestRole.GUEST, AttendanceReason.FAITH) for node in faithful)
    return found


async def invite(ctx: TickContext, row: GatheringRow, chosen: list[Guest]) -> int:
    limit = ctx.rules.gatherings.guests_max
    invited = set(await ctx.session.scalars(select(GatheringGuestRow.node_id).where(GatheringGuestRow.gathering_id == row.id)))
    present = {*invited, row.host_node_id}
    if row.host_node_id not in invited:
        ctx.session.add(GatheringGuestRow(gathering_id=row.id, node_id=row.host_node_id, role=GuestRole.HOST, reason=AttendanceReason.HOST, attended=None))
    added = 0
    for guest in [*chosen, *await candidates(ctx, row)]:
        if added >= limit:
            break
        if guest.node_id in present or held(guest.node_id) or await ctx.session.get(NodeRow, guest.node_id) is None:
            continue
        ctx.session.add(GatheringGuestRow(gathering_id=row.id, node_id=guest.node_id, role=guest.role, reason=guest.reason, attended=None))
        present.add(guest.node_id)
        added += 1
    await ctx.session.flush()
    return added


async def attend(ctx: TickContext, holding: Holding, atlas: RegionAtlas) -> None:
    table = ctx.rules.gatherings
    row = holding.row
    place = row.place_entity_id or row.host_node_id
    for guest in await ctx.session.scalars(select(GatheringGuestRow).where(GatheringGuestRow.gathering_id == row.id).order_by(GatheringGuestRow.node_id)):
        holding.guests[guest.node_id] = guest
        if guest.locked and guest.attended is not None:
            if guest.attended:
                holding.attendees.append(guest.node_id)
            continue
        node = await ctx.session.get(EntityRow, guest.node_id)
        if (
            guest.role is GuestRole.HOST
            or guest.reason is AttendanceReason.SUMMONED
            or (node is None and await ctx.session.get(NodeRow, guest.node_id) is not None)
        ):
            guest.attended = node is None or node.status is EntityStatus.CANON or guest.role is GuestRole.MOURNED
            if guest.attended:
                holding.attendees.append(guest.node_id)
            continue
        if node is None or node.status is not EntityStatus.CANON:
            guest.attended = node is not None and guest.role is GuestRole.MOURNED
            if guest.attended:
                holding.attendees.append(guest.node_id)
            continue
        if await unclean(ctx.session, guest.node_id) or (row.kind in HOSTED_FEASTS and await apart_at_table(ctx.session, guest.node_id, row.host_node_id)):
            guest.attended = False
            continue
        tie = await relation(ctx.session, guest.node_id, row.host_node_id)
        odds = table.attend_base_pct + (tie.friendship * table.attend_friendship_pct / PERCENT if tie is not None else 0)
        if guest.reason in (AttendanceReason.KIN, AttendanceReason.OBLIGATION) or guest.role is not GuestRole.GUEST:
            odds += table.attend_obligation_pct
        odds -= atlas.distance(guest.node_id, place) * table.attend_hop_pct if node.location_id is not None else 0
        odds += await leisure_odds(ctx.session, ctx.rules, node)
        guest.attended = rng(ctx, row, f"attend.{guest.node_id}").chance(clamp_int(odds, 0, PERCENT))
        if guest.attended:
            holding.attendees.append(guest.node_id)


async def unwed(ctx: TickContext, node_id: int) -> bool:
    mortal = await ctx.session.get(EntityRow, node_id)
    profile = await ctx.session.get(MortalProfileRow, node_id)
    if mortal is None or profile is None or mortal.status is not EntityStatus.CANON or not adult(profile.life_stage):
        return False
    return not await spouses_of(ctx.session, node_id) and not await betrothed_of(ctx.session, node_id)


async def mingle(ctx: TickContext, holding: Holding, tally: GatheringTally) -> None:
    table = ctx.rules.gatherings
    row = holding.row
    mortals = [node for node in holding.attendees if (found := await ctx.session.get(EntityRow, node)) is not None and found.entity_type is EntityType.MORTAL]
    if len(mortals) < 2:
        return
    draw = rng(ctx, row, "mingle")
    kept_count: dict[int, SecretRow] = {}
    for unexposed in await ctx.session.scalars(
        select(SecretRow).where(SecretRow.holder_node_id.in_(mortals), SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.id)
    ):
        kept_count.setdefault(unexposed.holder_node_id, unexposed)
    for index in range(max(1, round(table.mingle_pairs * len(mortals) / MINGLE_GROUP))):
        first = draw.pick(mortals)
        second = draw.pick([node for node in mortals if node != first])
        there = await ensure_relation(ctx.session, first, second, ctx.epoch)
        back = await ensure_relation(ctx.session, second, first, ctx.epoch)
        if there is None or back is None:
            continue
        if there.rivalry >= table.quarrel_rivalry:
            shift(ctx.rules, there, ctx.epoch, rivalry=table.quarrel_shift)
            shift(ctx.rules, back, ctx.epoch, rivalry=table.quarrel_shift)
            holding.worsen(GatheringOutcome.QUARRELSOME)
            holding.steps.append(StepDraft(StepAction.QUARREL, actor=first, target=second))
            continue
        for tie in (there, back):
            shift(ctx.rules, tie, ctx.epoch, friendship=table.mingle_friendship, familiarity=table.mingle_familiarity)
        if await unwed(ctx, first) and await unwed(ctx, second) and rng(ctx, row, f"romance.{index}").chance(table.romance_pct):
            for tie in (there, back):
                shift(ctx.rules, tie, ctx.epoch, romance=table.romance_gain)
            tally.romances += 1
            if min(there.romance, back.romance) >= table.betrothal_romance:
                one, other = await ctx.session.get(EntityRow, first), await ctx.session.get(EntityRow, second)
                if one is not None and other is not None and await betroth(ctx.session, one, other, ctx.epoch, description="met at a gathering"):
                    tally.betrothals += 1
                    holding.steps.append(StepDraft(StepAction.COURT, actor=one.id, target=other.id, outcome=StepOutcome.ACCEPTED))
                    await record(
                        ctx,
                        "kin.betrothal",
                        roles={IncidentRole.SPOUSE: [one.id, other.id], IncidentRole.HOST: row.host_node_id},
                        facts={"romance": min(there.romance, back.romance)},
                        steps=(
                            StepDraft(StepAction.MEET, actor=one.id, target=other.id),
                            StepDraft(StepAction.COURT, actor=one.id, target=other.id, outcome=StepOutcome.ACCEPTED),
                        ),
                        place=row.place_entity_id,
                    )
        secret = kept_count.get(second)
        if secret is not None and rng(ctx, row, f"secret.{index}").chance(table.secret_pct) and await learn(ctx, secret, first):
            tally.secrets += 1
    await plots(ctx, holding)


async def plots(ctx: TickContext, holding: Holding) -> None:
    present = set(holding.attendees)
    progress = ctx.rules.gatherings.scheme_progress
    for scheme in await ctx.session.scalars(
        select(SchemeRow).where(SchemeRow.owner_node_id.in_(sorted(present)), SchemeRow.phase.in_([SchemePhase.RECRUIT, SchemePhase.PREPARE]))
    ):
        if present & set(scheme.agents) and "progress" not in (scheme.locked or []):
            scheme.progress = clamp_int(scheme.progress + progress, 0, PERCENT)


async def strike_at(ctx: TickContext, holding: Holding, tally: GatheringTally) -> None:
    present = set(holding.attendees)
    boost = 1 + ctx.rules.gatherings.strike_boost_pct / PERCENT
    for scheme in await ctx.session.scalars(
        select(SchemeRow).where(SchemeRow.kind == PlotKind.MURDER, SchemeRow.phase == SchemePhase.EXECUTE, SchemeRow.target_node_id.in_(sorted(present)))
    ):
        if held(scheme.owner_node_id) or not ({scheme.owner_node_id, *scheme.agents} & present):
            continue
        owner = await ctx.session.get(EntityRow, scheme.owner_node_id)
        target = await ctx.session.get(EntityRow, scheme.target_node_id) if scheme.target_node_id is not None else None
        if owner is None or target is None:
            continue
        await execute(ctx, scheme, owner, target, boost=boost, tally=SchemeTally())
        tally.strikes += 1
        if scheme.phase is SchemePhase.SUCCEEDED:
            holding.harmed.append(target.id)
            holding.worsen(GatheringOutcome.VIOLENT)


async def massacre_chance(ctx: TickContext, host: EntityRow) -> float:
    table = ctx.rules.gatherings
    if await kept(ctx.session, host.location_id, TraditionFunction.HOSPITALITY):
        return 0.0
    culture = await culture_of(ctx.session, host.id)
    ethic = (await ethics_of(ctx.session, culture.id)).get(ActKind.GUEST_KILLING) if culture is not None else None
    if ethic is not None and ethic.stance is EthicalStance.UNTHINKABLE:
        return 0.0
    shame = table.massacre_shameful_pct / PERCENT if ethic is not None and ethic.stance is EthicalStance.SHAMEFUL else 1.0
    return table.massacre_pct * shame


async def massacre(ctx: TickContext, holding: Holding, tally: GatheringTally) -> None:
    table = ctx.rules.gatherings
    host = await ctx.session.get(EntityRow, holding.row.host_node_id)
    if host is None or host.entity_type is not EntityType.MORTAL or not rng(ctx, holding.row, "massacre").chance(await massacre_chance(ctx, host)):
        return
    hated: list[EntityRow] = []
    for node in holding.attendees:
        tie = await relation(ctx.session, host.id, node)
        guest = await ctx.session.get(EntityRow, node)
        if tie is not None and tie.rivalry >= table.massacre_rivalry and guest is not None and guest.entity_type is EntityType.MORTAL and not held(node):
            hated.append(guest)
    if not hated:
        return
    for guest in hated:
        await apply_hits(ctx, guest, Harm(table.massacre_hp, HarmCause.BATTLE, f"was cut down at {host.name}'s {spoken(holding.row.kind)}", killer_id=host.id))
        holding.harmed.append(guest.id)
    await add_infamy(ctx.session, host.id, table.massacre_hp, ctx.epoch, rules=ctx.rules)
    await conscience(ctx, host.id, ActKind.GUEST_KILLING, hated[0].id)
    holding.worsen(GatheringOutcome.MASSACRE)
    tally.massacres += 1
    struck = [
        StepDraft(StepAction.STRIKE, actor=host.id, target=guest.id, amount=table.massacre_hp, unit=FactUnit.HP, outcome=StepOutcome.WOUNDED) for guest in hated
    ]
    holding.steps.extend(struck)
    await record(
        ctx,
        "gathering.massacre",
        roles={IncidentRole.HOST: host.id, IncidentRole.VICTIM: [guest.id for guest in hated]},
        facts={"gathering": holding.row.kind, "harm": table.massacre_hp, "infamy": table.massacre_hp},
        steps=tuple(struck),
        place=holding.row.place_entity_id,
    )


async def bouts(ctx: TickContext, holding: Holding, *, harmful: bool) -> int | None:
    table = ctx.rules.gatherings
    fighters = [
        found
        for node in holding.attendees
        if holding.guests.get(node) is not None
        and holding.guests[node].role is GuestRole.CONTESTANT
        and (found := await ctx.session.get(EntityRow, node)) is not None
        and found.status is EntityStatus.CANON
    ]
    draw = rng(ctx, holding.row, "bouts")
    while len(fighters) > 1:
        first, second = fighters.pop(0), fighters.pop(0)
        winner, loser = (
            (first, second) if stat_or(first, "strength", 0) + draw.die(PERCENT) >= stat_or(second, "strength", 0) + draw.die(PERCENT) else (second, first)
        )
        holding.steps.append(StepDraft(StepAction.COMPETE, actor=winner.id, target=loser.id, outcome=StepOutcome.SUCCESS))
        await think(ctx.session, ctx.rules, winner.id, ThoughtKind.WON_DUEL, ctx.epoch, subject_id=loser.id)
        await think(ctx.session, ctx.rules, loser.id, ThoughtKind.LOST_DUEL, ctx.epoch, subject_id=winner.id)
        if harmful and not held(loser.id):
            await apply_hits(ctx, loser, Harm(table.bout_hp, HarmCause.DUEL, f"fell in the lists before {winner.name}", source_node_id=winner.id), lethal=False)
            holding.harmed.append(loser.id)
            holding.steps.append(
                StepDraft(StepAction.STRIKE, actor=winner.id, target=loser.id, amount=table.bout_hp, unit=FactUnit.HP, outcome=StepOutcome.WOUNDED)
            )
        fighters.append(winner)
    if not fighters:
        return None
    champion = fighters[0]
    await add_renown(ctx.session, champion.id, table.bout_renown, ctx.epoch, rules=ctx.rules)
    holding.steps.append(StepDraft(StepAction.WIN, actor=champion.id, amount=table.bout_renown, unit=FactUnit.RENOWN))
    holding.facts["winner"] = champion.id
    return champion.id


async def realm_ruled_by(ctx: TickContext, ruler_id: int) -> PolityProfileRow | None:
    polity = await ctx.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == ruler_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return await ctx.session.get(PolityProfileRow, polity) if polity is not None else None


OUTCOMES: Handlers[GatheringKind, Callable[[TickContext, Holding], Awaitable[None]]] = Handlers(GatheringKind)


@OUTCOMES.on(GatheringKind.TOURNAMENT)
@OUTCOMES.on(GatheringKind.GAMES)
async def contest(ctx: TickContext, holding: Holding) -> None:
    await bouts(ctx, holding, harmful=holding.row.kind is G.TOURNAMENT)


@OUTCOMES.on(GatheringKind.HUNT)
async def hunt(ctx: TickContext, holding: Holding) -> None:
    table = ctx.rules.gatherings
    host = await ctx.session.get(EntityRow, holding.row.host_node_id)
    if host is None or not rng(ctx, holding.row, "beast").chance(table.hunt_beast_pct):
        return
    beast = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.BEAST, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == host.world_id)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if beast is None:
        return
    if stat_or(host, "strength", 0) + rng(ctx, holding.row, "beast.fight").die(PERCENT) < stat_or(beast, "strength", 0) + rng(
        ctx, holding.row, "beast.turn"
    ).die(PERCENT):
        await apply_hits(ctx, host, Harm(table.hunt_hp, HarmCause.MONSTER, f"was gored by {beast.name} on the hunt", source_node_id=beast.id), lethal=False)
        holding.harmed.append(host.id)
        holding.worsen(GatheringOutcome.VIOLENT)
        holding.facts["beast"] = beast.id
        holding.steps.append(
            StepDraft(
                StepAction.MEET_DANGER,
                actor=host.id,
                target=beast.id,
                instrument_kind=InstrumentKind.CREATURE,
                instrument_node=beast.id,
                amount=table.hunt_hp,
                unit=FactUnit.HP,
                outcome=StepOutcome.WOUNDED,
            )
        )
        return
    await add_renown(ctx.session, host.id, table.hunt_renown, ctx.epoch, rules=ctx.rules)
    holding.facts["beast"] = beast.id
    holding.steps.append(StepDraft(StepAction.MEET_DANGER, actor=host.id, target=beast.id, outcome=StepOutcome.SUCCESS))


@OUTCOMES.on(GatheringKind.CORONATION)
async def coronation(ctx: TickContext, holding: Holding) -> None:
    profile = await realm_ruled_by(ctx, holding.row.host_node_id)
    if profile is not None and "legitimacy" not in (profile.locked or []) and not held(profile.polity_entity_id):
        profile.legitimacy = clamp_int(profile.legitimacy + ctx.rules.gatherings.coronation_legitimacy, 0, PERCENT)


@OUTCOMES.on(GatheringKind.SUMMIT)
async def summit(ctx: TickContext, holding: Holding) -> None:
    table = ctx.rules.gatherings
    realms = [profile for node in holding.attendees if (profile := await realm_ruled_by(ctx, node)) is not None]
    signed = 0
    for index, first in enumerate(realms):
        for second in realms[index + 1 :]:
            tie = await ensure_relation(ctx.session, first.polity_entity_id, second.polity_entity_id, ctx.epoch)
            back = await ensure_relation(ctx.session, second.polity_entity_id, first.polity_entity_id, ctx.epoch)
            if tie is None or back is None:
                continue
            shift(ctx.rules, tie, ctx.epoch, friendship=table.summit_friendship)
            shift(ctx.rules, back, ctx.epoch, friendship=table.summit_friendship)
            if min(tie.friendship, back.friendship) >= table.summit_treaty_friendship:
                treaty = await sign_derived(
                    ctx, TreatyKind.NON_AGGRESSION, first.polity_entity_id, second.polity_entity_id, until=ctx.epoch + table.summit_treaty_epochs
                )
                signed += treaty is not None
    holding.row.prestige = clamp_int(holding.row.prestige + signed * table.feast_prestige, 0, PERCENT)
    holding.facts["treaties"] = signed
    if signed:
        holding.steps.append(StepDraft(StepAction.SIGN, amount=signed, unit=FactUnit.COUNT))


@OUTCOMES.on(GatheringKind.FESTIVAL)
async def festival(ctx: TickContext, holding: Holding) -> None:
    community = await ctx.session.get(EntityRow, holding.row.host_node_id)
    if community is not None:
        await cohere(ctx, community, ctx.rules.gatherings.festival_cohesion)


@OUTCOMES.on(GatheringKind.FAIR)
async def fair(ctx: TickContext, holding: Holding) -> None:
    merchants = await ctx.session.scalars(
        select(EntityRow.id).where(
            await present_among(ctx.session, [holding.row.host_node_id]), EntityRow.mortal_role == MortalRole.MERCHANT, EntityRow.status == EntityStatus.CANON
        )
    )
    for merchant in merchants:
        if not held(merchant):
            await add_wealth(ctx.session, int(merchant), ctx.rules.gatherings.fair_wealth, ctx.epoch)


@OUTCOMES.on(GatheringKind.COMMEMORATION)
async def commemoration(ctx: TickContext, holding: Holding) -> None:
    host = holding.row.host_node_id
    proud = False
    for row in await ctx.session.scalars(select(CommemorationRow).where(CommemorationRow.holder_entity_id == host).order_by(CommemorationRow.collection_id)):
        proud = proud or row.pride
        if "last_observed_epoch" not in row.locked:
            row.last_observed_epoch = ctx.epoch
    town = holding.row.place_entity_id or host
    if await ctx.session.get(SettlementProfileRow, town) is not None and not held(town):
        feeling = CrowdFeeling.FERVOUR if proud else CrowdFeeling.GRIEF
        await stir_feelings(ctx, town, {feeling: ctx.rules.gatherings.commemoration_feeling})
        holding.facts["feeling"] = feeling


@OUTCOMES.on(GatheringKind.MUSTER)
async def muster_held(ctx: TickContext, holding: Holding) -> None:
    host = await ctx.session.get(EntityRow, holding.row.host_node_id)
    armies = await ctx.session.scalars(
        select(ArmyRow).where(ArmyRow.owner_entity_id == holding.row.host_node_id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)
    )
    fled = 0
    for row in list(armies):
        army = await ctx.session.get(EntityRow, row.entity_id)
        if army is None or held(army.id):
            continue
        stacks = await stacks_of(ctx.session, army.id)
        leaving = sum(stack.count for stack in stacks) * ctx.rules.gatherings.muster_desertion_pct // PERCENT
        gone = take(stacks, leaving)
        if gone <= 0:
            continue
        with flowing(FlowCategory.LEVY):
            returned = demobilise(ctx.rules, host, gone)
            set_stats(army, size=max(0, (stat(army, "size") or 0) - returned))
        fled += gone
    holding.facts["deserted"] = fled
    if fled:
        holding.steps.append(StepDraft(StepAction.FLEE, amount=fled, unit=FactUnit.PEOPLE))


@OUTCOMES.on(GatheringKind.PERFORMANCE)
async def performance(ctx: TickContext, holding: Holding) -> None:
    for node in holding.attendees:
        guest = holding.guests.get(node)
        if guest is not None and guest.role is GuestRole.PERFORMER and not held(node):
            await add_renown(ctx.session, node, ctx.rules.gatherings.performer_renown, ctx.epoch, rules=ctx.rules)
            holding.steps.append(
                StepDraft(StepAction.PERFORM, actor=node, target=holding.row.host_node_id, amount=ctx.rules.gatherings.performer_renown, unit=FactUnit.RENOWN)
            )


@OUTCOMES.on(GatheringKind.PILGRIMAGE)
async def pilgrimage(ctx: TickContext, holding: Holding) -> None:
    profile = await ctx.session.get(PlaceProfileRow, holding.row.place_entity_id or holding.row.host_node_id)
    if profile is not None and "sacredness" not in profile.locked and not held(profile.entity_id):
        profile.sacredness = clamp_int(profile.sacredness + ctx.rules.gatherings.pilgrim_sacredness, 0, PERCENT)


@OUTCOMES.on(GatheringKind.PROCESSION)
async def procession(ctx: TickContext, holding: Holding) -> None:
    cult = await ctx.session.get(EntityRow, holding.row.host_node_id)
    if cult is not None and cult.entity_type is EntityType.CULT:
        shift_stat(cult, "zeal", ctx.rules.gatherings.procession_zeal_gain, 0, high=PERCENT)


@OUTCOMES.on(GatheringKind.COUNCIL)
async def council(ctx: TickContext, holding: Holding) -> None:
    for node in holding.attendees:
        if node != holding.row.host_node_id:
            tie = await ensure_relation(ctx.session, node, holding.row.host_node_id, ctx.epoch)
            if tie is not None:
                shift(ctx.rules, tie, ctx.epoch, friendship=ctx.rules.gatherings.council_loyalty)


@OUTCOMES.on(GatheringKind.EXECUTION)
async def execution(ctx: TickContext, holding: Holding) -> None:
    for node in holding.attendees:
        found = await ctx.session.get(EntityRow, node)
        if found is not None and found.entity_type is EntityType.MORTAL and not held(node):
            await add_stress(ctx.session, node, ctx.rules.gatherings.execution_stress, ctx.epoch)


@OUTCOMES.on(GatheringKind.ELECTION)
async def election(ctx: TickContext, holding: Holding) -> None:
    profile = await realm_ruled_by(ctx, holding.row.host_node_id)
    if profile is not None and "legitimacy" not in (profile.locked or []) and not held(profile.polity_entity_id):
        profile.legitimacy = clamp_int(profile.legitimacy + ctx.rules.gatherings.election_legitimacy, 0, PERCENT)


async def unrest_of(ctx: TickContext, town_id: int, amount: int) -> None:
    profile = await ctx.session.get(SettlementProfileRow, town_id)
    if profile is not None and "unrest" not in profile.locked and not held(town_id):
        profile.unrest = clamp_int(profile.unrest + amount, 0, PERCENT)


@OUTCOMES.on(GatheringKind.RALLY)
async def rally(ctx: TickContext, holding: Holding) -> None:
    await unrest_of(ctx, holding.row.host_node_id, ctx.rules.gatherings.rally_unrest_gain)


@OUTCOMES.on(GatheringKind.STRIKE)
async def strike(ctx: TickContext, holding: Holding) -> None:
    table = ctx.rules.gatherings
    town = await ctx.session.get(EntityRow, holding.row.host_node_id)
    society = await ctx.session.get(CommunitySocietyRow, holding.row.host_node_id)
    if town is None or held(town.id):
        return
    shift_stat(town, "prosperity", -table.strike_prosperity_loss, 0, high=PERCENT)
    if society is not None:
        society.satisfaction_worker = clamp_int(society.satisfaction_worker + table.strike_satisfaction_gain, 0, PERCENT)


@OUTCOMES.on(GatheringKind.CONVENTION)
async def convention(ctx: TickContext, holding: Holding) -> None:
    for node in holding.attendees:
        found = await ctx.session.get(EntityRow, node)
        if found is not None and found.social_class is SocialClass.PROFESSIONAL and not held(node):
            await add_renown(ctx.session, node, ctx.rules.gatherings.convention_renown, ctx.epoch, rules=ctx.rules)


@OUTCOMES.on(GatheringKind.LAUNCH)
async def launch(ctx: TickContext, holding: Holding) -> None:
    town = await ctx.session.get(SettlementProfileRow, holding.row.host_node_id)
    if town is not None and "prestige" not in town.locked and not held(town.settlement_entity_id):
        town.prestige = clamp_int(town.prestige + ctx.rules.gatherings.launch_prestige, 0, PERCENT)


@OUTCOMES.on(GatheringKind.BROADCAST)
async def broadcast(ctx: TickContext, holding: Holding) -> None:
    community = await ctx.session.get(EntityRow, holding.row.host_node_id)
    if community is not None:
        await cohere(ctx, community, ctx.rules.gatherings.broadcast_cohesion)


@OUTCOMES.on(GatheringKind.TESTING)
async def testing(ctx: TickContext, holding: Holding) -> None:
    found = await test_people(ctx, holding.row.host_node_id)
    holding.facts["gifts_found"] = found
    holding.steps.append(StepDraft(StepAction.TEST, actor=holding.row.host_node_id, amount=found or None, unit=FactUnit.COUNT if found else None))


async def nothing(ctx: TickContext, holding: Holding) -> None:
    return


GUEST_INCIDENT_ROLES: Mapping[GuestRole, IncidentRole] = total(
    GuestRole,
    {
        GuestRole.HOST: IncidentRole.HOST,
        GuestRole.GUEST: IncidentRole.GUEST,
        GuestRole.HONOURED: IncidentRole.BENEFICIARY,
        GuestRole.CONTESTANT: IncidentRole.OPPONENT,
        GuestRole.PERFORMER: IncidentRole.MEMBER,
        GuestRole.ACCUSED: IncidentRole.ACCUSED,
        GuestRole.MOURNED: IncidentRole.SUBJECT,
        GuestRole.WEDDED: IncidentRole.SPOUSE,
        GuestRole.CROWNED: IncidentRole.SUCCESSOR,
        GuestRole.ENVOY: IncidentRole.ENVOY,
    },
)


async def host_the_feast(ctx: TickContext, holding: Holding) -> None:
    table = ctx.rules.gatherings
    row = holding.row
    guests = max(0, len(holding.attendees) - 1)
    host = await ctx.session.get(EntityRow, row.host_node_id)
    if row.kind in HOSTED_FEASTS and "cost" not in row.locked:
        cost = guests * table.feast_cost
        if host is not None and cost and await take_coin(ctx.session, ctx.rules, host, cost):
            row.cost = cost
    wanted = guests * table.feast_food if row.kind in HOSTED_FEASTS else 0
    if wanted and "food" not in row.locked:
        row.food = await serve(ctx, larder_of(host), wanted)
    holding.steps.append(StepDraft(StepAction.HOST, actor=row.host_node_id, amount=guests or None, unit=FactUnit.PEOPLE if guests else None))
    if row.food:
        holding.steps.append(StepDraft(StepAction.SERVE_FOOD, actor=row.host_node_id, amount=row.food, unit=FactUnit.COUNT))
    fed = min(1.0, row.food / wanted) if wanted else 1.0
    if "prestige" not in row.locked:
        row.prestige = clamp_int(row.prestige + round(guests * table.feast_prestige * fed), 0, PERCENT)
    invited = max(1, len(holding.guests) - 1)
    if host is not None and host.entity_type is EntityType.MORTAL and guests * 2 >= invited:
        await add_honour(ctx.session, host.id, table.host_honour, ctx.epoch)
    for node in holding.attendees:
        if node != row.host_node_id:
            tie = await ensure_relation(ctx.session, node, row.host_node_id, ctx.epoch)
            if tie is not None:
                shift(ctx.rules, tie, ctx.epoch, friendship=table.guest_opinion)


def larder_of(host: EntityRow | None) -> int | None:
    if host is None:
        return None
    return host.location_id if host.entity_type is EntityType.MORTAL else host.id


async def serve(ctx: TickContext, larder: int | None, wanted: int) -> int:
    if larder is None:
        return 0
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    served = 0
    for food in FOOD_KINDS:
        if served >= wanted:
            break
        served += await ledger.take_units(larder, food, wanted - served, GoodsFlow.CONSUMPTION)
    return served


async def remember(ctx: TickContext, holding: Holding) -> None:
    thought = GATHERING_THOUGHTS[holding.row.kind]
    for node in holding.attendees:
        if node in holding.harmed:
            await think(ctx.session, ctx.rules, node, ThoughtKind.WAS_WOUNDED, ctx.epoch, subject_id=holding.row.host_node_id)
            continue
        kind = GATHERING_RESULTS[holding.outcome].thought or thought
        await think(ctx.session, ctx.rules, node, kind, ctx.epoch, subject_id=holding.row.host_node_id, intensity=ctx.rules.gatherings.thought_intensity)
        if holding.row.milestone is not None and node != holding.row.host_node_id:
            await mind_remember(
                ctx.session,
                ctx.rules,
                holder_id=node,
                subject_id=holding.row.host_node_id,
                kind=MemoryKind.FORMATIVE,
                magnitude=ctx.rules.gatherings.milestone_memory,
                epoch=ctx.epoch,
                note=f"the {spoken(holding.row.milestone)} kept in epoch {ctx.epoch}",
            )


def collection_role(holding: Holding, node: int) -> CollectionRole:
    if node == holding.row.host_node_id:
        return HOST_ROLES.get(holding.row.kind, CollectionRole.HOST)
    guest = holding.guests.get(node)
    return GUEST_ROLES[guest.role] if guest is not None else CollectionRole.GUEST


async def chronicle(ctx: TickContext, holding: Holding) -> None:
    row = holding.row
    collection = await open_collection(
        ctx,
        GATHERING_COLLECTIONS[row.kind],
        world_id=row.world_id,
        members={node: collection_role(holding, node) for node in holding.attendees},
        places=[row.place_entity_id] if row.place_entity_id is not None else [],
        source_key=f"gathering.{row.id}",
    )
    if collection is not None and "collection_id" not in row.locked:
        row.collection_id = collection.id
    guests: dict[IncidentRole, list[int]] = {}
    for node in holding.attendees:
        if node == row.host_node_id:
            continue
        guest = holding.guests.get(node)
        guests.setdefault(GUEST_INCIDENT_ROLES[guest.role] if guest is not None else IncidentRole.GUEST, []).append(node)
    key = f"gathering.{row.kind.value}"
    floor = latest(Moment(row.year) if row.year is not None else None, await rite_floor(ctx, row), await incident_moment(ctx.session, scoped_cause()))
    moment = await moment_for(ctx, kind_of(key).clock, key=key, participants=[row.host_node_id, *holding.attendees], cause_moment=floor, world_id=row.world_id)
    if "year" not in row.locked:
        row.year = moment.year
    await record(
        ctx,
        key,
        roles={IncidentRole.HOST: row.host_node_id, IncidentRole.PLACE: row.place_entity_id if row.place_entity_id != row.host_node_id else None, **guests},
        facts={
            "gathering": row.kind,
            "outcome": holding.outcome,
            "guests": max(0, len(holding.attendees) - 1),
            "cost": row.cost,
            "food": row.food,
            "prestige": row.prestige,
            "milestone": row.milestone,
            **holding.facts,
        },
        steps=tuple(holding.steps),
        place=row.place_entity_id,
        world_id=row.world_id,
        at_moment=moment,
    )


async def hold(ctx: TickContext, row: GatheringRow, atlas: RegionAtlas, tally: GatheringTally) -> bool:
    host = await ctx.session.get(NodeRow, row.host_node_id)
    if host is None or row.status is not GatheringStatus.PLANNED or held(row.host_node_id):
        return False
    holding = Holding(row, host)
    await attend(ctx, holding, atlas)
    if len(holding.attendees) < (1 if row.kind in HOLD_GATHERING_KINDS else 2):
        if "status" not in row.locked:
            row.status = GatheringStatus.CANCELLED
        return False
    tally.held += 1
    tally.attended += len(holding.attendees)
    if row.kind in CONTEST_KINDS or row.kind in HOSTED_FEASTS or row.kind is G.COUNCIL:
        await host_the_feast(ctx, holding)
    await mingle(ctx, holding, tally)
    await strike_at(ctx, holding, tally)
    await massacre(ctx, holding, tally)
    await OUTCOMES.get(row.kind, nothing)(ctx, holding)
    if holding.outcome is GatheringOutcome.CONVIVIAL and len(holding.attendees) <= 2:
        holding.outcome = GatheringOutcome.UNEVENTFUL
    for node in holding.harmed:
        if node in holding.guests:
            holding.guests[node].harmed = True
    if "status" not in row.locked:
        row.status = GatheringStatus.DISRUPTED if GATHERING_RESULTS[holding.outcome].disrupts else GatheringStatus.HELD
    if "outcome" not in row.locked:
        row.outcome = holding.outcome
    await remember(ctx, holding)
    await chronicle(ctx, holding)
    return True


async def gather_all(ctx: TickContext, occasions: list[Occasion], atlas: RegionAtlas, tally: GatheringTally) -> None:
    for occasion in occasions:
        if await plan(ctx, occasion) is not None:
            tally.planned += 1
    due = await ctx.session.scalars(
        select(GatheringRow).where(GatheringRow.status == GatheringStatus.PLANNED, GatheringRow.epoch <= ctx.epoch).order_by(GatheringRow.id)
    )
    for row in list(due):
        await hold(ctx, row, atlas, tally)
