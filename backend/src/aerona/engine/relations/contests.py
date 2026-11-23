from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import CONTEST_STAKE_TRAITS, having
from aerona.catalog.mind import COMBAT_SKILLS
from aerona.catalog.relations import CONTESTS
from aerona.catalog.renown import CONTEST_RENOWN
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.errors import AeronaError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import PreferenceRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import ContestRow, GroupRankRow, RelationshipRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.life_traits import ContestStakeTrait
from aerona.domain.enums.mind import Attribute, PreferenceKind, SkillKind, ThoughtKind, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.relations import ContestEnd, ContestKind, ContestStake, GroupKind, RelationType
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.crafts.rights import win_right
from aerona.engine.ecology.beasts import mounted_power
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.art import commission_work
from aerona.engine.mind.book import best_skill, skill_level, stored_values
from aerona.engine.mind.split import attribute
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kin import partners_of
from aerona.engine.mortal.kinship import close_between
from aerona.engine.mortal.standing import add_infamy, add_renown
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import active_bonds, connect, living_entity
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.relations.book import ensure_relation, relation, shift
from aerona.engine.relations.interactions import alignment
from aerona.engine.relations.passions import strongest_against
from aerona.engine.renown.deeds import acclaim_deed
from aerona.engine.renown.lore import grant, holdings
from aerona.engine.services.war import release_captive

LEARNED_AT = 40
VALUE_SPAN = 100
NOTED = having(CONTEST_STAKE_TRAITS, ContestStakeTrait.NOTED)
LAND_TYPES = frozenset({EntityType.REGION, EntityType.SETTLEMENT})


@dataclass
class ContestTally:
    held: int = 0
    famous: int = 0
    by_stake: dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass(frozen=True)
class Bout:
    kind: ContestKind
    stake: ContestStake
    challenger: EntityRow
    defender: EntityRow
    judge_id: int | None = None
    stake_node_id: int | None = None
    place_id: int | None = None
    wager: int = 0


async def prowess(ctx: TickContext, mortal: EntityRow, kind: ContestKind) -> float:
    spec = CONTESTS[kind]
    skills = [await skill_level(ctx.session, mortal.id, skill) for skill in spec.skills]
    gifts = [await attribute(ctx.session, ctx.rules, mortal, which) for which in spec.attributes]
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    conviction = profile.conviction if profile is not None else PERCENT // 2
    if spec.races:
        lean = ctx.rules.contests.race_endurance_pct / PERCENT
        carried = (max(skills) * (1 - lean) + sum(gifts) / len(gifts) * lean) * await mounted_power(ctx, mortal.id)
        return carried * 2 + conviction / 5
    return sum(skills) / len(skills) + sum(gifts) / len(gifts) + conviction / 5


async def tilt(session: AsyncSession, judge_id: int | None, contestant: int) -> float:
    if judge_id is None or judge_id == contestant:
        return 0.0
    liking = await relation(session, judge_id, contestant)
    fit = alignment(await stored_values(session, ValueHolder.PERSONAL, judge_id), await stored_values(session, ValueHolder.PERSONAL, contestant))
    return (liking.friendship if liking is not None else 0) / VALUE_SPAN + fit


async def best_kind(ctx: TickContext, first: EntityRow, second: EntityRow) -> ContestKind:
    scores = {kind: await prowess(ctx, first, kind) + await prowess(ctx, second, kind) for kind in ContestKind}
    return max(scores, key=lambda kind: (scores[kind], kind.value))


async def judge_of(session: AsyncSession, place_id: int | None) -> int | None:
    if place_id is None:
        return None
    rulers = await active_bonds(session, [BondKind.RULES], targets=[place_id])
    return rulers[0].source_node_id if rulers else None


async def pass_wealth(session: AsyncSession, loser: int, winner: int, amount: int) -> None:
    lost, won = await session.get(MortalProfileRow, loser), await session.get(MortalProfileRow, winner)
    if lost is None or won is None or "wealth" in lost.locked or "wealth" in won.locked:
        return
    moved = min(lost.wealth, amount)
    lost.wealth -= moved
    won.wealth = min(PERCENT, won.wealth + moved)


