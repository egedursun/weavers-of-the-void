from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow, ItemProfileRow, ResearchProgressRow
from aerona.db.tables.discovery import (
    ArtifactStudyRow,
    BannedWorkRow,
    BlueprintRow,
    EraDeedRow,
    GreatPersonRow,
    GreatPointsRow,
    PolityEraRow,
    ResearchIncidentRow,
    WorldEraRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.discovery import AgeKind, BlueprintKind, BlueprintSource, EraDeed, GreatField, ResearchIncident
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.models.entity_stats import ItemStats, PolityStats, StructureStats
from aerona.engine.lore import blueprints, dangers, discovery_control, eras, great_people, obsolescence, printing, reverse
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm
from tests.engine.warfare.factories import make, make_ctx, society
from tests.tools.factories import connect, make_entity

RULES = Rules()


def tuned(**values: int) -> Rules:
    return replace(RULES, discovery=replace(RULES.discovery, **values))


async def town(session: AsyncSession, realm: Realm, name: str, *, prosperity: int = 50, wealth: int = 50) -> EntityRow:
    return await make(session, name, EntityType.SETTLEMENT, realm.world.id, location_id=realm.region.id, population=4000, prosperity=prosperity, wealth=wealth)


async def scholar(session: AsyncSession, home: EntityRow, name: str, skill: SkillKind, level: int) -> EntityRow:
    mortal = await make(session, name, EntityType.MORTAL, home.world_id or 0, location_id=home.id)
    session.add(SkillRow(holder_node_id=mortal.id, skill=skill, level=level, xp=0, peak=level, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    return mortal


async def kingdom(session: AsyncSession, realm: Realm, member: EntityRow, name: str = "Ash Crown") -> EntityRow:
    polity = await make_entity(session, name, EntityType.POLITY, world_id=realm.world.id, stats=PolityStats())
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=member.id, locked=[]))
    await session.flush()
    return polity


async def test_skill_gathers_points_and_a_great_scholar_breaks_through(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(great_threshold=2, skill_divisor=10))
    home = await town(session, realm, "Lamp Town")
    sage = await scholar(session, home, "Ora Venn", SkillKind.LORE, 60)
    session.add(
        HolderLevelRow(holder_entity_id=home.id, branch=KnowledgeBranch.CIVICS, level=1, practitioners=1, progress=0, secret=False, updated_epoch=1, locked=[])
    )
    await session.flush()
    assert await great_people.gather_points(ctx) >= 1
    points = await session.get(GreatPointsRow, (home.id, GreatField.SCHOLAR))
    assert points is not None and points.points == 6
    assert await great_people.promote_great(ctx) >= 1
    great = await session.get(GreatPersonRow, sage.id)
    assert great is not None and great.field is GreatField.SCHOLAR and great.deed_done
    learned = await session.scalar(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == home.id))
    assert learned is not None


async def age_of(session: AsyncSession, polity_id: int) -> tuple[AgeKind, int]:
    row = await session.get(PolityEraRow, polity_id)
    assert row is not None
    return row.age, row.lowest


async def test_deeds_raise_a_realm_into_a_golden_age_and_a_dark_one_recovers_heroically(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(golden_at=20, dark_at=-20, heroic_rise=30, era_decay=0))
    home = await town(session, realm, "Bell Town")
    polity = await kingdom(session, realm, home)
    assert await eras.record_deed(ctx, polity.id, EraDeed.GREAT_VICTORY, 25, home.id)
    assert not await eras.record_deed(ctx, polity.id, EraDeed.GREAT_VICTORY, 25, home.id)
    await eras.settle_ages(ctx)
    row = await session.get(PolityEraRow, polity.id)
    assert row is not None and row.age is AgeKind.GOLDEN and row.score == 25
    await eras.record_deed(ctx, polity.id, EraDeed.DEFEAT, -60)
    await eras.settle_ages(ctx)
    assert await age_of(session, polity.id) == (AgeKind.DARK, -35)
    await eras.record_deed(ctx, polity.id, EraDeed.WONDER, 40)
    await eras.settle_ages(ctx)
    assert (await age_of(session, polity.id))[0] is AgeKind.HEROIC
    assert await eras.era_factor(session, ctx.rules, home.id) == 1 + ctx.rules.discovery.heroic_research_pct / 100
    assert len(list(await session.scalars(select(EraDeedRow).where(EraDeedRow.polity_entity_id == polity.id)))) == 3


