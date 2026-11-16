from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.council_order import CouncilProcedureRow, DivineSeatRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.domain.enums.divine import CouncilMotion, CouncilSeat, EscalationStep, VotingRule
from aerona.domain.enums.living import CultivationMethod, Fertility
from aerona.domain.enums.powers import SourceAccess, SourceLocus
from aerona.engine.divine.council_order import LADDER, carried, escalate, procedure_of, regulate
from aerona.engine.divine.motions import Motion
from aerona.engine.divine.rulings import enact, record
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_arcana_w15 import foreign_caster
from tests.engine.core.test_minds_w44 import at

M = CouncilMotion


def procedure(rule: VotingRule, quorum: int = 50) -> CouncilProcedureRow:
    return CouncilProcedureRow(quorum_pct=quorum, voting_rule=rule, creator_veto=True, term_epochs=5, locked=[])


def test_a_motion_carries_by_the_council_rule_and_only_with_a_quorum() -> None:
    split = {1: (1, True), 2: (1, True), 3: (1, False)}
    assert carried(procedure(VotingRule.MAJORITY), split, 3)
    assert not carried(procedure(VotingRule.UNANIMITY), split, 3)
    assert carried(procedure(VotingRule.UNANIMITY), {1: (1, True), 2: (1, True)}, 2)
    weighed = {1: (9, True), 2: (2, False), 3: (2, False)}
    assert carried(procedure(VotingRule.WEIGHTED_BY_STANDING), weighed, 3)
    assert carried(procedure(VotingRule.WEIGHTED_BY_RANK), weighed, 3)
    assert not carried(procedure(VotingRule.MAJORITY), {1: (1, True)}, 10)
    assert not carried(procedure(VotingRule.MAJORITY, quorum=100), split, 4)


async def test_each_breach_climbs_the_ladder(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    son = world.son
    son.fame, son.essence = 50, 50
    ruling = await record(ctx, Motion(M.COSMIC_TRUCE), council_id=None)
    steps = [await escalate(ctx, ruling, son.id) for _ in LADDER]
    assert steps == list(LADDER)
    assert son.fame < 50 and son.essence < 50
    seat = await session.get(DivineSeatRow, son.id)
    assert seat is not None and seat.excluded_until is not None
    assert son.rebel
    assert steps[-1] is EscalationStep.DIVINE_WAR


async def test_every_new_motion_is_carried_out(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    god = await foreign_caster(session, world)
    son = world.son
    son.essence = 50
    source = PowerSourceRow(name="the open well", scope_node_id=world.world.id, drawn_from=SourceLocus.PLACE, access=SourceAccess.BONDED, locked=[])
    line = LivingLineRow(name="the drifting line", method=CultivationMethod.ENGINEERING, fertility=Fertility.STERILE, drift_pct=40, locked=[])
    session.add_all([source, line])
    await session.flush()
    members = [son]

    async def carry(motion: Motion) -> list[str]:
        return await enact(ctx, await record(ctx, motion, council_id=None), members)

    await carry(Motion(M.REASSIGN_WORLD, target_node_id=son.id, world_id=world.world.id))
    assert world.world.patron_son_id == son.id
    assert await carry(Motion(M.OUTLAW_POWER, target_node_id=son.id))
    await carry(Motion(M.OUTLAW_SOURCE, world_id=world.world.id))
    assert source.access is SourceAccess.GRANTED
    await carry(Motion(M.ADMIT_MEMBER, target_node_id=god.id))
    seat = await session.get(DivineSeatRow, god.id)
    assert seat is not None and seat.seat is CouncilSeat.INVITED
    await carry(Motion(M.EXPEL_MEMBER, target_node_id=god.id))
    await session.flush()
    assert await session.get(DivineSeatRow, god.id) is None
    await carry(Motion(M.RECOGNISE_GOD, target_node_id=god.id))
    recognised = await session.get(DivineSeatRow, god.id)
    assert recognised is not None and recognised.seat is CouncilSeat.RECOGNISED
    await carry(Motion(M.ESSENCE_TITHE))
    assert son.essence < 50
    await carry(Motion(M.SET_COUNCIL_RULES, voting_rule=VotingRule.WEIGHTED_BY_RANK))
    assert (await procedure_of(ctx)).voting_rule is VotingRule.WEIGHTED_BY_RANK
    for motion in (M.REGULATE_MADE_MINDS, M.REGULATE_POWERS, M.REGULATE_LIVING_CRAFT):
        assert await carry(Motion(motion))
    await regulate(ctx)
    assert line.drift_pct < 40
