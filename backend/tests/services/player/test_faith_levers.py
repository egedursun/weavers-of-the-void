import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.tables.faith import (
    AfterlifeStratumRow,
    CultDoctrineRow,
    CultHoldingRow,
    CultOfficeRow,
    CultTenetRow,
    HeresyRow,
    PossessionRow,
    RelicRow,
    SpiritProfileRow,
)
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.faith import (
    AfterlifeState,
    ClergyFunction,
    HoldingKind,
    RebirthPath,
    SpiritAlignment,
    StratumKind,
    TenetKind,
)
from aerona.domain.models.entity_stats import LanguageStats
from aerona.domain.models.faith import StratumCriteria
from aerona.services.player import faith
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.engine.faith.factories import faithful, mortal, spirit
from tests.services.player.factories import PlayerWorld, ledger_entries, make_entity

FAITH_LEVERS = (
    "cult:doctrine",
    "cult:reset_doctrine",
    "cult:tenet",
    "cult:office",
    "cult:holding",
    "cult:edit_heresy",
    "cult:undeclare_heresy",
    "relic:edit",
    "relic:remove",
    "soul:raise",
    "soul:edit",
    "soul:reread_deeds",
    "soul:possess",
    "soul:possession",
    "soul:exorcise",
    "afterlife:stratum",
)


def test_every_faith_lever_is_in_the_catalogue() -> None:
    assert [lever for lever in FAITH_LEVERS if lever not in ACTIONS_BY_ID] == []


async def test_doctrine_fields_are_set_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:

    church = await faithful(session, world)
    tongue = await make_entity(session, "Holy Tongue", EntityType.LANGUAGE, world_id=world.world.id, stats=LanguageStats())
    outcast = await mortal(session, world, church.town, "Apostate")
    values = {
        "rebirth_path": "merit",
        "liturgical_language_id": tongue.id,
        "fanaticism": "crusade",
        "excommunicated": [outcast.id],
        "zeal_parts": {"a god's anger": 9},
        "devotion": 30,
    }
    await faith.edit_doctrine(scope, faith.EditDoctrine(cult_id=church.cult.id, values=values))
    row = await session.get(CultDoctrineRow, church.cult.id)
    assert row is not None and row.rebirth_path is RebirthPath.MERIT and row.liturgical_language_id == tongue.id
    assert row.excommunicated == [outcast.id] and set(values) <= set(row.locked)
    assert church.cult.stats.devotion == 30
    await faith.edit_doctrine(scope, faith.EditDoctrine(cult_id=church.cult.id, release=list(values)))
    assert not set(values) & set(row.locked)
    with pytest.raises(ValidationFailedError):
        await faith.edit_doctrine(scope, faith.EditDoctrine(cult_id=church.cult.id, values={"parent_cult_id": church.cult.id}))
    assert await ledger_entries(session)


async def test_a_doctrine_can_be_unwritten_and_taught_anew(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world, tenets=(TenetKind.ASCETICISM,))
    await faith.reset_doctrine(scope, faith.CultTarget(cult_id=church.cult.id))
    assert await session.get(CultDoctrineRow, church.cult.id) is not None
    assert list(await session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == church.cult.id)))


async def test_custom_tenets_ride_on_base_effects(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world)
    await faith.set_tenet(scope, faith.SetTenet(cult_id=church.cult.id, tenet=TenetKind.PILGRIMAGE_DUTY, name="The Long Walk"))
    row = await session.get(CultTenetRow, (church.cult.id, TenetKind.PILGRIMAGE_DUTY))
    assert row is not None and row.name == "The Long Walk"


