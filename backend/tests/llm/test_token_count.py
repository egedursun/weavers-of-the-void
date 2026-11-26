from pathlib import Path

from aerona.llm.events import ReplyEnded, TextDelta, ToolCalled, ToolFinished
from aerona.llm.token_count import ENCODING_FILE, TokenMeter, count_tokens

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RETIRED_SDK = "claude_agent_sdk"


def test_tokens_are_counted_by_the_bundled_tokenizer() -> None:
    assert ENCODING_FILE.is_file()
    assert count_tokens("") == 0
    assert count_tokens("hello world") == 2
    assert count_tokens("Hello there, the Creator speaks.") == count_tokens("Hello there,") + count_tokens(" the Creator speaks.")
    assert count_tokens('{"accepted": true}') == 5


def test_every_reply_reads_the_whole_context_so_far() -> None:
    meter = TokenMeter("hello world", "hello world")
    meter.read(ReplyEnded("", ""))
    meter.read(ToolCalled("t", "look", {"at": "sea"}))
    meter.read(ToolFinished("t", "look", "hello world", False))
    meter.read(TextDelta("hello world"))
    meter.read(ReplyEnded("hello world", ""))
    tool_call = count_tokens('look\n{"at": "sea"}')
    assert meter.replies == 2
    assert meter.output_tokens == tool_call + 2
    assert meter.input_tokens == 4 + (4 + tool_call + 2)


def test_thoughts_count_as_output() -> None:
    meter = TokenMeter("hello world")
    meter.read(ReplyEnded("hello world", "hello world"))
    assert meter.output_tokens == count_tokens("hello world\nhello world")


def test_no_code_imports_the_retired_agent_sdk() -> None:
    sources = [path for folder in ("src", "tests") for path in (BACKEND_ROOT / folder).rglob("*.py")]
    importers = sorted(
        str(path.relative_to(BACKEND_ROOT)) for path in sources if path != Path(__file__).resolve() and RETIRED_SDK in path.read_text(encoding="utf-8")
    )
    assert importers == []
