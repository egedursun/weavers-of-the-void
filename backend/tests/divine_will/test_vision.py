from typing import Any

from aerona.db.tables.divine_will import DivineWillAttachmentRow
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.providers import ModelRole
from aerona.events.kinds import EventKind
from aerona.llm.client import LlmClient
from aerona.llm.content import PROBE_IMAGE, ImagePart
from aerona.llm.events import ReplyEnded
from aerona.llm.stream import StreamActor, StreamReporter
from aerona.rules.registry.server import ServerRules
from tests.api.conftest import ApiWorld
from tests.divine_will.conftest import ask
from tests.divine_will.scripted import Say, ScriptedWill
from tests.llm.fakes import FakeBackend, FakeRoutes, FixedRules, route

PICTURE_KEY = "divine_will/tests/picture.png"


def conversing(backend: FakeBackend, sees_images: bool | None) -> FakeRoutes:
    return FakeRoutes({ModelRole.CONVERSATION: [route(backend, sees_images=sees_images)]})


async def test_a_checked_model_that_sees_pictures_is_reported_as_seeing() -> None:
    backend = FakeBackend()
    found = await LlmClient(FixedRules(), enabled=True, routes=conversing(backend, True)).capabilities(ModelRole.CONVERSATION)
    assert found.images is True and found.probed is True
    assert backend.requests == []


async def test_a_model_whose_check_failed_cannot_see() -> None:
    found = await LlmClient(FixedRules(), enabled=True, routes=conversing(FakeBackend(), False)).capabilities(ModelRole.CONVERSATION)
    assert found.images is False and found.probed is True
    assert found.note


async def test_a_disabled_model_is_not_asked() -> None:
    found = await LlmClient(FixedRules(), enabled=False, routes=conversing(FakeBackend(), True)).capabilities(ModelRole.CONVERSATION)
    assert found.images is False and found.probed is False


async def test_an_agent_run_sends_pictures_with_the_prompt() -> None:
    backend = FakeBackend()
    client = LlmClient(FixedRules(), enabled=True, routes=conversing(backend, True))
    run = await client.run_agent("will", "system", "Look at this.", tools=[], images=[ImagePart("image/png", PROBE_IMAGE)], role=ModelRole.CONVERSATION)
    assert run.completed
    assert backend.requests[0].prompt == "Look at this."
    assert [image.media_type for image in backend.requests[0].images] == ["image/png"]
    await client.run_agent("will", "system", "No picture.", tools=[], role=ModelRole.CONVERSATION)
    assert backend.requests[1].images == ()


def test_streamed_events_carry_the_channel_of_their_cycle() -> None:
    published: list[tuple[EventKind, dict[str, Any]]] = []
    actor = StreamActor(ActorKind.CREATOR, 1, "Ul", channel="divine_will:7")
    reporter = StreamReporter(lambda kind, payload: published.append((kind, payload)), ServerRules(), actor, "divine_will")
    reporter.feed(ReplyEnded("Thinking aloud.", ""))
    assert published == [
        (EventKind.AGENT_THOUGHT, {"actor_kind": "creator", "actor_id": 1, "actor_name": "Ul", "channel": "divine_will:7", "text": "Thinking aloud."})
    ]


async def picture(api: ApiWorld) -> int:
    await api.services.application.media.put(PICTURE_KEY, PROBE_IMAGE)
    async with api.services.database.write() as session:
        row = DivineWillAttachmentRow(
            kind=AttachmentKind.IMAGE, filename="picture.png", mime="image/png", size=len(PROBE_IMAGE), media_key=PICTURE_KEY, status=AttachmentStatus.STORED
        )
        session.add(row)
        await session.flush()
        return row.id


async def test_a_picture_reaches_a_model_that_sees(will: ApiWorld, will_model: ScriptedWill) -> None:
    attachment_id = await picture(will)
    will_model.plan([Say("A red square.")])
    cycle = await ask(will, "What is this?", mode="ask_lore", attachment_ids=[attachment_id])
    assert cycle["status"] == "done"
    assert [image.data for image in will_model.seen[0].images] == [PROBE_IMAGE]
    assert cycle["attachments"][0]["seen_by_model"] is True
    assert "picture.png" in will_model.seen[0].prompt
    assert "you cannot see this picture" not in will_model.seen[0].prompt


async def test_a_model_that_cannot_see_is_told_in_words(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.vision = False
    attachment_id = await picture(will)
    will_model.plan([Say("I cannot see it.")])
    cycle = await ask(will, "What is this?", mode="ask_lore", attachment_ids=[attachment_id])
    assert cycle["status"] == "done"
    assert will_model.seen[0].images == []
    assert cycle["attachments"][0]["seen_by_model"] is False
    assert cycle["attachments"][0]["note"]
    notices = [event for event in cycle["events"] if event["kind"] == "notice"]
    assert notices[0]["payload"]["notice"] == "vision_unavailable"
    assert "you cannot see this picture" in will_model.seen[0].prompt
    capabilities = (await will.http.get("/api/divine-will/capabilities")).json()
    assert capabilities["images"] is False


async def test_an_attachment_belongs_to_one_request_only(will: ApiWorld, will_model: ScriptedWill) -> None:
    attachment_id = await picture(will)
    will_model.plan([Say("Seen.")])
    await ask(will, "First look.", mode="ask_lore", attachment_ids=[attachment_id])
    again = await will.http.post("/api/divine-will/cycles", json={"text": "Second look.", "mode": "ask_lore", "attachment_ids": [attachment_id]})
    assert again.status_code == 400
    missing = await will.http.post("/api/divine-will/cycles", json={"text": "Look.", "mode": "ask_lore", "attachment_ids": [999999]})
    assert missing.status_code == 400