async def test_offices_are_appointed_held_vacated_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world)
    priest = await mortal(session, world, church.town, "Abbot")
    command = faith.SetOffice(cult_id=church.cult.id, kind=ClergyFunction.ASCETIC, holder_id=priest.id)
    await faith.set_office(scope, command)
    row = await session.scalar(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == church.cult.id))
    assert row is not None and row.holder_entity_id == priest.id and row.locked
    await faith.set_office(scope, faith.SetOffice(cult_id=church.cult.id, kind=ClergyFunction.ASCETIC, locked=False))
    assert not row.locked
    await faith.set_office(scope, faith.SetOffice(cult_id=church.cult.id, kind=ClergyFunction.ASCETIC, vacate=True))
    assert row.holder_entity_id is None and row.locked
    await faith.set_office(scope, faith.SetOffice(cult_id=church.cult.id, kind=ClergyFunction.ASCETIC, remove=True))
    assert await session.scalar(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == church.cult.id)) is None


async def test_holdings_are_granted_and_taken(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world)
    await faith.set_holding(scope, faith.SetHolding(cult_id=church.cult.id, entity_id=church.people.id, kind=HoldingKind.LAND))
    assert await session.get(CultHoldingRow, (church.cult.id, church.people.id)) is not None
    await faith.set_holding(scope, faith.SetHolding(cult_id=church.cult.id, entity_id=church.people.id, remove=True))
    assert await session.get(CultHoldingRow, (church.cult.id, church.people.id)) is None


async def test_relics_and_heresies_are_edited_and_removed(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:

    church = await faithful(session, world)
    saint = await mortal(session, world, church.town, "Saint Eda", dead=True, role=MortalRole.PRIEST)
    await faith.canonise(scope, faith.Canonise(cult_id=church.cult.id, saint_id=saint.id))
    relic = await session.scalar(select(RelicRow).where(RelicRow.saint_entity_id == saint.id))
    assert relic is not None
    await faith.edit_relic(scope, faith.EditRelic(item_id=relic.item_entity_id, values={"sanctity": 90, "pilgrims": 300, "shrine_entity_id": church.town.id}))
    assert relic.sanctity == 90 and relic.pilgrims == 300 and "sanctity" in relic.locked
    await faith.edit_relic(scope, faith.EditRelic(item_id=relic.item_entity_id, release=["sanctity", "pilgrims", "shrine_entity_id"]))
    assert relic.locked == []
    await faith.remove_relic(scope, faith.RelicTarget(item_id=relic.item_entity_id))
    assert await session.get(RelicRow, relic.item_entity_id) is None
    sect = await make_entity(session, "Splinter", EntityType.CULT, world_id=world.world.id, location_id=church.town.id)
    await faith.declare_heresy(scope, faith.DeclareHeresy(heresy_id=sect.id, parent_id=church.cult.id))
    await faith.edit_heresy(scope, faith.EditHeresy(heresy_id=sect.id, values={"distance": 70, "tolerated": True, "suppressed": False}))
    heresy = await session.get(HeresyRow, sect.id)
    assert heresy is not None and heresy.distance == 70 and heresy.tolerated and "distance" in heresy.locked
    await faith.undeclare_heresy(scope, faith.HeresyTarget(heresy_id=sect.id))
    assert await session.get(HeresyRow, sect.id) is None


async def test_souls_are_raised_rewritten_and_released_from_holds(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world)
    dead = await mortal(session, world, church.town, "Raised One", dead=True)
    outcome = await faith.raise_soul(scope, faith.RaiseSoul(mortal_id=dead.id, alignment=SpiritAlignment.GUARDIAN))
    spirit_id = outcome.created_ids[0] if hasattr(outcome, "created_ids") else None
    profile = await session.scalar(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id == dead.id))
    assert profile is not None and profile.alignment is SpiritAlignment.GUARDIAN
    assert spirit_id in {None, profile.spirit_entity_id}
    with pytest.raises(ConflictError):
        await faith.raise_soul(scope, faith.RaiseSoul(mortal_id=dead.id))
    values = {
        "deeds": {"renown": 80, "violence": 5},
        "imprint": {"mercy": -40},
        "traits": ["brave"],
        "rite": "nameless",
        "patron_son_id": church.god.id,
        "seal_strength": 30,
    }
    await faith.edit_spirit(scope, faith.EditSpirit(spirit_id=profile.spirit_entity_id, values=values))
    assert profile.deeds["renown"] == 80 and profile.imprint == {"mercy": -40} and profile.rite is FuneralCustom.NAMELESS
    assert profile.patron_son_id == church.god.id and set(values) <= set(profile.locked)
    await faith.edit_spirit(scope, faith.EditSpirit(spirit_id=profile.spirit_entity_id, release=list(values)))
    assert not set(values) & set(profile.locked)
    await faith.reread_deeds(scope, faith.SpiritTarget(spirit_id=profile.spirit_entity_id))
    assert profile.deeds["renown"] != 80
    with pytest.raises(ValidationFailedError):
        await faith.edit_spirit(scope, faith.EditSpirit(spirit_id=profile.spirit_entity_id, values={"state": "reborn"}))


