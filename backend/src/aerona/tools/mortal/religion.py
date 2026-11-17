from typing import Any

from aerona.catalog.mind import PREACHING_SKILLS
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, MessageIntent, PrayerRequest, TurnCounter
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.limits import RELATION_MIN
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.relations import AppealKind, PersuasionAim
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarCause
from aerona.engine.body.book import factor
from aerona.engine.dominion.worship import prayer_tone
from aerona.engine.gods import devotion
from aerona.engine.gods.devotion import RiteKind as EngineRite
from aerona.engine.lore import prophecy as prophecy_engine
from aerona.engine.primitives.faith import clear_seeking, foreign_patron, living_patron, patron_son, worship_creator
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import StepDraft
from aerona.engine.relations.persuasion import lift, persuade
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import DenyInput, PrayerInput, PreachInput, ProphesyInput, RiteInput, RiteKind, WorshipInput
from aerona.tools.mortal.support import MortalCreation, create_record, name_free, near, practised, require_target, wits_of

PERCENT = 100
CREATOR_ID = 0
PREACH_TARGETS = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION, EntityType.MORTAL})
RITES = {RiteKind.PRAYER: EngineRite.PRAYER, RiteKind.WEALTH: EngineRite.OFFERING, RiteKind.BLOOD: EngineRite.BLOOD, RiteKind.LIFE: EngineRite.LIFE}
JOIN = ", "


async def _drop_worship(call: MortalCall, entity: EntityRow, reason: str) -> None:
    bonds = BondRepository(call.session)
    for bond in await bonds.outgoing(entity.id, BondKind.WORSHIPS):
        if await call.session.get(SonRow, bond.target_node_id) is not None or await call.session.get(ForeignGodRow, bond.target_node_id) is not None:
            await bonds.deactivate(bond, call.epoch, reason[:KEY_MAX_LENGTH])


def _lower_stance(god: ForeignGodRow | None, amount: int) -> None:
    if god is not None:
        god.stance = max(RELATION_MIN, god.stance - amount)


async def worship(call: MortalCall, args: WorshipInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.WORSHIP_CHANGES, tools.worship_per_epoch, "mortal_tools.worship_per_epoch", MortalResult.WORSHIP_LIMIT)
    if args.son_id == CREATOR_ID:
        creator = await CosmosRepository(call.session).require_creator()
        if not await worship_creator(call.session, call.me, call.epoch, args.offering):
            fail(MortalResult.ALREADY_WORSHIP_CREATOR)
        await call.bump(TurnCounter.WORSHIP_CHANGES)
        call.target(creator.id)
        await call.record(
            "tools.mortal.worship_creator", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PATRON: creator.id}, facts={"offering": args.offering}
        )
        return result(MortalResult.WORSHIP_CREATOR)
    son = await call.session.get(SonRow, args.son_id)
    if son is None:
        fail(MortalResult.NO_SUCH_GOD)
    if son.status is SonStatus.DEAD:
        fail(MortalResult.GOD_IS_DEAD, name=son.name)
    old = await patron_son(call.session, call.me)
    if old is not None and old.id == son.id:
        fail(MortalResult.ALREADY_WORSHIP, name=son.name)
    old_foreign = await foreign_patron(call.session, call.me)
    if old is not None or old_foreign is not None:
        call.charge_actions(tools.worship_switch_action_cost)
    await _drop_worship(call, call.me, son.name)
    _lower_stance(old_foreign, tools.worship_foreign_attitude_loss)
    await BondRepository(call.session).connect(BondDraft(call.me.id, son.id, BondKind.WORSHIPS, call.epoch, args.offering))
    await clear_seeking(call.session, call.me.id)
    if old is not None and old.id != son.id:
        await SonRepository(call.session).change_relation(old.id, son.id, -tools.worship_switch_relation)
    await call.bump(TurnCounter.WORSHIP_CHANGES)
    call.target(son.id)
    await call.record(
        "tools.mortal.worship",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PATRON: son.id, IncidentRole.PREDECESSOR: old.id if old is not None and old.id != son.id else None},
        facts={"offering": args.offering},
        about=son.id,
    )
    return result(MortalResult.WORSHIPPING, name=son.name)


async def pray_to_creator(call: MortalCall, args: PrayerInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.PRAYERS, tools.pray_creator_per_epoch, "mortal_tools.pray_creator_per_epoch", MortalResult.PRAYER_LIMIT)
    creator = await CosmosRepository(call.session).require_creator()
    request = PrayerRequest.WISH if args.request else PrayerRequest.NONE
    call.session.add(
        MessageRow(
            epoch=call.epoch,
            sender_node_id=call.me.id,
            recipient_node_id=creator.id,
            intent=MessageIntent.PRAYER,
            text=args.prayer,
            request=request,
            wish=args.request,
            tone=await prayer_tone(call.session, call.me, creator.id),
        )
    )
    await call.bump(TurnCounter.PRAYERS)
    call.target(creator.id)
    suffix = lines.PRAYER_REQUEST.format(request=args.request) if args.request else ""
    await call.record(
        "tools.mortal.prayed", roles={IncidentRole.ACTOR: call.me.id}, facts={"request": str(suffix), "prayer": str(args.prayer)}, kind=ChronicleKind.PRAYER
    )
    return result(MortalResult.PRAYER_RISEN)


