import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.body import Handedness
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import CalendarSlot, MagicSchool, MagicSource
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import StratumKind
from aerona.domain.enums.geology import UndergroundStratum
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.entity_stats import RiteStats
from aerona.engine.body.book import ensure_body
from aerona.engine.body.digits import backfill_digits
from aerona.engine.context import TickContext
from aerona.engine.economy.deposits import backfill_physics
from aerona.engine.environment.cells import DeepTally, shape_cells
from aerona.engine.faith.backfill import strata_criteria
from aerona.engine.recording.legacy import LegacyTally, restore_folded
from aerona.services.integrity.rite_needs import keep_war_needs
from tests.engine.core.factories import CoreWorld, entity, mortal

PROPERTIES = {
    "hardness": 50,
    "toughness": 50,
    "weight": 50,
    "edge": 10,
    "conductivity": 10,
    "sanctity": 0,
    "corruption": 0,
    "rarity": 20,
    "base_value": 5,
    "decay": 0,
    "created_epoch": 0,
}


async def test_the_physics_backfill_keeps_a_substance_whose_physics_were_chosen(session: AsyncSession, world: CoreWorld) -> None:
    chosen = WorldMaterialRow(world_id=world.world.id, origin=MaterialOrigin.CATALOG, family=MaterialFamily.METAL, melting_point=7, density=93, **PROPERTIES)
    bare = WorldMaterialRow(world_id=world.world.id, origin=MaterialOrigin.CATALOG, family=MaterialFamily.METAL, **PROPERTIES)
    session.add_all([chosen, bare])
    await session.flush()
    assert await backfill_physics(session) == 1
    assert (chosen.melting_point, chosen.density) == (7, 93)
    assert (bare.melting_point, bare.density) != (100, 50)


async def test_the_criteria_backfill_fills_only_strata_without_criteria(ctx: TickContext, world: CoreWorld) -> None:
    shaped = AfterlifeStratumRow(realm_entity_id=world.regions[0].id, kind=StratumKind.REWARD, name="Shaped", criteria={"priority": 7})
    blank = AfterlifeStratumRow(realm_entity_id=world.regions[0].id, kind=StratumKind.COMMON, name="Blank", criteria={})
    ctx.session.add_all([shaped, blank])
    await ctx.session.flush()
    assert await strata_criteria(ctx) == 1
    assert shaped.criteria == {"priority": 7}
    assert blank.criteria


async def test_the_cell_fixup_never_reshapes_a_cell_a_son_made(ctx: TickContext, world: CoreWorld) -> None:
    region = world.regions[0]
    made = RegionStratumRow(region_entity_id=region.id, stratum=UndergroundStratum.AQUIFER, extent=37, light=12, by_node_id=world.son.id, locked=[])
    ctx.session.add(made)
    await ctx.session.flush()
    await shape_cells(ctx, DeepTally())
    assert (made.extent, made.light) == (37, 12)


async def test_a_held_or_explicit_rite_requirement_is_never_turned_to_war(session: AsyncSession, world: CoreWorld) -> None:
    rites = [await entity(session, name, EntityType.RITE, RiteStats(), world_id=world.world.id) for name in ("Calm Rite", "Held Rite", "Open Rite")]
    calm, kept, open_rite = (
        RiteProfileRow(
            rite_entity_id=rite.id,
            school=next(iter(MagicSchool)),
            source=next(iter(MagicSource)),
            requirements={"slot": CalendarSlot.CAMPAIGN.value, **extra},
            locked=locks,
        )
        for rite, extra, locks in zip(rites, ({"war": False}, {}, {}), ([], ["requirements"], []), strict=True)
    )
    session.add_all([calm, kept, open_rite])
    await session.flush()
    assert await keep_war_needs(session) == 1
    assert calm.requirements.get("war") is False
    assert "war" not in kept.requirements
    assert open_rite.requirements.get("war") is True


async def test_the_digit_backfill_keeps_a_chosen_hand(session: AsyncSession, ctx: TickContext, world: CoreWorld) -> None:
    lefty = await mortal(session, "Lefty", world, world.regions[0].id)
    body = await ensure_body(session, ctx.rules, lefty, 1)
    body.handedness = Handedness.LEFT
    await session.flush()
    await backfill_digits(session, ctx.rules)
    assert body.handedness is Handedness.LEFT


async def test_restored_folds_leave_lines_the_god_hid_hidden(session: AsyncSession, world: CoreWorld) -> None:
    hidden = ChronicleRow(epoch=1, kind=ChronicleKind.ENGINE_RAW, visible=False, template_key="births.child", text="A line the god hid.")
    folded = ChronicleRow(epoch=1, kind=ChronicleKind.ENGINE_RAW, visible=False, template_key="births.child", text="A folded line.")
    session.add_all([hidden, folded])
    await session.flush()
    session.add(
        StateChangeRow(
            epoch=1,
            table_name="chronicle",
            row_key=json.dumps({"id": hidden.id}, sort_keys=True),
            operation=LedgerOperation.UPDATE,
            field="visible",
            actor_kind=ActorKind.CREATOR,
        )
    )
    await session.flush()
    await restore_folded(session, LegacyTally())
    assert hidden.visible is False
    assert folded.visible is True
    assert (await session.scalar(select(ChronicleRow.kind).where(ChronicleRow.id == hidden.id))) is not ChronicleKind.ENGINE_RAW
