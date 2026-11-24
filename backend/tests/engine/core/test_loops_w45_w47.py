from collections.abc import Callable
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.creator_bonds import CreatorStandingRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.divine import WorldAttentionRow
from aerona.db.tables.intrigue import BeliefRow, IdentityRow
from aerona.db.tables.mind import CultureValueRow, MemoryRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.powers import GiftedAttitudeRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import GiftedAttitude, PowerVisibility
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import DiseaseStats, PeopleStats, PolityStats
from aerona.engine.divine.creator import tend_attention
from aerona.engine.gods.queries import creator_row
from aerona.engine.intrigue.far_sources import minds_read
from aerona.engine.intrigue.sources import SourceTally
from aerona.engine.polity.laws import enact, law_param
from aerona.engine.powers.backfill import built_in_source
from aerona.engine.powers.society import attitude_for, keep_apart, registry_pull
from aerona.engine.powers.sources import contend, density_row
from aerona.engine.primitives.queries import connect
from aerona.engine.structures.needs import NEEDS
from aerona.engine.structures.own_effects import tend_quarantine
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at
from tests.engine.core.test_powers_audit_w45 import power_for
from tests.engine.core.test_structure_effects_w47 import build


async def test_users_of_an_overdrawn_land_race_to_draw_and_come_to_resent_each_other(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Leyhollow", world, world.regions[0])
    first = await mortal(session, "Oriel", world, town.id)
    second = await mortal(session, "Tamsin", world, town.id)
    ctx = await at(session, 3)
    ley = await built_in_source(session, MagicSource.LEY)
    land = await density_row(ctx, ley, world.regions[0].id)
    land.density, land.depleted = 10, True
    for user in (first, second):
        power = power_for(user.id, SpellTechnique.CREATE, SpellForm.FIRE)
        power.source_id, power.last_used_epoch = ley.id, 3
        session.add(power)
    await session.flush()
    assert await contend(ctx, land, ley) == 1
    assert land.density < 10
    resented = await session.scalars(
        select(MemoryRow.holder_node_id).where(MemoryRow.kind == MemoryKind.ENVIED, MemoryRow.subject_node_id.in_([first.id, second.id]))
    )
    assert set(resented) == {first.id, second.id}


async def test_the_gifted_who_hide_turn_to_quiet_use(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hushfield", world, world.regions[0])
    realm = await entity(session, "The Watching Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    gifted = await mortal(session, "Brand Ollo", world, town.id)
    power = power_for(gifted.id, SpellTechnique.DESTROY, SpellForm.FIRE, visibility=PowerVisibility.OVERT)
    session.add(power)
    await session.flush()
    ctx = await at(session, 2)
    await enact(ctx, town, LawKind.POWER_LAW, {"level": "hunted", "mind_powers": "banned"})
    assert await keep_apart(ctx) == 1
    assert power.visibility is PowerVisibility.SUBTLE


async def test_the_gifted_living_under_false_names_feed_a_people_s_fear(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "The Wary", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    session.add(CultureValueRow(entity_id=folk.id, axis=ValueAxis.TRADITION, value=30))
    town = await settlement(session, "Shuttered", world, world.regions[0])
    hiders = [await mortal(session, f"Hider {index}", world, town.id) for index in range(8)]
    for hider in hiders:
        session.add(IdentityRow(mortal_node_id=hider.id, false_name="one of no note", reason=IdentityReason.HIDDEN_POWER, since_epoch=1, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    calm = await attitude_for(ctx, folk, set())
    afraid = await attitude_for(ctx, folk, {hider.id for hider in hiders})
    assert calm is GiftedAttitude.ORDINARY
    assert afraid in {GiftedAttitude.FEARED, GiftedAttitude.PERSECUTED}


async def test_a_realm_that_has_registered_most_of_its_gifted_moves_to_conscript_them(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "The Counted", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    town = await settlement(session, "Ledgerford", world, world.regions[0])
    await connect(session, town.id, folk.id, BondKind.DESCENDS_FROM, 1)
    realm = await entity(session, "The Ledger Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    session.add(GiftedAttitudeRow(people_entity_id=folk.id, attitude=GiftedAttitude.REGULATED, registered_share=90, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    await enact(ctx, realm, LawKind.POWER_LAW, {"level": "registered", "mind_powers": "licensed"})
    for epoch in range(2, 60):
        ctx = await at(session, epoch)
        if await registry_pull(ctx):
            break
    assert await law_param(session, realm.id, LawKind.POWER_LAW, "level") == "conscripted"


def test_a_lettered_town_that_writes_wants_a_printing_house_and_an_epidemic_wants_a_quarantine_house() -> None:
    rules = Rules()
    tests: dict[StructureKind, Callable[[Rules, object], bool]] = {}
    for kind, test in NEEDS:
        if kind in {StructureKind.PRINTING_HOUSE, StructureKind.QUARANTINE_HOUSE}:
            tests.setdefault(kind, test)
    lettered = SimpleNamespace(
        knows=lambda _branch: True,
        reaches=lambda _kind: True,
        at_least=lambda _tier: True,
        literacy=rules.construction.press_literacy,
        outbreak=True,
        workshops=set(),
    )
    unlettered = SimpleNamespace(
        knows=lambda _branch: True, reaches=lambda _kind: True, at_least=lambda _tier: True, literacy=0, outbreak=False, workshops=set()
    )
    assert tests[StructureKind.PRINTING_HOUSE](rules, lettered)
    assert not tests[StructureKind.PRINTING_HOUSE](rules, unlettered)
    assert tests[StructureKind.QUARANTINE_HOUSE](rules, lettered)
    assert not tests[StructureKind.QUARANTINE_HOUSE](rules, unlettered)


async def test_a_quarantine_house_falls_out_of_use_once_epidemics_are_forgotten_and_reopens_in_the_next(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fevermoor", world, world.regions[0])
    await build(session, world, town.id, StructureKind.QUARANTINE_HOUSE, level=1)
    house = await session.scalar(select(StructureProfileRow).where(StructureProfileRow.host_entity_id == town.id))
    assert house is not None
    ctx = await at(session, 30)
    await tend_quarantine(ctx, town)
    assert house.condition < PERCENT
    plague = await entity(session, "The Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(
        OutbreakRow(disease_entity_id=plague.id, region_entity_id=world.regions[0].id, path=SpreadPath.ORIGIN, severity=40, started_epoch=31, locked=[])
    )
    await session.flush()
    await tend_quarantine(await at(session, 31), town)
    assert house.condition == PERCENT


async def test_a_world_in_awe_of_the_creator_draws_its_eye(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    if await creator_row(session) is None:
        return
    await tend_attention(ctx)
    row = await session.get(WorldAttentionRow, world.world.id)
    assert row is not None
    before = row.attention
    session.add(CreatorStandingRow(people_entity_id=world.people.id, awe=100, love=0, dread=0, gratitude=0, resentment=0, ignorance=0, locked=["awe"]))
    await session.flush()
    row.attention = before
    await tend_attention(await at(session, 3))
    calm = before * (PERCENT - ctx.rules.creator.attention_decay_pct) / PERCENT
    assert row.attention > calm


async def test_a_mind_reader_reads_the_folk_of_its_own_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stillwater", world, world.regions[0])
    reader = await mortal(session, "Vesh", world, town.id)
    neighbour = await mortal(session, "Orla", world, town.id)
    reading = power_for(reader.id, SpellTechnique.PERCEIVE, SpellForm.MIND)
    session.add(reading)
    await session.flush()
    tally = SourceTally()
    await minds_read(await at(session, 3), tally)
    assert tally.beliefs > 0
    held_beliefs = await session.scalars(select(BeliefRow.subject_node_id).where(BeliefRow.holder_node_id == reader.id))
    assert neighbour.id in set(held_beliefs)
