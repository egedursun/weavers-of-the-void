from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.agent import MessageIntent
from tests.api.conftest import ApiWorld, seeded


async def test_prayers_list_and_answer(api: ApiWorld) -> None:
    world = seeded(api).core
    async with api.services.database.write() as session:
        prayer = MessageRow(epoch=1, sender_node_id=world.son.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="Give me strength.")
        session.add(prayer)
        await session.flush()
        prayer_id = prayer.id
    listed = (await api.http.get("/api/prayers")).json()
    assert [item["message"]["id"] for item in listed] == [prayer_id]
    answered = await api.http.post(f"/api/prayers/{prayer_id}/answer", json={"text": "Endure.", "essence": 0})
    assert answered.status_code == 200, answered.text
    again = await api.http.post(f"/api/prayers/{prayer_id}/answer", json={"text": "Endure.", "essence": 0})
    assert again.status_code == 400