STAKES: Handlers[ContestStake, Callable[[TickContext, Bout, EntityRow, EntityRow], Awaitable[None]]] = Handlers(ContestStake)


@STAKES.on(ContestStake.UNION)
async def win_union(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    if bout.stake_node_id is None:
        return
    view = await ensure_relation(ctx.session, bout.stake_node_id, winner.id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, romance=ctx.rules.contests.union_romance, familiarity=5)
    await think(ctx.session, ctx.rules, loser.id, ThoughtKind.HEARTBROKEN, ctx.epoch, subject_id=bout.stake_node_id)


@STAKES.on(ContestStake.WAGER)
async def win_wager(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    await pass_wealth(ctx.session, loser.id, winner.id, bout.wager or ctx.rules.contests.wager_wealth)


@STAKES.on(ContestStake.CAPTIVE)
async def win_freedom(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    if winner.id != bout.challenger.id:
        return
    row = await ctx.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == winner.id, CaptiveRow.status == CaptiveStatus.HELD).limit(1))
    if row is not None:
        await release_captive(ctx, row, CaptiveStatus.RELEASED)


@STAKES.on(ContestStake.OFFICE)
async def win_place(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    if bout.stake_node_id is None or winner.id != bout.challenger.id:
        return
    mine = await ctx.session.get(GroupRankRow, (bout.stake_node_id, winner.id))
    theirs = await ctx.session.get(GroupRankRow, (bout.stake_node_id, loser.id))
    if mine is not None and theirs is not None and "rank" not in mine.locked and "rank" not in theirs.locked and mine.rank > theirs.rank:
        mine.rank, theirs.rank = theirs.rank, mine.rank
        await think(ctx.session, ctx.rules, winner.id, ThoughtKind.ROSE_IN_STANDING, ctx.epoch, subject_id=bout.stake_node_id)


@STAKES.on(ContestStake.DIVINE_FAVOUR)
async def win_favour(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    god = await living_patron(ctx.session, winner)
    if god is None:
        return
    for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], targets=[god.id]):
        cult = await living_entity(ctx.session, bond.source_node_id)
        followers = stat(cult, "followers") if cult is not None and cult.entity_type is EntityType.CULT else None
        if cult is not None and followers is not None:
            set_stats(cult, followers=round(followers * (1 + ctx.rules.contests.favour_followers_pct / PERCENT)))


@STAKES.on(ContestStake.LAND)
async def win_land(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    holding = bout.stake_node_id
    if holding is None:
        owned = await active_bonds(ctx.session, [BondKind.OWNS, BondKind.RULES], sources=[loser.id])
        lands = [bond.target_node_id for bond in owned if await is_land(ctx, bond.target_node_id)]
        holding = lands[0] if lands else None
    if holding is None or held(holding):
        return
    moved = await close_between(ctx.session, loser.id, holding, (BondKind.OWNS, BondKind.RULES), epoch=ctx.epoch, reason="lost in a contest")
    if not moved:
        return
    await connect(ctx.session, winner.id, holding, BondKind.OWNS, ctx.epoch, description="won in a contest")
    await paid(ctx, bout, winner, loser, holding)


async def is_land(ctx: TickContext, node_id: int) -> bool:
    entity = await living_entity(ctx.session, node_id)
    return entity is not None and entity.entity_type in LAND_TYPES


@STAKES.on(ContestStake.FREEDOM)
async def win_own_freedom(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    row = await ctx.session.scalar(
        select(CaptiveRow).where(CaptiveRow.captive_entity_id == winner.id, CaptiveRow.status == CaptiveStatus.HELD).order_by(CaptiveRow.id).limit(1)
    )
    if row is None:
        return
    await release_captive(ctx, row, CaptiveStatus.RELEASED)
    await paid(ctx, bout, winner, loser, winner.id)


@STAKES.on(ContestStake.KNOWLEDGE)
async def win_knowledge(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    for kind in KnowledgeKind:
        mine = await holdings(ctx.session, winner.id, kind)
        for key, subject in sorted(await holdings(ctx.session, loser.id, kind) - mine, key=lambda item: (item[0], item[1] or 0)):
            if await grant(ctx, winner, (kind, key, subject)):
                await paid(ctx, bout, winner, loser, subject)
                return


async def paid(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow, stake_node_id: int | None) -> None:
    await record(
        ctx,
        "contest.stake_paid",
        roles={IncidentRole.ACTOR: winner.id, IncidentRole.OPPONENT: loser.id, IncidentRole.SUBJECT: stake_node_id},
        facts={"stake": bout.stake},
        place=bout.place_id or winner.location_id,
    )


@STAKES.on(ContestStake.HONOUR)
async def win_honour(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow) -> None:
    await add_renown(ctx.session, winner.id, ctx.rules.contests.renown / 2, ctx.epoch, rules=ctx.rules)
    await add_infamy(ctx.session, loser.id, ctx.rules.contests.infamy, ctx.epoch, rules=ctx.rules)


async def judge_taste(ctx: TickContext, bout: Bout) -> int:
    form = CONTESTS[bout.kind].work
    judge = bout.judge_id or bout.place_id
    if form is None or judge is None:
        return 0
    found = await ctx.session.scalar(
        select(PreferenceRow.strength).where(PreferenceRow.holder_node_id == judge, PreferenceRow.kind == PreferenceKind.ART_FORM, PreferenceRow.target == form)
    )
    return int(found or 0)


async def rounds_of(ctx: TickContext, bout: Bout) -> list[list[float]]:
    table = ctx.rules.contests
    rng = ctx.rng(seed_of("contest", bout.challenger.id, bout.defender.id, ctx.epoch, bout.kind.value))
    sides = (bout.challenger, bout.defender)
    base = [await prowess(ctx, side, bout.kind) for side in sides]
    drive = [
        1 + table.passion_pct / PERCENT * await strongest_against(ctx.session, side.id, other.id) / PERCENT
        for side, other in zip(sides, sides[::-1], strict=True)
    ]
    taste = await judge_taste(ctx, bout)
    merit = 1 + taste / (4 * PERCENT)
    lean = [await tilt(ctx.session, bout.judge_id, side.id) * table.judge_pct * (1 - taste / (2 * PERCENT)) for side in sides]
    found = []
    for _ in range(table.rounds):
        found.append([round(base[index] * drive[index] * merit + lean[index] + rng.integer(0, table.jitter), 1) for index in range(2)])
    return found


async def famed(ctx: TickContext, bout: Bout, winner: EntityRow, loser: EntityRow, margin: int) -> int | None:
    repository = EntityRepository(ctx.session)
    notable = all([is_notable(ctx.rules, side, await repository.flags(side.id)) for side in (winner, loser)])
    if not notable or margin < ctx.rules.contests.famous_margin:
        return None
    spec = CONTESTS[bout.kind]
    medium = ArtMode(spec.work) if spec.work is not None else ArtMode.VERBAL
    try:
        work = await commission_work(
            ctx,
            winner.id,
            name=f"The {spec.label} of {winner.name} and {loser.name}",
            medium=medium,
            author_id=winner.id,
            subject_id=loser.id,
            message=None,
            paid=False,
        )
    except AeronaError:
        return None
    return work.id


async def masterwork(ctx: TickContext, bout: Bout, winner: EntityRow) -> int | None:
    spec = CONTESTS[bout.kind]
    if not spec.crafted or not ctx.rng(seed_of("contest_masterwork", winner.id, ctx.epoch)).chance(ctx.rules.contests.craft_masterwork_pct):
        return None
    try:
        work = await commission_work(
            ctx,
            winner.id,
            name=f"The {spec.label} work of {winner.name}",
            medium=ArtMode.SOLID_IMAGE,
            author_id=winner.id,
            subject_id=None,
            message=None,
            paid=False,
        )
    except AeronaError:
        return None
    await think(ctx.session, ctx.rules, winner.id, ThoughtKind.MADE_MASTERWORK, ctx.epoch)
    return work.id


async def hold_contest(ctx: TickContext, bout: Bout, tally: ContestTally) -> ContestRow | None:
    if held(bout.challenger.id) or held(bout.defender.id) or bout.challenger.id == bout.defender.id:
        return None
    rounds = await rounds_of(ctx, bout)
    ahead = sum(1 for first, second in rounds if first > second) - sum(1 for first, second in rounds if second > first)
    outcome = ContestEnd.CHALLENGER if ahead > 0 else ContestEnd.DEFENDER if ahead < 0 else ContestEnd.DRAWN
    row = ContestRow(
        kind=bout.kind,
        stake=bout.stake,
        challenger_node_id=bout.challenger.id,
        defender_node_id=bout.defender.id,
        judge_node_id=bout.judge_id,
        stake_node_id=bout.stake_node_id,
        place_node_id=bout.place_id,
        wager=bout.wager,
        rounds=rounds,
        outcome=outcome,
        epoch=ctx.epoch,
    )
    ctx.session.add(row)
    tally.held += 1
    tally.by_stake[bout.stake.value] += 1
    if outcome is not ContestEnd.DRAWN:
        winner, loser = (bout.challenger, bout.defender) if outcome is ContestEnd.CHALLENGER else (bout.defender, bout.challenger)
        await settle(ctx, bout, row, winner, loser, margin=abs(ahead), tally=tally)
    await ctx.session.flush()
    return row


async def sport_harm(ctx: TickContext, bout: Bout, loser: EntityRow) -> None:
    rough = any(skill in COMBAT_SKILLS for skill in CONTESTS[bout.kind].skills) or Attribute.STRENGTH in CONTESTS[bout.kind].attributes
    if not rough or not ctx.rng(f"contest.harm.{loser.id}.{ctx.epoch}.{bout.kind.value}").chance(ctx.rules.harm.sport_harm_pct):
        return
    await apply_hits(ctx, loser, Harm(ctx.rules.harm.sport_hp, HarmCause.SPORT, "hurt in a contest", source_node_id=bout.challenger.id))


async def settle(ctx: TickContext, bout: Bout, row: ContestRow, winner: EntityRow, loser: EntityRow, *, margin: int, tally: ContestTally) -> None:
    table = ctx.rules.contests
    await add_renown(ctx.session, winner.id, table.renown, ctx.epoch, rules=ctx.rules)
    await add_infamy(ctx.session, loser.id, table.infamy, ctx.epoch, rules=ctx.rules)
    await think(ctx.session, ctx.rules, winner.id, ThoughtKind.WON_CONTEST, ctx.epoch, subject_id=loser.id)
    await think(ctx.session, ctx.rules, loser.id, ThoughtKind.LOST_CONTEST, ctx.epoch, subject_id=winner.id)
    sore = await ensure_relation(ctx.session, loser.id, winner.id, ctx.epoch)
    if sore is not None:
        shift(ctx.rules, sore, ctx.epoch, rivalry=table.renown, familiarity=3)
    await STAKES[bout.stake](ctx, bout, winner, loser)
    await sport_harm(ctx, bout, loser)
    await win_right(ctx, row.id, row.stake_node_id, winner.id, loser.id)
    axis, skill = CONTEST_RENOWN[bout.kind]
    await acclaim_deed(ctx, winner.id, axis, ctx.rules.local_renown.contest_magnitude, place_id=bout.place_id or winner.location_id, skill=skill)
    row.work_node_id = await famed(ctx, bout, winner, loser, margin) or await masterwork(ctx, bout, winner)
    row.famous = row.work_node_id is not None
    if row.famous:
        tally.famous += 1
    if not (row.famous or bout.stake in NOTED):
        await record(
            ctx,
            "contest.held",
            roles={IncidentRole.ACTOR: winner.id, IncidentRole.OPPONENT: loser.id},
            facts={"contest": bout.kind, "margin": margin},
            place=bout.place_id or winner.location_id,
        )
    if row.famous or bout.stake in NOTED:
        await record(
            ctx,
            "contest.famous" if row.famous else "contest.won",
            roles={IncidentRole.ACTOR: winner.id, IncidentRole.OPPONENT: loser.id, IncidentRole.PRODUCT: row.work_node_id},
            facts={"contest": bout.kind, "stake": bout.stake, "margin": margin},
            steps=contest_steps(row, winner, loser),
            place=bout.place_id or winner.location_id,
        )


def contest_steps(row: ContestRow, winner: EntityRow, loser: EntityRow) -> tuple[StepDraft, ...]:
    sides = (row.challenger_node_id, row.defender_node_id)
    scored = tuple(
        StepDraft(
            StepAction.SCORE,
            actor=side,
            target=sides[1 - index],
            round=number,
            parent=0,
            amount=float(scores[index]),
            unit=FactUnit.COUNT,
            outcome=StepOutcome.SUCCESS if scores[index] > scores[1 - index] else StepOutcome.FAILURE,
        )
        for number, scores in enumerate(row.rounds, start=1)
        for index, side in enumerate(sides)
    )
    return (
        StepDraft(StepAction.COMPETE, actor=winner.id, target=loser.id),
        *scored,
        StepDraft(StepAction.WIN, actor=winner.id, target=loser.id),
        StepDraft(StepAction.LOSE, actor=loser.id, target=winner.id),
    )


async def rival_bouts(ctx: TickContext, place_id: int, ids: list[int]) -> list[Bout]:
    rows = await ctx.session.scalars(
        select(RelationshipRow)
        .where(
            RelationshipRow.holder_node_id.in_(ids), RelationshipRow.subject_node_id.in_(ids), RelationshipRow.holder_node_id < RelationshipRow.subject_node_id
        )
        .order_by(RelationshipRow.id)
    )
    bouts = []
    for row in rows:
        if RelationType.RIVAL.value not in row.kinds:
            continue
        if not ctx.rng(seed_of("rival_contest", row.id, ctx.epoch)).chance(ctx.rules.contests.rival_pct):
            continue
        first, second = await living_entity(ctx.session, row.holder_node_id), await living_entity(ctx.session, row.subject_node_id)
        if first is None or second is None:
            continue
        rich = all(
            (profile.wealth if profile else 0) >= ctx.rules.contests.wager_wealth
            for profile in [await ctx.session.get(MortalProfileRow, side.id) for side in (first, second)]
        )
        stake = await stake_between(ctx, first, second, rich=rich)
        bouts.append(Bout(await best_kind(ctx, first, second), stake, first, second, judge_id=await judge_of(ctx.session, place_id), place_id=place_id))
    return bouts


async def landed(ctx: TickContext, mortal: EntityRow) -> bool:
    owned = await active_bonds(ctx.session, [BondKind.OWNS, BondKind.RULES], sources=[mortal.id])
    return any([await is_land(ctx, bond.target_node_id) for bond in owned])


async def stake_between(ctx: TickContext, first: EntityRow, second: EntityRow, *, rich: bool) -> ContestStake:
    if await landed(ctx, first) and await landed(ctx, second):
        return ContestStake.LAND
    learned = [await skill_level(ctx.session, side.id, SkillKind.LORE) >= LEARNED_AT for side in (first, second)]
    if all(learned):
        return ContestStake.KNOWLEDGE
    return ContestStake.WAGER if rich else ContestStake.HONOUR


async def suitor_bouts(ctx: TickContext, place_id: int, ids: list[int]) -> list[Bout]:
    suitors: dict[int, list[int]] = defaultdict(list)
    rows = await ctx.session.scalars(
        select(RelationshipRow).where(RelationshipRow.holder_node_id.in_(ids), RelationshipRow.subject_node_id.in_(ids)).order_by(RelationshipRow.id)
    )
    for row in rows:
        if RelationType.CRUSH.value in row.kinds or RelationType.LOVER.value in row.kinds:
            suitors[row.subject_node_id].append(row.holder_node_id)
    bouts = []
    for wooed, wooers in sorted(suitors.items()):
        if len(wooers) < 2 or await partners_of(ctx.session, wooed):
            continue
        if not ctx.rng(seed_of("suitors", wooed, ctx.epoch)).chance(ctx.rules.contests.suitor_pct):
            continue
        first, second = await living_entity(ctx.session, wooers[0]), await living_entity(ctx.session, wooers[1])
        if first is not None and second is not None:
            kind = await best_kind(ctx, first, second)
            bouts.append(Bout(kind, ContestStake.UNION, first, second, judge_id=wooed, stake_node_id=wooed, place_id=place_id))
    return bouts


async def captive_bouts(ctx: TickContext) -> list[Bout]:
    bouts = []
    for row in await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.status == CaptiveStatus.HELD).order_by(CaptiveRow.id)):
        captive = await living_entity(ctx.session, row.captive_entity_id)
        if captive is None or captive.entity_type is not EntityType.MORTAL:
            continue
        learned = await skill_level(ctx.session, captive.id, SkillKind.LORE) >= LEARNED_AT
        captor = await living_entity(ctx.session, row.captor_entity_id)
        keeper = (
            captor
            if captor is not None and captor.entity_type is EntityType.MORTAL
            else await living_entity(ctx.session, await judge_of(ctx.session, row.captor_entity_id))
        )
        if keeper is None or not ctx.rng(seed_of("riddle", row.id, ctx.epoch)).chance(ctx.rules.contests.captive_pct):
            continue
        kind, stake = (ContestKind.RIDDLE_GAME, ContestStake.CAPTIVE) if learned else (await best_kind(ctx, captive, keeper), ContestStake.FREEDOM)
        bouts.append(Bout(kind, stake, captive, keeper, judge_id=keeper.id, place_id=keeper.location_id))
    return bouts


async def court_bouts(ctx: TickContext) -> list[Bout]:
    bouts = []
    courts: dict[int, list[GroupRankRow]] = defaultdict(list)
    for row in await ctx.session.scalars(
        select(GroupRankRow).where(GroupRankRow.group_kind == GroupKind.COURT).order_by(GroupRankRow.group_node_id, GroupRankRow.rank)
    ):
        courts[row.group_node_id].append(row)
    for polity, rows in sorted(courts.items()):
        for upper, lower in pairwise(rows):
            if abs(upper.dominance - lower.dominance) > ctx.rules.pecking.challenge_margin:
                continue
            if not ctx.rng(seed_of("court_contest", polity, lower.member_node_id, ctx.epoch)).chance(ctx.rules.contests.court_pct):
                continue
            first, second = await living_entity(ctx.session, lower.member_node_id), await living_entity(ctx.session, upper.member_node_id)
            if first is not None and second is not None:
                kind = ContestKind.DEBATE if await best_skill(ctx.session, first.id, [SkillKind.ORATORY]) else ContestKind.TRIAL_OF_WISDOM
                bouts.append(Bout(kind, ContestStake.OFFICE, first, second, judge_id=await judge_of(ctx.session, polity), stake_node_id=polity))
            break
    return bouts


async def faith_bouts(ctx: TickContext, place_id: int, mortals: list[EntityRow]) -> list[Bout]:
    priests = [mortal for mortal in mortals if mortal.mortal_role in {MortalRole.PRIEST, MortalRole.SEER}]
    gods: dict[int, EntityRow] = {}
    for priest in priests:
        god = await living_patron(ctx.session, priest)
        if god is not None:
            gods.setdefault(god.id, priest)
    if len(gods) < 2 or not ctx.rng(seed_of("faith_contest", place_id, ctx.epoch)).chance(ctx.rules.contests.faith_pct):
        return []
    first, second = list(gods.values())[:2]
    return [Bout(ContestKind.SONG_CONTEST, ContestStake.DIVINE_FAVOUR, first, second, place_id=place_id)]


async def tend_contests(ctx: TickContext, places: dict[int, list[EntityRow]], tally: ContestTally) -> None:
    bouts: list[Bout] = [*await captive_bouts(ctx), *await court_bouts(ctx)]
    for place_id, mortals in sorted(places.items()):
        ids = [mortal.id for mortal in mortals]
        bouts += await rival_bouts(ctx, place_id, ids)
        bouts += await suitor_bouts(ctx, place_id, ids)
        bouts += await faith_bouts(ctx, place_id, mortals)
    busy: set[int] = set()
    for bout in bouts:
        if bout.challenger.id in busy or bout.defender.id in busy or bout.challenger.status is not EntityStatus.CANON:
            continue
        if await hold_contest(ctx, bout, tally) is not None:
            busy.update({bout.challenger.id, bout.defender.id})