async def test_possessions_are_set_edited_and_exorcised(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world)
    host = await mortal(session, world, church.town, "Vessel")
    shade = await spirit(session, world, church.town, "Hungry Shade")
    session.add(SpiritProfileRow(spirit_entity_id=shade.id, imprint={"mercy": -90}, traits=[], deeds={}, locked=[]))
    await session.flush()
    await faith.possess(scope, faith.Possess(spirit_id=shade.id, host_id=host.id))
    row = await session.get(PossessionRow, host.id)
    assert row is not None
    await faith.edit_possession(scope, faith.EditPossession(host_id=host.id, values={"stress": 70}))
    assert row.stress == 70 and row.locked == ["stress"]
    await faith.edit_possession(scope, faith.EditPossession(host_id=host.id, release=["stress"]))
    assert row.locked == []
    await faith.exorcise(scope, faith.HostTarget(host_id=host.id))
    assert await session.get(PossessionRow, host.id) is None


async def test_custom_strata_take_typed_rules_links_and_closure(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    church = await faithful(session, world)
    rule = StratumCriteria(priority=5, renown_at_least=70)
    await faith.set_stratum(scope, faith.SetStratum(realm_id=world.region.id, kind=StratumKind.REWARD, name="Hall of Heroes", criteria=rule))
    await faith.set_stratum(scope, faith.SetStratum(realm_id=world.region.id, kind=StratumKind.REWARD, name="Garden of the Meek"))
    rows = list(await session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.kind == StratumKind.REWARD)))
    assert len(rows) == 2
    hall = next(row for row in rows if row.name == "Hall of Heroes")
    assert StratumCriteria.read(hall.criteria) == rule
    await faith.set_stratum(
        scope,
        faith.SetStratum(realm_id=world.region.id, kind=hall.kind, stratum_id=hall.id, son_id=church.god.id, cult_id=church.cult.id, closed=True),
    )
    assert hall.son_id == church.god.id and hall.cult_entity_id == church.cult.id and hall.closed
    await faith.set_stratum(scope, faith.SetStratum(realm_id=world.region.id, kind=hall.kind, stratum_id=hall.id, clear_links=True, closed=False))
    assert hall.son_id is None and not hall.closed
    soul = await spirit(session, world, world.region, "Placed")
    profile = SpiritProfileRow(spirit_entity_id=soul.id, imprint={}, traits=[], deeds={}, locked=[])
    session.add(profile)
    await session.flush()
    await faith.judge_soul(scope, faith.JudgeSoul(spirit_id=soul.id, stratum_id=hall.id))
    assert hall.population == 1 and profile.state is AfterlifeState.IN_REALM
    await faith.set_stratum(scope, faith.SetStratum(realm_id=world.region.id, kind=hall.kind, stratum_id=hall.id, remove=True))
    assert profile.stratum_id is None and profile.state is AfterlifeState.JUDGED
