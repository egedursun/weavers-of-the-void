from collections.abc import AsyncIterator

from aerona.imaging.sse import SseMessage, parse_sse


async def lines(*values: str) -> AsyncIterator[str]:
    for value in values:
        yield value


async def test_parser_joins_data_lines_and_skips_comments() -> None:
    source = lines(": ping", "", "id: 3", "event: step", 'data: {"a":', "data: 1}\r", "", "data: tail")
    messages = [message async for message in parse_sse(source)]
    assert messages == [SseMessage(data='{"a":\n1}', event="step", event_id="3"), SseMessage(data="tail")]
