from aerona.db.session import Database
from aerona.db.tables.demography import PeopleCultureRow
from aerona.domain.enums.demography import FuneralCustom, MartialStyle
from tests.tools.factories import seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected


async def test_a_son_shapes_the_customs_of_its_own_people(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    text = await ok(
        toolkit,
        "shape_folk",
        {"people_id": realm.people_id, "martial_style": "shock", "funeral_rite": "sky_burial", "reason": "the tide wants them fierce"},
    )
    assert "ways of Kessar Folk changed" in text
    async with database.read() as session:
        culture = await session.get(PeopleCultureRow, realm.people_id)
        assert culture is not None
        assert culture.martial_style is MartialStyle.SHOCK
        assert culture.funeral_rite is FuneralCustom.SKY_BURIAL
        assert {"martial_style", "funeral_rite"} <= set(culture.locked)
    assert "does not worship you" in await rejected(
        toolkit, "shape_folk", {"people_id": realm.other_people_id, "aesthetic": "ornate", "reason": "a gift of beauty"}
    )
    assert "at least one custom" in await rejected(toolkit, "shape_folk", {"people_id": realm.people_id, "reason": "nothing at all to say"})
