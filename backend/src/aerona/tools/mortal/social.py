from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.relations import CONTESTS, INTERACTIONS, STAKE_LABELS
from aerona.catalog.renown import LORE_LABELS, PRICE_LABELS
from aerona.constants.tool_inputs import NAME_MIN, REASON_MAX
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import AppealKind, ContestEnd, ContestKind, ContestStake, InteractionKind, PersuasionAim
from aerona.domain.enums.renown import LorePrice
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.mortal.kin import children_of, sworn_kin_of
from aerona.engine.mortal.kinship import foster
from aerona.engine.mortal.life import young
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import connect
from aerona.engine.relations.book import relation
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest
from aerona.engine.relations.interactions import SocialTally, interact, load_scene
from aerona.engine.relations.persuasion import persuade
from aerona.engine.renown.lore import holdings, trade, value_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import require_target

SPAN = 100


class SocialiseInput(ToolInput):
    target_id: int
    interaction: InteractionKind


class ContestInput(ToolInput):
    target_id: int
    kind: ContestKind
    stake: ContestStake = ContestStake.HONOUR


class PersuadeInput(ToolInput):
    target_id: int
    appeal: AppealKind
    aim: PersuasionAim = PersuasionAim.BELIEF
    axis: ValueAxis | None = None
    toward: int = SPAN
    subject_id: int | None = None


class SwearKinshipInput(ToolInput):
    target_id: int
    rite: Annotated[str, Field(min_length=NAME_MIN, max_length=REASON_MAX)]


class FosterChildInput(ToolInput):
    child_id: int
    household_id: int


async def fellow(call: MortalCall, target_id: int) -> EntityRow:
    if call.me.entity_type is not EntityType.MORTAL:
        fail(MortalResult.SOCIAL_NOT_MORTAL)
    other = await require_target(call, target_id)
    if other.entity_type is not EntityType.MORTAL or other.id == call.me.id:
        fail(MortalResult.SOCIAL_TARGET)
    if other.location_id != call.me.location_id:
        fail(MortalResult.SOCIAL_FAR, name=other.name)
    return other


async def socialise(call: MortalCall, args: SocialiseInput) -> str:
    other = await fellow(call, args.target_id)
    scene = await load_scene(call.tick, call.me.location_id or other.id, [call.me, other])
    rng = call.tick.rng(seed_of("chosen_interaction", call.me.id, other.id, call.epoch))
    landed = await interact(scene, call.me.id, other.id, args.interaction, rng=rng, tally=SocialTally())
    call.target(other.id)
    label = INTERACTIONS[args.interaction].label.lower()
    return result(MortalResult.SOCIALISED if landed else MortalResult.SOCIAL_MISSED, action=label, name=other.name)


async def challenge(call: MortalCall, args: ContestInput) -> str:
    other = await fellow(call, args.target_id)
    bout = Bout(args.kind, args.stake, call.me, other, place_id=call.me.location_id)
    row = await hold_contest(call.tick, bout, ContestTally())
    if row is None:
        fail(MortalResult.SOCIAL_TARGET)
    call.target(other.id)
    outcome = "drew" if row.outcome is ContestEnd.DRAWN else "won" if row.outcome is ContestEnd.CHALLENGER else "lost"
    return result(MortalResult.CONTEST_HELD, kind=CONTESTS[args.kind].label.lower(), stake=STAKE_LABELS[args.stake].lower(), name=other.name, outcome=outcome)


async def aim_target(call: MortalCall, args: PersuadeInput) -> tuple[EntityRow, int | None]:
    if args.aim is PersuasionAim.SURRENDER:
        town = await require_target(call, args.subject_id)
        siege = await call.session.scalar(
            select(SiegeRow).where(SiegeRow.besieged_entity_id == town.id, SiegeRow.status == SiegeStatus.ONGOING).order_by(SiegeRow.id.desc()).limit(1)
        )
        if siege is None:
            fail(MortalResult.PERSUASION_AIM, why=f"{town.name} is not under siege")
        return await require_target(call, args.target_id), town.id
    if args.aim is PersuasionAim.CONFESSION:
        accused = await require_target(call, args.target_id)
        case = await call.session.scalar(
            select(CrimeCaseRow)
            .where(CrimeCaseRow.accused_entity_id == accused.id, CrimeCaseRow.stage == CaseStage.TRIAL)
            .where((CrimeCaseRow.investigator_entity_id == call.me.id) | (CrimeCaseRow.judge_entity_id == call.me.id))
            .limit(1)
        )
        if case is None:
            fail(MortalResult.PERSUASION_AIM, why=f"you hold no case against {accused.name}")
        return accused, case.settlement_entity_id
    if args.aim is PersuasionAim.BELIEF and args.axis is None:
        fail(MortalResult.PERSUASION_AIM, why="name the belief at stake")
    return await fellow(call, args.target_id), args.subject_id


