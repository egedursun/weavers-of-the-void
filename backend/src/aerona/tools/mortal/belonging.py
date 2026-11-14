from typing import Any

from aerona.db.tables.belonging import SatireRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.belonging import SatireSource
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import SkillKind
from aerona.engine.belonging import control
from aerona.engine.belonging.refuge import refuge_of
from aerona.engine.belonging.sanctuary import fugitives, host_for
from aerona.engine.belonging.satire import SatireTally, judge
from aerona.engine.collective.book import ruler_id
from aerona.engine.cycles.book import realm_of
from aerona.engine.mind.book import skills_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines


class SeekSanctuaryInput(ToolInput):
    pass


class MockTheRulerInput(ToolInput):
    pass


async def seek_sanctuary(call: MortalCall, args: SeekSanctuaryInput) -> str:
    me = call.me
    if await refuge_of(call.session, me.id) is not None:
        fail(MortalResult.SANCTUARY_DENIED, why="you already have sanctuary")
    hunted = next((item for item in await fugitives(call.tick) if item.mortal.id == me.id), None)
    if hunted is None:
        fail(MortalResult.SANCTUARY_DENIED, why="no one hunts you")
    found = await host_for(call.tick, hunted)
    if found is None:
        fail(MortalResult.SANCTUARY_DENIED, why="no temple or welcoming hearth in your town will take you in")
    host, kind = found
    await control.set_record(
        call.tick,
        "sanctuary",
        {},
        {
            "fugitive_entity_id": me.id,
            "host_entity_id": host.id,
            "kind": kind,
            "fugitive_kind": hunted.kind,
            "pursuer_entity_id": hunted.pursuer,
            "fee": call.tick.rules.sanctuary.fee,
        },
    )
    call.target(host.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.SEEK_SANCTUARY, entity_ids=[me.id, host.id], me=me.name, host=host.name)
    return result(MortalResult.SANCTUARY_FOUND, host=host.name)


async def mock_the_ruler(call: MortalCall, args: MockTheRulerInput) -> str:
    me = call.me
    realm = await realm_of(call.session, me.location_id) if me.location_id is not None else None
    ruler = await ruler_id(call.tick, realm) if realm is not None else None
    if realm is None or ruler is None:
        fail(MortalResult.SATIRE_DECLINED, why="your town answers to no ruler")
    if ruler == me.id:
        fail(MortalResult.SATIRE_DECLINED, why="you cannot mock yourself as ruler")
    oratory = (await skills_of(call.session, me.id)).get(SkillKind.ORATORY)
    bite = clamp_int(call.tick.rules.satire.bite + (oratory.level if oratory is not None else 0) * 2, 0, 100)
    row = await control.set_record(
        call.tick,
        "satire",
        {},
        {"satirist_entity_id": me.id, "target_entity_id": ruler, "polity_entity_id": realm, "source": SatireSource.MORTAL, "bite": bite},
    )
    if isinstance(row, SatireRow):
        await judge(call.tick, row, SatireTally())
    call.target(ruler)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.MOCK_THE_RULER, entity_ids=[me.id, ruler], me=me.name)
    return result(MortalResult.SATIRE_TOLD, bite=bite, tolerated=isinstance(row, SatireRow) and row.tolerated)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SEEK_SANCTUARY, mortal, SeekSanctuaryInput, meta, seek_sanctuary),
        ToolSpec(MortalToolId.MOCK_THE_RULER, mortal, MockTheRulerInput, meta, mock_the_ruler),
    ]