async def preach(call: MortalCall, args: PreachInput) -> str:
    await practised(call, PREACHING_SKILLS, call.rules.skills.preach_xp)
    tools = call.rules.mortal_tools
    god = await living_patron(call.session, call.me)
    if god is None:
        fail(MortalResult.NO_GOD_TO_PREACH)
    target = await require_target(call, args.target_id)
    if target.entity_type not in PREACH_TARGETS or not await near(call, target):
        fail(MortalResult.PREACH_TARGET)
    old = await patron_son(call.session, target)
    if old is not None and old.id == god.id:
        fail(MortalResult.ALREADY_FOLLOWS, name=target.name, god=god.name)
    old_foreign = await foreign_patron(call.session, target)
    rival = (old.charisma / tools.preach_old_god_divisor if old is not None else 0) + (
        old_foreign.charisma / tools.preach_old_god_divisor if old_foreign is not None else 0
    )
    influence = (stat_or(call.me, "influence", tools.preach_default_influence)) * await factor(call.session, call.me.id, Capacity.PRESENCE)
    piety = stat_or(target, "piety", tools.preach_default_piety)
    chance = tools.preach_base_pct + influence / 2 + god.charisma / tools.preach_god_charisma_divisor - rival - piety / tools.preach_piety_divisor
    sermon = await persuade(call.tick, call.me.id, target.id, AppealKind.BELIEF, PersuasionAim.FAITH, axis=ValueAxis.PIETY, toward=PERCENT, subject_id=god.id)
    chance *= lift(call.rules.persuasion.sermon_pct, sermon)
    call.target(target.id)
    argued = StepDraft(
        StepAction.PERSUADE,
        actor=call.me.id,
        target=target.id,
        amount=sermon.score,
        unit=FactUnit.PERCENT,
        outcome=StepOutcome.SUCCESS if sermon.success else StepOutcome.FAILURE,
    )
    if call.die(PERCENT, "sermon") > chance:
        await call.record(
            "tools.mortal.preach_failed", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: target.id}, kind=ChronicleKind.WORSHIP, steps=(argued,)
        )
        return result(MortalResult.NOT_HEARD)
    await _drop_worship(call, target, god.name)
    _lower_stance(old_foreign, tools.worship_foreign_attitude_loss)
    await BondRepository(call.session).connect(BondDraft(target.id, god.id, BondKind.WORSHIPS, call.epoch, lines.SERMON_BOND.format(me=call.me.name)))
    await clear_seeking(call.session, target.id)
    followers = stat(call.me, "followers")
    if followers is not None:
        set_stats(call.me, followers=min(call.rules.limits.cult_follower_cap, max(1, round(followers * (1 + tools.preach_follower_gain_pct / PERCENT)))))
    if old is not None:
        await SonRepository(call.session).change_relation(old.id, god.id, -tools.preach_relation)
    losers = [name for name in (old.name if old else None, old_foreign.name if old_foreign else None) if name]
    lost = lines.LOST_WORSHIPPER.format(names=JOIN.join(losers)) if losers else ""
    await call.record(
        "tools.mortal.preached",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: target.id, IncidentRole.SUBJECT: god.id},
        facts={"lost": str(lost), "sermon": str(args.sermon)},
        kind=ChronicleKind.WORSHIP,
        about=god.id,
        steps=(argued,),
    )
    return result(MortalResult.PREACHED, name=target.name, god=god.name)


async def deny_god(call: MortalCall, args: DenyInput) -> str:
    tools = call.rules.mortal_tools
    son = await patron_son(call.session, call.me)
    foreign = await foreign_patron(call.session, call.me)
    entities = EntityRepository(call.session)
    if son is None and foreign is None and await entities.has_flag(call.me.id, EntityFlag.GODLESS):
        fail(MortalResult.ALREADY_GODLESS)
    await _drop_worship(call, call.me, args.reason)
    if foreign is not None:
        _lower_stance(foreign, tools.deny_foreign_attitude)
        foreign.faith = max(0, foreign.faith - tools.deny_foreign_faith)
    await entities.add_flag(call.me.id, EntityFlag.GODLESS, call.epoch)
    if son is not None:
        son.existence = max(0, son.existence - tools.deny_son_existence)
        await BondRepository(call.session).connect(
            BondDraft(son.id, call.me.id, BondKind.ENEMY, call.epoch, lines.DENIAL_BOND.format(reason=args.reason), war_cause=WarCause.DIVINE_GRUDGE)
        )
        call.target(son.id)
    denied = son.id if son is not None else foreign.id if foreign is not None else None
    await call.record(
        "tools.mortal.denied" if denied is not None else "tools.mortal.denied_all",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: denied},
        facts={"reason": args.reason},
    )
    return result(MortalResult.DENIED)


