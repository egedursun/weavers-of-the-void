import pytest
from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.presence import PresenceSessionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.presence import PresenceGuise, PresenceRecord, PresenceStatus
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.engine.mind.describe import mind_lines
from aerona.engine.mind.memories import remember
from aerona.prompts import PromptId, render
from aerona.services.presence.context import system_context
from aerona.services.presence.speakers import require_speaker
from aerona.services.presence.tools import SpeakerTools, speaker_tools
from aerona.tools.toolkit import Toolkits
from tests.api.conftest import ApiWorld, seeded
from tests.presence.beings import beast, cosmic_being, foreign_god

SON_READS = frozenset({"world_summary", "inspect_entity", "search_entities", "my_memory", "inspect_sibling", "recall_event"})
GUISE_LINES = {
    PresenceGuise.CREATOR: "the Creator of this cosmos, speaks to you, revealed",
    PresenceGuise.UNNAMED_POWER: "You do not know which power it is",
    PresenceGuise.DREAM_VOICE: "A voice comes to you in a dream",
    PresenceGuise.ORDINARY: "Someone of your own world whom you do not know speaks to you",
}


def toolkits_of(api: ApiWorld) -> Toolkits:
    found = api.services.agents.toolkits
    assert isinstance(found, Toolkits)
    return found


async def tools_for(api: ApiWorld, node_id: int, record: PresenceRecord, *, world_busy: bool = False) -> SpeakerTools:
    rules = api.services.rules.current
    async with api.services.database.read() as session:
        speaker = await require_speaker(session, rules, node_id)
    epoch = seeded(api).core.cosmos.epoch
    return await speaker_tools(api.services.database, toolkits_of(api), rules, speaker, record=record, epoch=epoch, world_busy=world_busy)


async def system_text(api: ApiWorld, node_id: int, guise: PresenceGuise, record: PresenceRecord, *, world_busy: bool = False) -> str:
    rules = api.services.rules.current
    tools = await tools_for(api, node_id, record, world_busy=world_busy)
    holder = PresenceSessionRow(node_id=node_id, guise=guise, record=record, status=PresenceStatus.OPEN, dead_when_summoned=False, opened_epoch=1)
    async with api.services.database.read() as session:
        speaker = await require_speaker(session, rules, node_id)
        return render(PromptId.PRESENCE_SYSTEM, await system_context(session, rules, speaker, holder, tools))


async def test_on_the_record_a_living_son_gets_its_own_acting_tools(presence: ApiWorld) -> None:
    tools = await tools_for(presence, seeded(presence).core.son.id, PresenceRecord.ON_RECORD)
    assert tools.acting and "touch_mortal" in tools.names
    assert tools.read_only >= SON_READS
    assert tools.points > 0


async def test_off_the_record_a_son_only_reads(presence: ApiWorld) -> None:
    tools = await tools_for(presence, seeded(presence).core.son.id, PresenceRecord.OFF_RECORD)
    assert not tools.acting and set(tools.names) == set(tools.read_only) == SON_READS


@pytest.mark.parametrize("status", [SonStatus.DEAD, SonStatus.ASLEEP])
async def test_a_dead_or_sleeping_son_only_reads_even_on_the_record(presence: ApiWorld, status: SonStatus) -> None:
    son_id = seeded(presence).core.son.id
    async with presence.services.database.write() as session:
        son = await session.get(SonRow, son_id)
        assert son is not None
        son.status = status
        son.death_epoch = 1 if status is SonStatus.DEAD else None
    tools = await tools_for(presence, son_id, PresenceRecord.ON_RECORD)
    assert not tools.acting and set(tools.names) == SON_READS


async def test_a_foreign_god_has_no_tools(presence: ApiWorld) -> None:
    async with presence.services.database.write() as session:
        god_id = await foreign_god(session, seeded(presence).core)
    tools = await tools_for(presence, god_id, PresenceRecord.ON_RECORD)
    assert tools.toolkit is None and tools.tools() == [] and not tools.acting
    text = await system_text(presence, god_id, PresenceGuise.UNNAMED_POWER, PresenceRecord.ON_RECORD)
    assert "Ombrun" in text and "not one of the divine children" in text


async def test_a_mortal_acts_through_its_own_tools_on_the_record_and_reads_off_it(presence: ApiWorld) -> None:
    sage = seeded(presence).core.extra["sage"].id
    kept = await tools_for(presence, sage, PresenceRecord.ON_RECORD)
    loose = await tools_for(presence, sage, PresenceRecord.OFF_RECORD)
    assert kept.acting and set(kept.names) - kept.read_only
    assert loose.names and set(loose.names) == set(loose.read_only)
    assert set(loose.names) == set(kept.read_only)


