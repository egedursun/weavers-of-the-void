import asyncio

from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind


async def test_subscriber_replays_missed_events_then_streams_live() -> None:
    bus = EventBus(replay_size=10)
    bus.publish(EventKind.WORLD_CHANGED, {"n": 1})
    bus.publish(EventKind.WORLD_CHANGED, {"n": 2})
    received: list[int] = []

    async def consume() -> None:
        async for item in bus.subscribe(last_event_id=1):
            received.append(item.payload["n"])
            if len(received) == 2:
                return

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    bus.publish(EventKind.WORLD_CHANGED, {"n": 3})
    await asyncio.wait_for(task, timeout=1)
    assert received == [2, 3]


def test_replay_buffer_is_bounded() -> None:
    bus = EventBus(replay_size=3)
    for index in range(5):
        bus.publish(EventKind.WORLD_CHANGED, {"n": index})
    assert [item.payload["n"] for item in bus.replay_after(0)] == [2, 3, 4]
