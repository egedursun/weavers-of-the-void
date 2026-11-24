from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from tests.api.conftest import ApiWorld, seeded


async def test_the_family_endpoint_serves_kin_relations_and_a_drawn_layout(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        mortals = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL).order_by(EntityRow.id).limit(2)))
        parent, child = mortals
        await BondRepository(session).connect(BondDraft(parent.id, child.id, BondKind.PARENT_OF, 1, "born"))
    tree = (await api.http.get(f"/api/mortals/{child.id}/family", params={"up": 2, "down": 1})).json()
    assert tree["root"] == child.id and tree["up"] == 2 and tree["down"] == 1
    relation = {person["id"]: person["relation"] for person in tree["people"]}
    assert relation[child.id] == "This mortal" and relation[parent.id] == "Parent"
    cards = {card["person_id"]: card for card in tree["layout"]["cards"]}
    assert cards[parent.id]["y"] < cards[child.id]["y"]
    assert tree["layout"]["families"][0]["child_ids"] == [child.id]
    hidden = await api.http.get(f"/api/mortals/{child.id}/family", params={"hide": ["godparent_of", "sworn_kin"]})
    assert hidden.status_code == 200
    refused = await api.http.get(f"/api/mortals/{child.id}/family", params={"hide": "parent_of"})
    assert refused.status_code == 400
    town = seeded(api).core.extra["town"]
    assert (await api.http.get(f"/api/mortals/{town.id}/family")).status_code == 404
