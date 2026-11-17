import re
from pathlib import Path

from claude_agent_sdk import AssistantMessage, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage

from aerona.llm.token_count import ENCODING_FILE, TokenMeter, count_tokens

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "aerona"
MODEL_ENTRY = re.compile(r"from claude_agent_sdk import[^\n]*\b(query|ClaudeSDKClient)\b|claude_agent_sdk\.(query|ClaudeSDKClient)")
METERED_CLIENT = SOURCE_ROOT / "llm" / "client.py"


def test_tokens_are_counted_by_the_bundled_tokenizer() -> None:
    assert ENCODING_FILE.is_file()
    assert count_tokens("") == 0
    assert count_tokens("hello world") == 2
    assert count_tokens("Hello there, the Creator speaks.") == count_tokens("Hello there,") + count_tokens(" the Creator speaks.")
    assert count_tokens('{"accepted": true}') == 5


def test_every_reply_reads_the_whole_context_so_far() -> None:
    meter = TokenMeter("hello world", "hello world")
    meter.read(AssistantMessage(content=[ToolUseBlock(id="t", name="look", input={"at": "sea"})], model="m"))
    meter.read(UserMessage(content=[ToolResultBlock(tool_use_id="t", content="hello world")]))
    meter.read(AssistantMessage(content=[TextBlock(text="hello world")], model="m"))
    first_reply = count_tokens('look\n{"at": "sea"}')
    assert meter.replies == 2
    assert meter.output_tokens == first_reply + 2
    assert meter.input_tokens == 4 + (4 + first_reply + 2)


def test_only_the_metered_client_calls_a_model() -> None:
    sources = [path for path in SOURCE_ROOT.rglob("*.py") if path != METERED_CLIENT]
    callers = sorted(str(path.relative_to(SOURCE_ROOT)) for path in sources if MODEL_ENTRY.search(path.read_text(encoding="utf-8")))
    assert callers == []
    assert MODEL_ENTRY.search(METERED_CLIENT.read_text(encoding="utf-8"))