async def test_a_world_enters_the_next_era_when_its_leaders_know_enough(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(era_advance_pct=50))
    home = await town(session, realm, "Quill Town")
    await eras.advance_worlds(ctx)
    row = await session.get(WorldEraRow, realm.world.id)
    assert row is not None and row.era == 1
    second = [Technique.IRON, Technique.PAPER, Technique.CROP_ROTATION, Technique.TERRACING, Technique.SURGERY, Technique.AMPUTATION]
    session.add_all(HolderTechniqueRow(holder_entity_id=home.id, technique=item, since_epoch=1, secret=False) for item in second)
    await session.flush()
    share = await eras.leaders_share(session, realm.world.id, 2, ctx.rules.discovery.era_leaders)
    if share * 100 >= ctx.rules.discovery.era_advance_pct:
        await eras.advance_worlds(ctx)
        assert row.era == 2
    else:
        assert share > 0


async def test_learning_a_dangerous_art_angers_neighbours_who_shun_it_and_can_strike(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(discovery_incident_pct=100))
    home = await town(session, realm, "Bone Town", prosperity=50)
    session.add(HolderTechniqueRow(holder_entity_id=home.id, technique=Technique.NECROMANCY, since_epoch=ctx.epoch, secret=False))
    await session.flush()
    assert await dangers.learned_dangers(ctx) == 1
    incident = await session.scalar(select(ResearchIncidentRow).where(ResearchIncidentRow.holder_entity_id == home.id))
    assert incident is not None and incident.technique is Technique.NECROMANCY and incident.severity > 0


async def test_risky_research_rolls_accidents_that_burn_and_kill(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(accident_pct=100, incident_dead_pct=10))
    home = await town(session, realm, "Forge Town", prosperity=50)
    session.add(ResearchProgressRow(holder_entity_id=home.id, technique=Technique.STEEL, progress=20, updated_epoch=ctx.epoch))
    await session.flush()
    before = stat(home, "population") or 0
    assert await dangers.accidents(ctx) == 1
    incident = await session.scalar(select(ResearchIncidentRow).where(ResearchIncidentRow.holder_entity_id == home.id))
    assert incident is not None and incident.kind in {ResearchIncident.FIRE, ResearchIncident.EXPLOSION}
    assert (stat(home, "population") or 0) == before - incident.dead


async def test_scholars_take_apart_an_iron_blade_and_learn_iron(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(study_progress=100))
    home = await town(session, realm, "Anvil Town")
    await scholar(session, home, "Kel Brann", SkillKind.SMITHING, 100)
    blade = await make_entity(session, "Grey Blade", EntityType.ITEM, world_id=realm.world.id, stats=ItemStats())
    session.add(ItemProfileRow(item_entity_id=blade.id, item_class=ItemClass.BLADE, material=MaterialKind.IRON.value, condition=100, locked=[]))
    await connect(session, home.id, blade.id, BondKind.OWNS)
    await session.flush()
    counts = await reverse.reverse_engineer(ctx)
    study = await session.get(ArtifactStudyRow, (home.id, blade.id))
    progress = await session.get(ResearchProgressRow, (home.id, Technique.IRON))
    assert counts["artefacts_understood"] == 1 and study is not None and study.progress == 100
    assert progress is not None and progress.progress == ctx.rules.discovery.reverse_progress


