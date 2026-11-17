import base64
import gzip
import hashlib
import json
from functools import cache
from pathlib import Path
from typing import Any

import tiktoken
from claude_agent_sdk import AssistantMessage, SdkMcpTool, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage

ENCODING_NAME = "o200k_base"
ENCODING_FILE = Path(__file__).with_name("encodings") / f"{ENCODING_NAME}.tiktoken.gz"
ENCODING_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
ENCODING_PATTERN = "|".join(
    (
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""\p{N}{1,3}""",
        r""" ?[^\s\p{L}\p{N}]+[\r\n/]*""",
        r"""\s*[\r\n]+""",
        r"""\s+(?!\S)""",
        r"""\s+""",
    )
)
ENCODING_SPECIAL_TOKENS = {"<|endoftext|>": 199999, "<|endofprompt|>": 200018}


@cache
def encoding() -> tiktoken.Encoding:
    contents = gzip.decompress(ENCODING_FILE.read_bytes())
    if hashlib.sha256(contents).hexdigest() != ENCODING_SHA256:
        raise RuntimeError(f"the {ENCODING_NAME} token table at {ENCODING_FILE} is damaged")
    ranks = {base64.b64decode(token): int(rank) for token, rank in (line.split() for line in contents.splitlines() if line)}
    return tiktoken.Encoding(name=ENCODING_NAME, pat_str=ENCODING_PATTERN, mergeable_ranks=ranks, special_tokens=ENCODING_SPECIAL_TOKENS)


def count_tokens(text: str) -> int:
    return len(encoding().encode_ordinary(text)) if text else 0


def as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def tool_text(tool: SdkMcpTool[Any]) -> str:
    return "\n".join((tool.name, tool.description, as_text(tool.input_schema)))


def reply_text(message: AssistantMessage) -> str:
    parts: list[str] = []
    for block in message.content:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, ThinkingBlock):
            parts.append(block.thinking)
        elif isinstance(block, ToolUseBlock):
            parts.append(f"{block.name}\n{as_text(block.input)}")
    return "\n".join(parts)


def returned_text(message: UserMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    return "\n".join(as_text(block.content) if isinstance(block, ToolResultBlock) else as_text(block) for block in message.content)


class TokenMeter:
    def __init__(self, *opening: str) -> None:
        self.context = sum(count_tokens(text) for text in opening)
        self.input_tokens = 0
        self.output_tokens = 0
        self.replies = 0

    def reply(self, text: str) -> None:
        produced = count_tokens(text)
        self.input_tokens += self.context
        self.output_tokens += produced
        self.context += produced
        self.replies += 1

    def returned(self, text: str) -> None:
        self.context += count_tokens(text)

    def read(self, message: object) -> None:
        if isinstance(message, AssistantMessage):
            self.reply(reply_text(message))
        elif isinstance(message, UserMessage):
            self.returned(returned_text(message))