async def test_a_cosmic_being_reads_but_never_acts(presence: ApiWorld) -> None:
    async with presence.services.database.write() as session:
        being = await cosmic_being(session, seeded(presence).core)
    tools = await tools_for(presence, being.id, PresenceRecord.ON_RECORD)
    assert not tools.acting and set(tools.names) == set(tools.read_only)


async def test_while_the_world_is_lived_through_nobody_acts(presence: ApiWorld) -> None:
    son_id = seeded(presence).core.son.id
    tools = await tools_for(presence, son_id, PresenceRecord.ON_RECORD, world_busy=True)
    assert not tools.acting and tools.paused
    text = await system_text(presence, son_id, PresenceGuise.CREATOR, PresenceRecord.ON_RECORD, world_busy=True)
    assert "cannot act during this audience" in text


@pytest.mark.parametrize("guise", list(PresenceGuise))
async def test_every_guise_tells_the_speaker_who_speaks(presence: ApiWorld, guise: PresenceGuise) -> None:
    core = seeded(presence).core
    text = await system_text(presence, core.extra["sage"].id, guise, PresenceRecord.OFF_RECORD)
    assert GUISE_LINES[guise] in text
    assert "Ilvane" in text
    others = [line for other, line in GUISE_LINES.items() if other is not guise]
    assert not any(line in text for line in others)
    if guise is PresenceGuise.CREATOR:
        assert f"{core.creator.name}, the Creator of this cosmos" in text


async def test_the_record_reaches_the_context(presence: ApiWorld) -> None:
    son_id = seeded(presence).core.son.id
    kept = await system_text(presence, son_id, PresenceGuise.CREATOR, PresenceRecord.ON_RECORD)
    loose = await system_text(presence, son_id, PresenceGuise.CREATOR, PresenceRecord.OFF_RECORD)
    assert "What passes here is kept" in kept and "You may act through your own acting tools" in kept and "actions left" in kept
    assert "Nothing said here will be kept" in loose and "You may act" not in loose


async def test_the_dead_know_when_and_how_they_died(presence: ApiWorld) -> None:
    son_id = seeded(presence).core.son.id
    async with presence.services.database.write() as session:
        son = await session.get(SonRow, son_id)
        assert son is not None
        son.status = SonStatus.DEAD
        son.death_epoch = 3
        son.death_cause = SonDeathCause.KILLED_BY_SIBLING
    text = await system_text(presence, son_id, PresenceGuise.CREATOR, PresenceRecord.ON_RECORD)
    assert "You died in age 3: killed by sibling." in text
    assert "called back to speak" in text
    living = await system_text(presence, seeded(presence).core.extra["sage"].id, PresenceGuise.CREATOR, PresenceRecord.ON_RECORD)
    assert "YOUR DEATH" not in living


async def test_an_audience_memory_reaches_later_turns_without_naming_who_spoke(presence: ApiWorld) -> None:
    core = seeded(presence).core
    rules = presence.services.rules.current
    async with presence.services.database.write() as session:
        sage = await session.get(EntityRow, core.extra["sage"].id)
        assert sage is not None
        await remember(
            session,
            rules,
            holder_id=sage.id,
            subject_id=core.creator.id,
            kind=MemoryKind.AUDIENCE,
            magnitude=90,
            epoch=core.cosmos.epoch,
            note="Someone of my own world spoke with me: of the ford",
            merge=False,
        )
        lines = await mind_lines(session, rules, sage, core.cosmos.epoch, private=True)
    found = [line for line in lines if "an audience" in line]
    assert found and "Someone of my own world spoke with me: of the ford" in found[0]
    assert core.creator.name not in found[0]


async def test_every_kind_of_speaker_gets_a_whole_context_alive_and_dead(presence: ApiWorld) -> None:
    core = seeded(presence).core
    rules = presence.services.rules.current
    async with presence.services.database.write() as session:
        god_id = await foreign_god(session, core)
        being = await cosmic_being(session, core)
        bright = await beast(session, core, rules.mortal_agents.creature_min_intelligence)
        spirit = (await session.scalars(select(EntityRow).where(EntityRow.name == "Weeping Shade"))).one()
        ids = [core.son.id, god_id, core.extra["sage"].id, spirit.id, being.id, bright.id]
    for node_id in ids:
        for record in PresenceRecord:
            text = await system_text(presence, node_id, PresenceGuise.UNNAMED_POWER, record)
            assert "WHO SPEAKS TO YOU" in text and "THIS AUDIENCE" in text
    async with presence.services.database.write() as session:
        sage = await session.get(EntityRow, core.extra["sage"].id)
        assert sage is not None
        sage.status, sage.end_epoch = EntityStatus.DEAD, 1
    dead = await system_text(presence, core.extra["sage"].id, PresenceGuise.CREATOR, PresenceRecord.ON_RECORD)
    assert "YOUR DEATH" in dead and "You died in age 1" in dead