async def prophesy(call: MortalCall, args: ProphesyInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.PROPHECIES, tools.prophesy_per_epoch, "mortal_tools.prophesy_per_epoch", MortalResult.PROPHECY_LIMIT)
    await name_free(call, args.name)
    related = []
    for related_id in (args.related_ids or [])[: tools.prophecy_max_related]:
        entity = await call.session.get(EntityRow, related_id)
        if entity is not None and entity.status is EntityStatus.CANON:
            related.append(entity)
    concerns = lines.PROPHECY_CONCERNS.format(names=JOIN.join(entity.name for entity in related)) if related else ""
    description = lines.PROPHECY_TEXT.format(me=call.me.name, saying=args.saying, concerns=concerns)
    subtype = lines.PROPHECY_SUBTYPES["cult" if call.me.entity_type is EntityType.CULT else "mortal"]
    certainty = max(0, min(PERCENT, tools.prophecy_certainty_base + round((await wits_of(call)) / 2)))
    await practised(call, (SkillKind.PROPHECY,), call.rules.skills.preach_xp)
    prophecy = await create_record(call, MortalCreation(args.name, EntityType.PROPHECY, description, subtype=subtype, stats={"certainty": certainty}))
    bonds = BondRepository(call.session)
    await bonds.connect(BondDraft(call.me.id, prophecy.id, BondKind.PROPHESIES, call.epoch))
    for entity in related:
        await bonds.connect(BondDraft(prophecy.id, entity.id, BondKind.PROPHESIES, call.epoch, lines.PROPHECY_BOND))
    told = prophecy_engine.Foretelling(
        predicate=args.predicate,
        subject_id=args.subject_id,
        second_id=args.second_id,
        archetype=args.archetype,
        sky_kind=args.sky_kind,
        event_kind=args.event_kind,
        within_epochs=args.within_epochs,
        consequence=args.consequence,
        consequence_id=args.consequence_id,
    )
    await prophecy_engine.typed_condition(call.tick, prophecy, told)
    await call.bump(TurnCounter.PROPHECIES)
    await call.record(
        "tools.mortal.prophesied",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: prophecy.id},
        facts={"name": str(prophecy.name)},
        kind=ChronicleKind.PROPHECY,
    )
    return result(MortalResult.PROPHESIED, id=prophecy.id, name=prophecy.name)


async def resurrection_rite(call: MortalCall, args: RiteInput) -> str:
    cap = call.rules.death.rite_per_epoch
    await call.within_limit(TurnCounter.RESURRECTION_RITES, cap, "death.rite_per_epoch", MortalResult.RITE_LIMIT)
    son = await call.session.get(SonRow, args.son_id)
    worships = son is not None and await BondRepository(call.session).exists_between(call.me.id, son.id, BondKind.WORSHIPS)
    if son is None or son.status is not SonStatus.DEAD or not worships:
        fail(MortalResult.RITE_NOT_YOURS)
    victim = await call.session.get(EntityRow, args.victim_id) if args.victim_id is not None else None
    outcome = await perform_rite(call, son, RITES[args.kind], victim)
    await call.bump(TurnCounter.RESURRECTION_RITES)
    call.target(son.id)
    if call.me.status is not EntityStatus.CANON:
        call.died = True
    return result(MortalResult.RITE_DONE, text=outcome)


async def perform_rite(call: MortalCall, son: SonRow, kind: EngineRite, victim: EntityRow | None) -> str:
    outcome = await devotion.resurrection_rite(call.tick, call.me, son, kind, victim)
    return outcome.text


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.WORSHIP, mortal, WorshipInput, ToolMeta(ActionKind.WORSHIP, no_cost), worship),
        ToolSpec(MortalToolId.PRAY_TO_CREATOR, mortal, PrayerInput, ToolMeta(ActionKind.PRAY_TO_CREATOR, no_cost), pray_to_creator),
        ToolSpec(MortalToolId.PREACH, mortal, PreachInput, ToolMeta(ActionKind.PREACH, standard), preach),
        ToolSpec(MortalToolId.DENY_GOD, mortal, DenyInput, ToolMeta(ActionKind.DENY_GOD, standard), deny_god),
        ToolSpec(MortalToolId.PROPHESY, mortal, ProphesyInput, ToolMeta(ActionKind.PROPHESY, standard), prophesy),
        ToolSpec(MortalToolId.RESURRECTION_RITE, mortal, RiteInput, ToolMeta(ActionKind.RESURRECTION_RITE, standard), resurrection_rite),
    ]
