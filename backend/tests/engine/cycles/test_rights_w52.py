import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.market_kinds import WAYS
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.crafts import IncorporealRightRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.relations import ContestRow
from aerona.domain.enums.crafts import RightAcquired, RightKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.relations import ContestEnd, ContestKind, ContestStake
from aerona.engine.crafts.control import claim_right
from aerona.engine.crafts.rights import wed_portion, win_right
from aerona.engine.recording.render import render_incident
from aerona.services.integrity.market_links import unbound_rights
from tests.engine.core.factories import CoreWorld, mortal
from tests.engine.core.test_cycles_w21 import context, town_of

FIRST = next(iter(Technique))


def test_won_and_wed_rights_name_their_source() -> None:
    assert set(WAYS) == set(RightAcquired)
    assert WAYS[RightAcquired.WON].needs_contest and WAYS[RightAcquired.WED].needs_union


async def test_a_technique_right_names_a_technique_its_holder_knows(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    smith = await mortal(session, "Smith", world, town.id)
    ctx = await context(session)
    with pytest.raises(ValidationFailedError):
        await claim_right(ctx, smith.id, RightKind.TECHNIQUE, "The Way", technique=FIRST)
    session.add(HolderTechniqueRow(holder_entity_id=smith.id, technique=FIRST, since_epoch=1))
    await session.flush()
    row = await claim_right(ctx, smith.id, RightKind.TECHNIQUE, "The Way", technique=FIRST)
    assert row.technique is FIRST and row.acquired is RightAcquired.CREATED


async def test_rights_pass_with_a_union_and_a_won_contest_and_must_name_them(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    first = await mortal(session, "First", world, town.id)
    second = await mortal(session, "Second", world, town.id)
    song = IncorporealRightRow(holder_node_id=first.id, kind=RightKind.SONG, name="The Air", subject_node_id=town.id, since_epoch=1, locked=[])
    union = MarriageRow(first_id=first.id, second_id=second.id, start_epoch=1)
    session.add_all([song, union])
    await session.flush()
    contest = ContestRow(
        kind=next(iter(ContestKind)),
        stake=next(iter(ContestStake)),
        challenger_node_id=first.id,
        defender_node_id=second.id,
        stake_node_id=town.id,
        outcome=ContestEnd.CHALLENGER,
        epoch=1,
    )
    session.add(contest)
    await session.flush()
    ctx = await context(session, rights={"wed_pct": 100})
    assert await wed_portion(ctx, first.id, second.id, union.id) is song
    assert song.holder_node_id == second.id and song.acquired is RightAcquired.WED and song.marriage_id == union.id
    won = await win_right(ctx, contest.id, town.id, first.id, second.id)
    assert won is song and won.contest_id == contest.id
    assert (await session.get(IncorporealRightRow, song.id)) is song and str(song.acquired) == RightAcquired.WON.value
    song.contest_id = None
    await session.flush()
    assert song.id in await unbound_rights(session)


def test_a_right_used_without_leave_is_told_with_its_kind() -> None:
    line = render_incident(
        INCIDENT_KINDS["rights.infringed"],
        {IncidentRole.ACTOR: ["Fonju"], IncidentRole.VICTIM: ["House Anrar"]},
        {"right": "House Anrar", "kind": RightKind.NAME, "opinion": -10},
    )
    assert line.startswith("Fonju used the name House Anrar without the leave of")
