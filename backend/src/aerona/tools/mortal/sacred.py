from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.sacred import GeniusLocusRow, MillenarianRow, MysticRow, SpiritOfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.sacred import DivinationQuestion, MysticState, PetitionKind
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred import control
from aerona.engine.sacred.mysteries import LIVING_MOVEMENT, MysteryTally, answering_god, become_mystic, open_to_visions, see_vision
from aerona.engine.sacred.places import realm_ruled_by, town_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class PetitionSpiritInput(ToolInput):
    spirit_id: int
    kind: PetitionKind


class OfferToSpiritInput(ToolInput):
    spirit_id: int


class SeekVisionInput(ToolInput):
    pass


class ConsultDivinerInput(ToolInput):
    question: DivinationQuestion


class PreachEndTimeInput(ToolInput):
    pass


async def petition_spirit(call: MortalCall, args: PetitionSpiritInput) -> str:
    office = await call.session.get(SpiritOfficeRow, args.spirit_id)
    spirit = await living_entity(call.session, args.spirit_id)
    if office is None or spirit is None or office.dismissed or held(spirit.id):
        fail(MortalResult.PETITION_DECLINED, why="no spirit holds that office")
    defendant = None
    if args.kind is PetitionKind.SUIT:
        offended = await call.session.scalar(
            select(GeniusLocusRow.spirit_entity_id)
            .where(
                GeniusLocusRow.community_entity_id == office.jurisdiction_entity_id,
                GeniusLocusRow.offended.is_not(None),
                GeniusLocusRow.spirit_entity_id != spirit.id,
            )
            .limit(1)
        )
        if offended is None:
            fail(MortalResult.PETITION_DECLINED, why="no spirit under that office has wronged your town")
        defendant = int(offended)
    try:
        row = await control.lodge_petition(call.tick, call.me.id, spirit.id, args.kind, defendant_id=defendant, bribe=0)
    except ValidationFailedError as error:
        fail(MortalResult.PETITION_DECLINED, why=str(error).rstrip("."))
    call.target(spirit.id)
    await call.record("tools.mortal.petition_spirit", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: spirit.id}, kind=ChronicleKind.PRAYER)
    return result(MortalResult.PETITION_FILED, spirit=spirit.name, kind=spoken(args.kind), due=row.due_epoch)


async def offer_to_spirit(call: MortalCall, args: OfferToSpiritInput) -> str:
    row = await call.session.get(GeniusLocusRow, args.spirit_id)
    spirit = await living_entity(call.session, args.spirit_id)
    if row is None or spirit is None or held(spirit.id):
        fail(MortalResult.SPIRIT_OFFERING_DECLINED, why="no spirit dwells there")
    table = call.tick.rules.genius_loci
    row.offerings += table.hunger
    row.last_offering_epoch = call.tick.epoch
    if "contentment" not in row.locked:
        row.contentment = clamp_int(row.contentment + table.contentment_step, 0, PERCENT)
    call.target(spirit.id)
    await call.record("tools.mortal.offer_to_spirit", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: spirit.id}, kind=ChronicleKind.PRAYER)
    return result(MortalResult.SPIRIT_OFFERING_MADE, spirit=spirit.name, contentment=row.contentment)


async def seek_vision(call: MortalCall, args: SeekVisionInput) -> str:
    if held(call.me.id) or not await open_to_visions(call.tick, call.me):
        fail(MortalResult.VISION_DECLINED, why="no vision comes to a mind not yet open to it")
    sender = await answering_god(call.tick, call.me, f"seek.answer.{call.me.id}")
    row = await call.session.get(MysticRow, call.me.id)
    tally = MysteryTally()
    if row is None:
        row = await become_mystic(call.tick, call.me, sender, tally)
    else:
        await see_vision(call.tick, row, call.me, sender, tally)
    call.target(call.me.id)
    await call.record("tools.mortal.seek_vision", roles={IncidentRole.ACTOR: call.me.id}, kind=ChronicleKind.WORSHIP)
    return result(MortalResult.VISION_SEEN, visions=row.visions, followers=row.followers)


async def consult_diviner(call: MortalCall, args: ConsultDivinerInput) -> str:
    realm_id = await realm_ruled_by(call.session, call.me.id)
    if realm_id is None:
        fail(MortalResult.OMENS_DECLINED, why="only a ruler keeps court diviners")
    try:
        row = await control.read_omens(call.tick, realm_id, args.question, verdict=None, swayed_by=None, system_id=None)
    except ValidationFailedError as error:
        fail(MortalResult.OMENS_DECLINED, why=str(error).rstrip("."))
    call.target(realm_id)
    await call.record(
        "tools.mortal.consult_diviner",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: realm_id},
        facts={"question": args.question},
        kind=ChronicleKind.FATE,
    )
    return result(MortalResult.OMENS_READ, question=spoken(args.question), verdict=spoken(row.verdict))


async def preach_end_time(call: MortalCall, args: PreachEndTimeInput) -> str:
    mystic = await call.session.get(MysticRow, call.me.id)
    if (mystic is None or mystic.state is MysticState.LAPSED) and call.me.mortal_role is not MortalRole.SEER:
        fail(MortalResult.END_DECLINED, why="none would heed you; no vision or sight of the future marks you")
    town = await town_of(call.session, call.me)
    if town is None or held(town.id):
        fail(MortalResult.END_DECLINED, why="you stand in no town")
    busy = await call.session.scalar(
        select(MillenarianRow.id).where(MillenarianRow.settlement_entity_id == town.id, MillenarianRow.stage.in_(LIVING_MOVEMENT)).limit(1)
    )
    if busy is not None:
        fail(MortalResult.END_DECLINED, why="the town already awaits the end")
    row = await control.stir_movement(call.tick, town.id, call.me.id, None)
    call.target(town.id)
    await call.record(
        "tools.mortal.preach_end_time",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: town.id},
        facts={"town": str(town.name)},
        kind=ChronicleKind.WORSHIP,
    )
    return result(MortalResult.END_PREACHED, town=town.name, end=row.end_epoch, members=row.members)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PETITION_SPIRIT, mortal, PetitionSpiritInput, meta, petition_spirit),
        ToolSpec(MortalToolId.OFFER_TO_SPIRIT, mortal, OfferToSpiritInput, meta, offer_to_spirit),
        ToolSpec(MortalToolId.SEEK_VISION, mortal, SeekVisionInput, meta, seek_vision),
        ToolSpec(MortalToolId.CONSULT_DIVINER, mortal, ConsultDivinerInput, meta, consult_diviner),
        ToolSpec(MortalToolId.PREACH_END_TIME, mortal, PreachEndTimeInput, meta, preach_end_time),
    ]