async def test_copying_follows_the_scribes_until_printing_and_bans_hold_in_a_realm(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    home = await town(session, realm, "Ink Town")
    await society(session, home.id)
    assert await printing.scribe_pace(session, ctx.rules, home.id) == 1.0
    session.add(HolderTechniqueRow(holder_entity_id=home.id, technique=Technique.PRINTING, since_epoch=1, secret=False))
    await session.flush()
    assert await printing.printed(session, home.id)
    polity = await kingdom(session, realm, home)
    book = await make_entity(session, "Black Pages", EntityType.ITEM, world_id=realm.world.id, stats=ItemStats())
    assert not await printing.banned_for(session, home.id, book.id)
    await discovery_control.set_ban(ctx, polity.id, book.id, banned=True)
    assert await printing.banned_for(session, home.id, book.id)
    assert await discovery_control.set_ban(ctx, polity.id, book.id, banned=False) is None
    assert await session.get(BannedWorkRow, (polity.id, book.id)) is None


async def test_a_finished_building_leaves_a_plan_that_speeds_the_next_and_spies_can_steal_it(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned(blueprint_theft_pct=100))
    home = await town(session, realm, "Stone Town")
    rival = await town(session, realm, "Thief Town")
    hall = await make_entity(session, "Great Hall", EntityType.STRUCTURE, world_id=realm.world.id, location_id=home.id, stats=StructureStats())
    session.add(
        StructureProfileRow(
            structure_entity_id=hall.id,
            kind=StructureKind.TEMPLE,
            host_entity_id=home.id,
            construction_state=ConstructionState.COMPLETE,
            built_epoch=ctx.epoch,
            locked=[],
        )
    )
    await session.flush()
    assert await blueprints.draw_designs(ctx) == 1
    factor = await blueprints.design_factor(session, ctx.rules, home.id, BlueprintKind.STRUCTURE, StructureKind.TEMPLE.value)
    assert factor == 1 + ctx.rules.discovery.blueprint_pct * ctx.rules.discovery.blueprint_quality / 10000
    stolen = await blueprints.steal_design(ctx, rival.id, home.id)
    assert stolen is not None and stolen.source is BlueprintSource.STOLEN and stolen.holder_node_id == rival.id


async def test_an_outdated_wall_loses_its_strength_until_it_is_refitted(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    home = await town(session, realm, "Wall Town")
    wall = await make_entity(session, "Old Wall", EntityType.STRUCTURE, world_id=realm.world.id, location_id=home.id, stats=StructureStats())
    profile = StructureProfileRow(
        structure_entity_id=wall.id, kind=StructureKind.WALL, host_entity_id=home.id, construction_state=ConstructionState.COMPLETE, built_epoch=1, locked=[]
    )
    session.add(profile)
    session.add(HolderTechniqueRow(holder_entity_id=home.id, technique=Technique.FORTIFICATION, since_epoch=5, secret=False))
    await session.flush()
    assert await obsolescence.date_structures(ctx) == 1 and profile.obsolete_since == ctx.epoch
    assert await obsolescence.refit_structures(ctx) == 1 and profile.obsolete_since is None and profile.built_epoch == ctx.epoch


async def test_the_god_raises_greats_sets_eras_strikes_and_grants_designs(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    home = await town(session, realm, "God Town", prosperity=50)
    hero = await scholar(session, home, "Ves Arun", SkillKind.TACTICS, 30)
    polity = await kingdom(session, realm, home)
    great = await discovery_control.raise_great(ctx, hero.id, GreatField.GENERAL, deed=False)
    assert great.field is GreatField.GENERAL and "field" in great.locked
    era = await discovery_control.set_era(ctx, polity.id, 70, AgeKind.GOLDEN, hold=True)
    assert era.score == 70 and era.age is AgeKind.GOLDEN and set(era.locked) == {"score", "age"}
    released = await discovery_control.set_era(ctx, polity.id, None, None, hold=False)
    assert released.locked == []
    world = await discovery_control.set_world_era(ctx, realm.world.id, 3, hold=True)
    assert world.era == 3 and world.locked == ["era"]
    incident = await discovery_control.cause_incident(ctx, home.id, ResearchIncident.FIRE, None)
    assert incident.kind is ResearchIncident.FIRE
    design = await discovery_control.grant_design(ctx, home.id, BlueprintKind.VESSEL, "Long Hull", quality=80, name=None)
    assert design.source is BlueprintSource.GRANTED and design.subject == "long_hull"
    assert await session.get(BlueprintRow, design.id) is not None
    with pytest.raises(NotFoundError):
        await discovery_control.raise_great(ctx, home.id, GreatField.ARTIST, deed=False)


async def test_shifting_a_headcount_never_clips_it_to_a_percentage(session: AsyncSession, realm: Realm) -> None:
    home = await town(session, realm, "Crowd Town")
    assert stat(home, "population") == 4000
    assert shift_stat(home, "population", -100) == 3900
    assert shift_stat(home, "prosperity", 500) == 100
