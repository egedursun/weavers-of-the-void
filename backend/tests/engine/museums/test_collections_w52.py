from sqlalchemy import select

from aerona.catalog.life.museums import GARDEN_WILD, PIECE_OF_CLASS, PIECE_PRESTIGE
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.museums.hoards import loot, return_trophies, weigh
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, make, settlement

RULES = Rules()


def test_five_collections_eight_pieces_nine_gardens() -> None:
    assert len(HoardKind) == 5 and len(PieceKind) == 8 and len(GardenKind) == 9
    assert PIECE_OF_CLASS[ItemClass.CROWN] is PieceKind.REGALIA and PIECE_OF_CLASS[ItemClass.BOOK] is PieceKind.MANUSCRIPT
    assert set(PIECE_PRESTIGE) == set(PieceKind) and GARDEN_WILD[GardenKind.MENAGERIE] and not GARDEN_WILD[GardenKind.BOTANIC]


async def test_war_carries_treasures_to_a_trophy_hall_and_peace_returns_them(realm: Realm) -> None:
    victim = await settlement(realm, "Gilded")
    sacker = await settlement(realm, "Iron")
    crown = await make(realm.session, "Old Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(PolityProfileRow(polity_entity_id=crown.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), legitimacy=60))
    hoard = MuseumCollectionRow(keeper_entity_id=victim.id, kind=HoardKind.CABINET, founded_epoch=1, locked=[])
    realm.session.add(hoard)
    await realm.session.flush()
    realm.session.add(MuseumPieceRow(collection_id=hoard.id, kind=PieceKind.ARTIFACT, acquired_epoch=1, locked=[]))
    realm.session.add(MuseumPieceRow(collection_id=hoard.id, kind=PieceKind.REGALIA, polity_entity_id=crown.id, acquired_epoch=1, locked=[]))
    await realm.session.flush()
    ctx = context(realm.session, RULES)
    assert await loot(ctx, victim.id, sacker.id) == 2
    hall = await realm.session.scalar(select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id == sacker.id))
    assert hall is not None and hall.kind is HoardKind.TROPHY_HALL
    kinds = set(await realm.session.scalars(select(MuseumPieceRow.kind).where(MuseumPieceRow.collection_id == hall.id)))
    assert kinds == {PieceKind.TROPHY, PieceKind.REGALIA}
    profile = await realm.session.get(PolityProfileRow, crown.id)
    assert profile is not None and profile.legitimacy == 60 - RULES.museums.regalia_shame
    await weigh(ctx, hall)
    assert hall.prestige == RULES.museums.trophy_prestige + RULES.museums.prestige_per_piece
    assert "collection.trophy_taken" in await chronicle_keys(realm.session)
    assert await return_trophies(ctx, sacker.id, victim.id) == 2
