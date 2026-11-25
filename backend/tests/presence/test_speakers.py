import pytest
from sqlalchemy import select

from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.presence import SpeakerGroup
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.services.presence.speakers import speaker_card, speaker_lines, speaker_of
from tests.api.conftest import ApiWorld, seeded
from tests.presence.beings import beast, cosmic_being, foreign_god

DEAD_SONS = frozenset({SonStatus.DEAD})
DEAD_GODS = frozenset({ForeignGodStatus.DEAD})
ENDED = frozenset({EntityStatus.DEAD, EntityStatus.DESTROYED})


@pytest.mark.parametrize("status", list(SonStatus))
async def test_every_son_speaks_in_every_status(presence: ApiWorld, status: SonStatus) -> None:
    rules = presence.services.rules.current
    async with presence.services.database.write() as session:
        son = await session.get(SonRow, seeded(presence).core.son.id)
        assert son is not None
        son.status = status
        if status in DEAD_SONS:
            son.death_epoch = 1
            son.death_cause = SonDeathCause.FADING
        found = await speaker_of(session, rules, son)
        assert found is not None and found.group is SpeakerGroup.SONS
        assert found.dead is (status in DEAD_SONS)
        card = await speaker_card(session, found)
        assert (card.death is not None) is (status in DEAD_SONS)
        if card.death is not None:
            assert card.death.how == "fading" and card.death.epoch == 1


@pytest.mark.parametrize("status", list(ForeignGodStatus))
async def test_every_foreign_god_speaks_in_every_status(presence: ApiWorld, status: ForeignGodStatus) -> None:
    rules = presence.services.rules.current
    async with presence.services.database.write() as session:
        god = await session.get(ForeignGodRow, await foreign_god(session, seeded(presence).core))
        assert god is not None
        god.status = status
        if status in DEAD_GODS:
            god.death_epoch = 2
        found = await speaker_of(session, rules, god)
        assert found is not None and found.group is SpeakerGroup.FOREIGN_GODS
        assert found.dead is (status in DEAD_GODS)


@pytest.mark.parametrize("status", list(EntityStatus))
async def test_a_mortal_speaks_in_every_status_but_rejected(presence: ApiWorld, status: EntityStatus) -> None:
    rules = presence.services.rules.current
    async with presence.services.database.write() as session:
        sage = await session.get(EntityRow, seeded(presence).core.extra["sage"].id)
        assert sage is not None
        sage.status = status
        if status in ENDED:
            sage.end_epoch = 1
        found = await speaker_of(session, rules, sage)
        if status is EntityStatus.REJECTED:
            assert found is None
            return
        assert found is not None and found.group is SpeakerGroup.MORTALS
        assert found.dead is (status in ENDED)


async def test_spirits_beings_and_minded_beasts_speak_collectives_and_dull_beasts_do_not(presence: ApiWorld) -> None:
    rules = presence.services.rules.current
    floor = rules.mortal_agents.creature_min_intelligence
    core = seeded(presence).core
    async with presence.services.database.write() as session:
        bright = await beast(session, core, floor, "Bright Hunger")
        dull = await beast(session, core, max(0, floor - 1), "Dull Hunger")
        being = await cosmic_being(session, core)
        spirit = (await session.scalars(select(EntityRow).where(EntityRow.name == "Weeping Shade"))).one()
        assert (await speaker_of(session, rules, bright)) is not None
        assert (await speaker_of(session, rules, dull)) is None
        found_being = await speaker_of(session, rules, being)
        assert found_being is not None and found_being.group is SpeakerGroup.BEINGS
        found_spirit = await speaker_of(session, rules, spirit)
        assert found_spirit is not None and found_spirit.group is SpeakerGroup.SPIRITS
        assert await speaker_of(session, rules, await session.get(EntityRow, core.people.id)) is None
        assert await speaker_of(session, rules, await session.get(EntityRow, core.extra["town"].id)) is None
        assert await speaker_of(session, rules, await session.get(CreatorRow, core.creator.id)) is None
        assert await speaker_of(session, rules, await session.get(NodeRow, core.world.id)) is None
        assert await speaker_of(session, rules, None) is None


async def test_the_speaker_list_groups_searches_and_lets_the_dead_in_on_request(presence: ApiWorld) -> None:
    rules = presence.services.rules.current
    core = seeded(presence).core
    async with presence.services.database.write() as session:
        lover = await session.get(EntityRow, core.extra["lover"].id)
        assert lover is not None
        lover.status = EntityStatus.DEAD
        lover.end_epoch = 1
        await foreign_god(session, core)
        living = await speaker_lines(session, rules)
        everyone = await speaker_lines(session, rules, dead=True)
        mortals = await speaker_lines(session, rules, group=SpeakerGroup.MORTALS, dead=True)
        searched = await speaker_lines(session, rules, query="ilva")
    names = [line.name for line in living]
    assert core.son.name in names and "Ombrun" in names and "Ilvane" in names
    assert "Corwen" not in names
    assert "Corwen" in [line.name for line in everyone]
    assert {line.group for line in mortals} == {SpeakerGroup.MORTALS}
    assert [line.name for line in searched] == ["Ilvane"]
    order = [line.group for line in everyone]
    assert order == sorted(order, key=list(SpeakerGroup).index)