async def argue(call: MortalCall, args: PersuadeInput) -> str:
    other, subject = await aim_target(call, args)
    argument = await persuade(call.tick, call.me.id, other.id, args.appeal, args.aim, axis=args.axis, toward=args.toward, subject_id=subject)
    call.target(other.id)
    return result(MortalResult.PERSUADED if argument.success else MortalResult.NOT_PERSUADED, name=other.name, score=argument.score)


async def swear_kinship(call: MortalCall, args: SwearKinshipInput) -> str:
    other = await fellow(call, args.target_id)
    if other.id in await sworn_kin_of(call.session, call.me.id):
        fail(MortalResult.KIN_ALREADY, name=other.name)
    at = call.tick.rules.social.friend_at
    mine, theirs = await relation(call.session, call.me.id, other.id), await relation(call.session, other.id, call.me.id)
    if mine is None or theirs is None or mine.friendship < at or theirs.friendship < at:
        fail(MortalResult.KIN_NOT_FRIENDS, name=other.name)
    await connect(call.session, call.me.id, other.id, BondKind.SWORN_KIN, call.epoch, description=args.rite)
    call.target(other.id)
    return result(MortalResult.KIN_SWORN, name=other.name, rite=args.rite)


async def foster_child(call: MortalCall, args: FosterChildInput) -> str:
    child = await require_target(call, args.child_id)
    if child.id not in await children_of(call.session, call.me.id):
        fail(MortalResult.CHILD_REFUSED, why=f"{child.name} is not your child")
    profile = await call.session.get(MortalProfileRow, child.id)
    if profile is None or not young(profile.life_stage):
        fail(MortalResult.CHILD_REFUSED, why=f"{child.name} is no longer a child")
    household = await call.session.get(HouseholdRow, args.household_id)
    if household is None or household.head_node_id is None or household.head_node_id in {call.me.id, child.id}:
        fail(MortalResult.CHILD_REFUSED, why="name another household with a head")
    fosterer = await require_target(call, household.head_node_id)
    await foster(call.session, child.id, fosterer.id, call.epoch, description="sent to be raised in another house")
    call.target(child.id)
    return result(MortalResult.CHILD_FOSTERED, child=child.name, fosterer=fosterer.name)


class LoreInput(ToolInput):
    buyer_id: int
    kind: KnowledgeKind
    key: str
    subject_id: int | None = None
    price: LorePrice | None = None


async def sell_lore(call: MortalCall, args: LoreInput) -> str:
    buyer = await require_target(call, args.buyer_id)
    item = (args.kind, args.key, args.subject_id)
    if (args.key, args.subject_id) not in await holdings(call.session, call.me.id, args.kind):
        fail(MortalResult.LORE_REFUSED, name=buyer.name)
    row = await trade(call.tick, call.me, buyer, item, value=await value_of(call.tick, item), price=args.price)
    if row is None:
        fail(MortalResult.LORE_REFUSED, name=buyer.name)
    call.target(buyer.id)
    return result(MortalResult.LORE_TRADED, name=buyer.name, lore=LORE_LABELS[args.kind].lower(), price=PRICE_LABELS[row.price].lower())


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.SOCIALISE, mortal, SocialiseInput, ToolMeta(ActionKind.INFLUENCE, standard), socialise),
        ToolSpec(MortalToolId.CHALLENGE_TO_CONTEST, mortal, ContestInput, ToolMeta(ActionKind.INFLUENCE, standard), challenge),
        ToolSpec(MortalToolId.PERSUADE, mortal, PersuadeInput, ToolMeta(ActionKind.INFLUENCE, standard), argue),
        ToolSpec(MortalToolId.TRADE_LORE, mortal, LoreInput, ToolMeta(ActionKind.INFLUENCE, standard), sell_lore),
        ToolSpec(MortalToolId.SWEAR_KINSHIP, mortal, SwearKinshipInput, ToolMeta(ActionKind.INFLUENCE, standard), swear_kinship),
        ToolSpec(MortalToolId.FOSTER_CHILD, mortal, FosterChildInput, ToolMeta(ActionKind.INFLUENCE, standard), foster_child),
    ]
