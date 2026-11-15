import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.write_guard import BOND_DOWNGRADES, chosen_bonds
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from tests.db.factories import make_entity, make_son


async def test_direction_is_normalized_for_typed_bonds(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Ruvan", EntityType.REGION, world_id=world_id)
    people = await make_entity(session, "Askari", EntityType.PEOPLE, location_id=region.id)
    language = await make_entity(session, "Askari Tongue", EntityType.LANGUAGE, world_id=world_id)
    bond = await BondRepository(session).connect(BondDraft(language.id, people.id, BondKind.SPEAKS, 1))
    assert (bond.source_node_id, bond.target_node_id, bond.kind) == (people.id, language.id, BondKind.SPEAKS)


@pytest.mark.bond_downgrade_expected
async def test_invalid_endpoints_are_downgraded_to_related(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Oskar", EntityType.REGION, world_id=world_id)
    tradition = await make_entity(session, "Lantern Night", EntityType.TRADITION, world_id=world_id)
    bond = await BondRepository(session).connect(BondDraft(region.id, tradition.id, BondKind.KNOWS, 1, description="old lore"))
    assert bond.kind is BondKind.RELATED
    assert bond.description == "knows: old lore"


async def test_worship_from_a_god_is_flipped(session: AsyncSession, world_id: int) -> None:
    son = await make_son(session, "Irsen", world_id)
    region = await make_entity(session, "Holm", EntityType.REGION, world_id=world_id)
    people = await make_entity(session, "Holmfolk", EntityType.PEOPLE, location_id=region.id)
    bonds = BondRepository(session)
    bond = await bonds.connect(BondDraft(son.id, people.id, BondKind.WORSHIPS, 1))
    assert (bond.source_node_id, bond.target_node_id) == (people.id, son.id)
    assert await bonds.patron(people.id) == son.id


async def test_state_bonds_are_deduplicated_and_events_are_not(session: AsyncSession, world_id: int) -> None:
    first = await make_entity(session, "Arn", EntityType.REGION, world_id=world_id)
    second = await make_entity(session, "Bel", EntityType.REGION, world_id=world_id)
    bonds = BondRepository(session)
    ally = await bonds.connect(BondDraft(first.id, second.id, BondKind.ALLY, 1, description="old pact"))
    again = await bonds.connect(BondDraft(second.id, first.id, BondKind.ALLY, 2, description="renewed pact"))
    assert again.id == ally.id
    assert ally.description == "renewed pact"
    killed_once = await bonds.connect(BondDraft(first.id, second.id, BondKind.CAUSED, 1))
    killed_twice = await bonds.connect(BondDraft(first.id, second.id, BondKind.CAUSED, 2))
    assert killed_once.id != killed_twice.id


async def test_enmity_breaks_alliance_and_trade(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Corr", EntityType.REGION, world_id=world_id)
    first = await make_entity(session, "Corrfolk", EntityType.PEOPLE, location_id=region.id)
    second = await make_entity(session, "Dunfolk", EntityType.PEOPLE, location_id=region.id)
    bonds = BondRepository(session)
    ally = await bonds.connect(BondDraft(first.id, second.id, BondKind.ALLY, 1))
    trade = await bonds.connect(BondDraft(second.id, first.id, BondKind.TRADES_WITH, 1))
    await bonds.connect(BondDraft(first.id, second.id, BondKind.ENEMY, 2))
    assert ally.state is BondState.PAST
    assert trade.state is BondState.PAST
    assert await bonds.exists_between(second.id, first.id, BondKind.ENEMY)


async def test_a_mortal_ruler_dethrones_other_mortal_rulers(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Throne Vale", EntityType.REGION, world_id=world_id)
    city = await make_entity(session, "Kerrow", EntityType.SETTLEMENT, location_id=region.id)
    old_king = await make_entity(session, "Aldan", EntityType.MORTAL, location_id=city.id)
    new_king = await make_entity(session, "Bevric", EntityType.MORTAL, location_id=city.id)
    faction = await make_entity(session, "Gray Guild", EntityType.FACTION, location_id=city.id)
    bonds = BondRepository(session)
    old_rule = await bonds.connect(BondDraft(old_king.id, city.id, BondKind.RULES, 1))
    guild_rule = await bonds.connect(BondDraft(faction.id, city.id, BondKind.RULES, 1))
    await bonds.connect(BondDraft(new_king.id, city.id, BondKind.RULES, 2))
    assert old_rule.state is BondState.PAST
    assert guild_rule.state is BondState.ACTIVE


async def test_location_bond_follows_moves(session: AsyncSession, world_id: int) -> None:
    north = await make_entity(session, "North Reach", EntityType.REGION, world_id=world_id)
    south = await make_entity(session, "South Reach", EntityType.REGION, world_id=world_id)
    place = await make_entity(session, "Stone Well", EntityType.PLACE, location_id=north.id)
    bonds = BondRepository(session)
    assert await bonds.exists_between(place.id, north.id, BondKind.INSIDE)
    await EntityRepository(session).move(place, south.id, epoch=2)
    assert not await bonds.exists_between(place.id, north.id, BondKind.INSIDE)
    assert await bonds.exists_between(place.id, south.id, BondKind.INSIDE)


async def test_bonds_need_existing_nodes(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Lonely", EntityType.REGION, world_id=world_id)
    with pytest.raises(NotFoundError):
        await BondRepository(session).connect(BondDraft(region.id, 99999, BondKind.RELATED, 1))


async def test_an_entity_has_a_single_patron(session: AsyncSession, world_id: int) -> None:
    first = await make_son(session, "Ilvar", world_id)
    second = await make_son(session, "Juno", world_id)
    region = await make_entity(session, "Patron Vale", EntityType.REGION, world_id=world_id)
    people = await make_entity(session, "Valefolk", EntityType.PEOPLE, location_id=region.id)
    bonds = BondRepository(session)
    old = await bonds.connect(BondDraft(people.id, first.id, BondKind.WORSHIPS, 1))
    await bonds.connect(BondDraft(people.id, second.id, BondKind.WORSHIPS, 2))
    assert old.state is BondState.PAST
    assert await bonds.patron(people.id) == second.id


@pytest.mark.bond_downgrade_expected
async def test_a_downgrade_is_recorded_for_engine_code_and_not_for_a_chosen_bond(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Velm", EntityType.REGION, world_id=world_id)
    tradition = await make_entity(session, "Velm Rite", EntityType.TRADITION, world_id=world_id)
    downgrades = BOND_DOWNGRADES.get()
    assert downgrades is not None
    with chosen_bonds():
        await BondRepository(session).connect(BondDraft(region.id, tradition.id, BondKind.KNOWS, 1))
    assert downgrades == []
    await BondRepository(session).connect(BondDraft(tradition.id, region.id, BondKind.KNOWS, 1))
    assert downgrades == ["knows from tradition to region"]


async def test_realms_and_houses_own_things_works_celebrate_their_subjects_and_sites_are_known(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Teld", EntityType.REGION, world_id=world_id)
    realm = await make_entity(session, "Crown of Teld", EntityType.POLITY, world_id=world_id)
    house = await make_entity(session, "House Teld", EntityType.HOUSE, world_id=world_id)
    item = await make_entity(session, "Teld Standard", EntityType.ITEM, world_id=world_id)
    mortal = await make_entity(session, "Ama", EntityType.MORTAL, location_id=region.id)
    work = await make_entity(session, "Song of Ama", EntityType.ARTWORK, world_id=world_id)
    site = await make_entity(session, "Teld Spring", EntityType.PLACE, location_id=region.id)
    bonds = BondRepository(session)
    made = [
        await bonds.connect(BondDraft(realm.id, item.id, BondKind.OWNS, 1)),
        await bonds.connect(BondDraft(house.id, item.id, BondKind.OWNS, 1)),
        await bonds.connect(BondDraft(work.id, mortal.id, BondKind.CELEBRATES, 1)),
        await bonds.connect(BondDraft(mortal.id, site.id, BondKind.KNOWS, 1)),
    ]
    assert [bond.kind for bond in made] == [BondKind.OWNS, BondKind.OWNS, BondKind.CELEBRATES, BondKind.KNOWS]
