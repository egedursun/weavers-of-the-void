from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, LegendaryQuestRow, ThreadRow
from aerona.domain.enums.chronicle import ChronicleKind, LegendaryQuestKind, LegendaryQuestOutcome, ThreadStatus
from aerona.domain.enums.node import ActorKind
from tests.api.conftest import ApiWorld, seeded


async def test_great_expeditions_report_countdown_and_declarer(api: ApiWorld) -> None:
    assert (await api.http.get("/api/expeditions")).json() == []
    rules = api.services.rules.current
    async with api.services.database.write() as session:
        open_thread = ThreadRow(epoch=1, text="LEGENDARY QUEST", status=ThreadStatus.OPEN)
        closed_thread = ThreadRow(epoch=1, text="Old quest", status=ThreadStatus.CLOSED, closed_epoch=1, closing_text="Done")
        session.add_all([open_thread, closed_thread])
        await session.flush()
        session.add_all(
            [
                LegendaryQuestRow(
                    thread_id=open_thread.id,
                    kind=LegendaryQuestKind.DEAD_STAR,
                    opened_by=ActorKind.FATE,
                    opened_epoch=1,
                    deadline_epoch=1 + rules.beyond.expedition_epochs,
                ),
                LegendaryQuestRow(
                    thread_id=closed_thread.id,
                    kind=LegendaryQuestKind.ARCHIVE,
                    opened_by=ActorKind.CREATOR,
                    opened_epoch=1,
                    deadline_epoch=2,
                    outcome=LegendaryQuestOutcome.COMPLETED,
                ),
            ]
        )
    everything = (await api.http.get("/api/expeditions")).json()
    assert [item["kind"] for item in everything] == ["archive", "dead_star"]
    live = (await api.http.get("/api/expeditions", params={"open_only": True})).json()
    assert len(live) == 1
    assert live[0]["declared_by"] == "fate"
    assert live[0]["epochs_remaining"] == rules.beyond.expedition_epochs
    assert live[0]["name"]


async def test_epoch_star_reports_current_and_history(api: ApiWorld) -> None:
    world = seeded(api).core.world
    view = (await api.http.get("/api/cosmos/epoch-star")).json()
    assert view["history"] == []
    assert view["current"][0]["world_id"] == world.id
    assert view["current"][0]["star"] is None
    async with api.services.database.write() as session:
        line = ChronicleRow(epoch=2, kind=ChronicleKind.SYSTEM, text="Epoch 2 began. Star of the epoch: Sun.", template_key="transition.epoch_began")
        session.add(line)
        await session.flush()
        session.add(ChronicleEntityRow(chronicle_id=line.id, entity_id=seeded(api).core.regions[0].id, position=0))
        stored = await session.get(type(world), world.id)
        assert stored is not None
        stored.epoch_star_entity_id = seeded(api).core.regions[0].id
    view = (await api.http.get("/api/cosmos/epoch-star")).json()
    assert view["current"][0]["star"]["id"] == seeded(api).core.regions[0].id
    assert [(item["epoch"], item["entity_id"]) for item in view["history"]] == [(2, seeded(api).core.regions[0].id)]
