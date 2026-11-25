from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from aerona.constants.llm import HAIKU_MODEL_ID
from aerona.db.tables.divine_will import DivineWillAttachmentRow
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.llm.client import LlmClient
from aerona.llm.content import PROBE_IMAGE, ImagePart
from aerona.llm.stream import StreamActor, StreamReporter
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules
from aerona.rules.registry.server import ServerRules
from tests.api.conftest import ApiWorld
from tests.divine_will.conftest import ask
from tests.divine_will.scripted import Say, ScriptedWill

PICTURE_KEY = "divine_will/tests/picture.png"


class FixedRules:
    def __init__(self) -> None:
        self.current = Rules(model=ModelRules(retry_wait_1=0, retry_wait_2=0, retry_wait_3=0))


def answering(text: str) -> tuple[Any, list[Any]]:
    prompts: list[Any] = []

    async def fake_query(*, prompt: str | AsyncIterable[dict[str, Any]], options: Any) -> AsyncIterator[Any]:
        prompts.append(prompt if isinstance(prompt, str) else [item async for item in prompt])
        yield AssistantMessage(content=[TextBlock(text)], model=HAIKU_MODEL_ID)
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1, session_id="s", result=text)

    return fake_query, prompts


def blocks_of(sent: Any) -> list[dict[str, Any]]:
    assert isinstance(sent, list)
    content: list[dict[str, Any]] = sent[0]["message"]["content"]
    return content


async def test_the_probe_sends_one_picture_once_and_remembers_the_answer() -> None:
    fake_query, prompts = answering("Red.")
    client = LlmClient(FixedRules(), enabled=True, query_function=fake_query)
    first = await client.capabilities()
    second = await client.capabilities()
    assert first.images is True and first.probed is True
    assert second == first
    assert len(prompts) == 1
    assert [block["type"] for block in blocks_of(prompts[0])] == ["text", "image"]


async def test_a_model_that_misreads_the_probe_cannot_see() -> None:
    fake_query, _ = answering("I see nothing.")
    found = await LlmClient(FixedRules(), enabled=True, query_function=fake_query).capabilities()
    assert found.images is False and found.probed is True
    assert found.note


async def test_a_disabled_model_is_not_probed() -> None:
    fake_query, prompts = answering("Red.")
    found = await LlmClient(FixedRules(), enabled=False, query_function=fake_query).capabilities()
    assert found.images is False and found.probed is False
    assert prompts == []


async def test_an_agent_run_streams_pictures_with_the_prompt() -> None:
    fake_query, prompts = answering("Seen.")
    client = LlmClient(FixedRules(), enabled=True, query_function=fake_query)
    run = await client.run_agent("will", "system", "Look at this.", tools=[], images=[ImagePart("image/png", PROBE_IMAGE)])
    assert run.completed
    blocks = blocks_of(prompts[0])
    assert blocks[0] == {"type": "text", "text": "Look at this."}
    assert blocks[1]["source"]["media_type"] == "image/png"
    plain, more = answering("Plain.")
    await LlmClient(FixedRules(), enabled=True, query_function=plain).run_agent("will", "system", "No picture.", tools=[])
    assert more == ["No picture."]


def test_streamed_events_carry_the_channel_of_their_cycle() -> None:
    published: list[tuple[EventKind, dict[str, Any]]] = []
    actor = StreamActor(ActorKind.CREATOR, 1, "Ul", channel="divine_will:7")
    reporter = StreamReporter(lambda kind, payload: published.append((kind, payload)), ServerRules(), actor, "divine_will")
    reporter.feed(AssistantMessage(content=[TextBlock("Thinking aloud.")], model=HAIKU_MODEL_ID))
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
