from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.sacred import SACRAMENT_COSTS, VISIONS
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.faith import CultOfficeRow
from aerona.db.tables.folkways import PurityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.sacred import SacramentRow, VisionRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.ages import SeasonSpell
from aerona.domain.enums.faith import ClergyFunction
from aerona.domain.enums.folkways import PurityState
from aerona.domain.enums.sacred import SacramentKind, TheodicyCause, VisionKind
from aerona.engine.body.afflictions import afflict
from aerona.engine.sacred.guards import curse_ward
from aerona.engine.sacred.mysteries import MysteryTally, become_mystic, see_vision, suffering_of
from aerona.engine.sacred.rites import RiteTally, keep_sacraments
from tests.engine.core.factories import CoreWorld, mortal, settlement
from tests.engine.core.test_sacred_w25 import at, church, society

QUIET = {kind.value + "_weight": 0 for kind in VisionKind}


async def test_a_vision_comes_by_the_weights_of_its_kinds_and_a_public_oracle_draws_more_followers(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hallowmere", world, world.regions[0])
    dreamer = await mortal(session, "Sera", world, town.id)
    ctx = await at(session, 3, mystics=QUIET | {"dream_weight": 100})
    row = await become_mystic(ctx, dreamer, None, MysteryTally())
    seen = await session.scalar(select(VisionRow).where(VisionRow.mystic_entity_id == dreamer.id))
    assert seen is not None and seen.kind is VisionKind.DREAM and VISIONS[seen.kind].asleep
    told = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "mystic.vision"))
    assert told is not None
    quiet = await mortal(session, "Tamsin", world, town.id)
    quiet_row = await become_mystic(ctx, quiet, None, MysteryTally())
    before, quiet_before = row.followers, quiet_row.followers
    await see_vision(ctx, row, dreamer, None, MysteryTally(), chosen=VisionKind.ORACLE_SPEECH)
    await see_vision(ctx, quiet_row, quiet, None, MysteryTally(), chosen=VisionKind.VISION)
    assert row.followers - before > quiet_row.followers - quiet_before


async def test_a_long_season_that_grinds_on_tests_the_faith_of_its_world(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Frostholm", world, world.regions[0])
    session.add(society(town.id, 5000))
    session.add(IrregularSeasonRow(world_id=world.world.id, spell=SeasonSpell.WINTER, spell_started_epoch=1, spell_length=6, locked=[]))
    await session.flush()
    ctx = await at(session, 5, theodicy={"long_season_years": 50})
    suffering, cause = await suffering_of(ctx, town, (set(), set(), set()))
    assert cause is TheodicyCause.LONG_SEASON and suffering == ctx.rules.theodicy.long_season_suffering


async def test_purification_cleanses_ordination_binds_and_a_curse_sacrament_turns_curses_aside(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brightwater", world, world.regions[0])
    session.add(society(town.id, 5000))
    cult = await church(session, world, town)
    priest = await mortal(session, "Anselm", world, town.id)
    stained = await mortal(session, "Wren", world, town.id)
    session.add(CultOfficeRow(cult_entity_id=cult.id, kind=ClergyFunction.CELEBRANT, holder_entity_id=priest.id))
    session.add(PurityRow(holder_node_id=stained.id, state=PurityState.IMPURE, locked=[]))
    await session.flush()
    ctx = await at(session, 3, sacraments={"coverage": 100, "hardship_pct": 0, "strength": 100, "curse_ward_pct": 100})
    await keep_sacraments(ctx, RiteTally())
    purity = await session.get(PurityRow, stained.id)
    assert purity is not None and purity.state is PurityState.PURE
    ordained = await session.scalar(select(SacramentRow).where(SacramentRow.mortal_entity_id == priest.id, SacramentRow.kind == SacramentKind.ORDINATION))
    assert ordained is not None and not ordained.missed
    assert SACRAMENT_COSTS[SacramentKind.ORDINATION](ctx.rules) == ctx.rules.sacraments.ordination_cost
    assert await curse_ward(ctx, stained.id) == 100
    assert await afflict(ctx, stained, PackageKind.FORTUNE, Transmission.CURSE) is None
    assert await session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == stained.id)) is None
