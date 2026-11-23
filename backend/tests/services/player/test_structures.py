from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_undo import UndoRun
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.demography import CohortRow, LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import ConstructionRow, StructureDesignRow, StructureProfileRow, StructureStaffRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job, SexKind
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import ConstructionState, ConstructionStatus, StructureKind
from aerona.domain.models.entity_stats import SettlementStats
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import structures
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def town(session: AsyncSession, world: PlayerWorld) -> EntityRow:
    created = await EntityRepository(session).create(
        EntityDraft(
            name="Ashford",
            entity_type=EntityType.SETTLEMENT,
            description="A town.",
            stats=SettlementStats(population=6000, prosperity=70, defense=30, piety=60),
            power_level=3,
            origin=EntityOrigin.SON,
            birth_epoch=1,
            world_id=world.world.id,
            location_id=world.region.id,
            split_title=False,
        )
    )
    session.add(SettlementProfileRow(settlement_entity_id=created.id, size_tier=SizeTier.TOWN, treasury=50000, locked=[], foreigners={}))
    session.add(
        CohortRow(
            community_entity_id=created.id,
            age_band=AgeBand.ADULT,
            sex_kind=SexKind.BEGETTER,
            social_class=SocialClass.PRIEST,
            condition=CohortCondition.NONE,
            count=300,
            generation_epoch=0,
        )
    )
    session.add(LabourRow(community_entity_id=created.id, job=Job.BUILDING, workers=200, output_pct=100, epoch=1))
    await session.flush()
    return created


async def commissioned(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, kind: StructureKind = StructureKind.TEMPLE) -> int:
    site = await town(session, world)
    effect = await structures.commission(scope, structures.Commission(site_id=site.id, kind=kind, material="stone"))
    assert effect.target_node_id is not None
    return effect.target_node_id


async def undo(session: AsyncSession, world: PlayerWorld, entry_id: int | None) -> None:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == []


async def test_commissioning_begins_a_construction_that_can_be_funded_and_finished(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    structure_id = await commissioned(scope, session, world)
    profile = await session.get(StructureProfileRow, structure_id)
    assert profile is not None and profile.construction_state is ConstructionState.BUILDING
    await structures.fund(scope, structures.Fund(structure_id=structure_id, amount=500))
    row = await session.scalar(select(ConstructionRow).where(ConstructionRow.structure_entity_id == structure_id))
    assert row is not None and row.funds == 500
    essence = world.creator.essence
    await structures.finish(scope, structures.StructureTarget(structure_id=structure_id))
    assert profile.construction_state is ConstructionState.COMPLETE and row.status is ConstructionStatus.FINISHED
    assert world.creator.essence == essence - scope.rules.construction.finish_cost
    assert profile.effect_pct > 0


async def test_commissioning_is_undone_with_its_work(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    site = await town(session, world)
    outcome = await structures.commission(scope, structures.Commission(site_id=site.id, kind=StructureKind.SHRINE))
    assert outcome.target_node_id is not None
    await undo(session, world, outcome.ledger_entry_id)
    session.expire_all()
    assert await session.get(StructureProfileRow, outcome.target_node_id) is None


async def test_edits_are_held_released_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    structure_id = await commissioned(scope, session, world)
    await structures.finish(scope, structures.StructureTarget(structure_id=structure_id))
    profile = await session.get(StructureProfileRow, structure_id)
    assert profile is not None
    before = profile.condition
    outcome = await structures.edit(scope, structures.EditStructure(structure_id=structure_id, values={"condition": 33, "anchor": True}))
    assert profile.condition == 33 and profile.anchor and {"condition", "anchor"} <= set(profile.locked)
    await undo(session, world, outcome.ledger_entry_id)
    await session.refresh(profile)
    assert profile.condition == before and "condition" not in profile.locked
    await structures.edit(scope, structures.EditStructure(structure_id=structure_id, values={"level": 3}))
    assert profile.level == 3 and "level" in profile.locked
    await structures.edit(scope, structures.EditStructure(structure_id=structure_id, release=["level"]))
    assert "level" not in profile.locked


async def test_staff_damage_repair_and_abandonment(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    structure_id = await commissioned(scope, session, world)
    await structures.finish(scope, structures.StructureTarget(structure_id=structure_id))
    await structures.staff(scope, structures.Staff(structure_id=structure_id, allocated=1, hold=True))
    staff = await session.scalar(select(StructureStaffRow).where(StructureStaffRow.structure_entity_id == structure_id))
    profile = await session.get(StructureProfileRow, structure_id)
    assert staff is not None and staff.held and staff.allocated == 1 and profile is not None and profile.staff_pct < 100
    await structures.staff(scope, structures.Staff(structure_id=structure_id, hold=False))
    assert not staff.held and profile.staff_pct == 100
    before = profile.condition
    await structures.damage(scope, structures.Damage(structure_id=structure_id, amount=30))
    assert profile.condition == before - 30
    await structures.repair(scope, structures.StructureTarget(structure_id=structure_id))
    assert profile.condition == before
    other = await structures.commission(scope, structures.Commission(site_id=profile.host_entity_id or 0, kind=StructureKind.SHRINE))
    assert other.target_node_id is not None
    await structures.abandon(scope, structures.Abandon(structure_id=other.target_node_id))
    abandoned = await session.get(StructureProfileRow, other.target_node_id)
    assert abandoned is not None and abandoned.construction_state is ConstructionState.RUINED


async def test_designs_are_created_edited_held_and_retired(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    created = await structures.create_design(
        scope, structures.CreateDesign(world_id=world.world.id, values={"name": "Sun Granary", "base_kind": "granary", "capacity_pct": 250})
    )
    design = await session.scalar(select(StructureDesignRow))
    assert design is not None and created.values["design_id"] == design.id and design.capacity_pct == 250
    await structures.edit_design(scope, structures.EditDesign(design_id=design.id, values={"function_pct": 140, "staff_class": "farmer"}))
    assert design.function_pct == 140 and {"function_pct", "staff_class"} <= set(design.locked)
    await structures.edit_design(scope, structures.EditDesign(design_id=design.id, release=["function_pct"]))
    assert "function_pct" not in design.locked
    site = await town(session, world)
    built = await structures.commission(scope, structures.Commission(site_id=site.id, kind=StructureKind.GRANARY, design_id=design.id))
    profile = await session.get(StructureProfileRow, built.target_node_id)
    assert profile is not None and profile.design_id == design.id
    await structures.retire_design(scope, structures.RetireDesign(design_id=design.id))
    assert design.retired
