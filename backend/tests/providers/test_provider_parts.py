import base64
import io
import json
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import AsyncOpenAI
from PIL import Image

from aerona.constants.imaging import PNG_SIGNATURE
from aerona.domain.enums.providers import ModelRole
from aerona.imaging.contract import ImageJobRequest
from aerona.imaging.errors import ImageJobFailedError, ImageWorkerUnavailableError
from aerona.imaging.gateway import ChatImages, GatewayImages, nearest_size
from aerona.llm.backends.openai import OpenAIBackend
from aerona.services.providers.checks import check_model
from aerona.services.providers.secrets import SecretBox, SecretUnreadableError, hint_of, secret_box
from tests.providers.stand_in_model import PICTURE, StandInModel


def client(model: StandInModel) -> AsyncOpenAI:
    return AsyncOpenAI(base_url="http://gateway.test/v1", api_key="k", max_retries=0, http_client=httpx.AsyncClient(transport=model.transport()))


def test_secrets_are_sealed_with_a_private_key_file_and_refuse_another_key(tmp_path: Path) -> None:
    key_file = tmp_path / "secret.key"
    box = secret_box("", key_file)
    sealed = box.seal("sk-very-secret-1234")
    assert "sk-very" not in sealed and box.open(sealed) == "sk-very-secret-1234"
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    assert secret_box("", key_file).open(sealed) == "sk-very-secret-1234"
    with pytest.raises(SecretUnreadableError):
        secret_box("another phrase", tmp_path / "unused.key").open(sealed)
    assert SecretBox(base64.urlsafe_b64encode(bytes(32))).seal("") == ""
    assert hint_of("sk-very-secret-1234") == "1234" and hint_of("short") == ""


async def test_a_check_proves_tools_and_pictures() -> None:
    def reply(body: dict[str, Any]) -> dict[str, Any]:
        if body.get("tools") and not any(message["role"] == "tool" for message in body["messages"]):
            return {"tool_calls": [{"index": 0, "id": "e", "type": "function", "function": {"name": "echo", "arguments": json.dumps({"word": "ready"})}}]}
        return {"content": "red" if isinstance(body["messages"][1]["content"], list) else "done"}

    result = await check_model(OpenAIBackend(client(StandInModel(reply=reply))), "m", ModelRole.CONVERSATION, datetime.now(UTC))
    assert result.tools_work is True and result.sees_images is True and result.note == ""
    silent = await check_model(OpenAIBackend(client(StandInModel(reply=lambda body: {"content": "done"}))), "m", ModelRole.WRITING, datetime.now(UTC))
    assert silent.tools_work is False and silent.sees_images is None and silent.note
    refused = await check_model(OpenAIBackend(client(StandInModel(status=401))), "m", ModelRole.WRITING, datetime.now(UTC))
    assert refused.tools_work is False and "refused" in refused.note


async def test_a_cloud_picture_comes_back_as_png_at_the_nearest_size() -> None:
    model = StandInModel()
    picture = await GatewayImages(client(model), "openai/painter").generate(ImageJobRequest(prompt="a hill", width=720, height=480, steps=4, seed=1))
    assert picture.png.startswith(PNG_SIGNATURE)
    assert model.requests[0]["size"] == "1536x1024" and model.requests[0]["model"] == "openai/painter"
    assert "response_format" not in model.requests[0], "gpt-image models refuse response_format, so every OpenAI picture failed"
    assert nearest_size(720, 720) == (1024, 1024) and nearest_size(480, 720) == (1024, 1536)
    with Image.open(io.BytesIO(picture.png)) as opened:
        assert opened.size == (picture.width, picture.height)


async def test_a_cloud_picture_answered_as_a_link_is_downloaded() -> None:
    model = StandInModel(picture_url="http://pictures.test/drawn.png")
    downloads = httpx.AsyncClient(transport=model.transport())
    picture = await GatewayImages(client(model), "openai/dall-e-3", downloads).generate(
        ImageJobRequest(prompt="a hill", width=1024, height=1024, steps=4, seed=1)
    )
    assert picture.png.startswith(PNG_SIGNATURE)
    assert "http://pictures.test/drawn.png" in model.addresses


def chat_client(answer: dict[str, Any], asked: list[dict[str, Any]]) -> AsyncOpenAI:
    def handle(request: httpx.Request) -> httpx.Response:
        asked.append(json.loads(request.content))
        return httpx.Response(200, json=answer)

    return AsyncOpenAI(
        base_url="http://openrouter.test/api/v1", api_key="k", max_retries=0, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    )


def chat_answer(message: dict[str, Any]) -> dict[str, Any]:
    return {"id": "c", "object": "chat.completion", "created": 1, "model": "m", "choices": [{"index": 0, "finish_reason": "stop", "message": message}]}


async def test_an_openrouter_picture_comes_from_the_chat_reply() -> None:
    asked: list[dict[str, Any]] = []
    drawn = {"role": "assistant", "content": "", "images": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PICTURE}"}}]}
    picture = await ChatImages(chat_client(chat_answer(drawn), asked), "google/gemini-2.5-flash-image").generate(
        ImageJobRequest(prompt="a hill", width=720, height=480, steps=4, seed=1)
    )
    assert picture.png.startswith(PNG_SIGNATURE)
    assert asked[0]["modalities"] == ["image", "text"] and asked[0]["image_config"] == {"aspect_ratio": "3:2"}


async def test_an_openrouter_text_model_fails_as_a_drawer() -> None:
    with pytest.raises(ImageJobFailedError):
        await ChatImages(chat_client(chat_answer({"role": "assistant", "content": "I cannot draw."}), []), "openai/gpt-6-luna").generate(
            ImageJobRequest(prompt="a hill", width=1024, height=1024, steps=4, seed=1)
        )


@pytest.mark.parametrize(("status", "error"), [(400, ImageJobFailedError), (429, ImageWorkerUnavailableError), (503, ImageWorkerUnavailableError)])
async def test_a_refused_cloud_picture_maps_to_the_worker_errors(status: int, error: type[Exception]) -> None:
    with pytest.raises(error):
        await GatewayImages(client(StandInModel(status=status)), "openai/painter").generate(
            ImageJobRequest(prompt="a hill", width=720, height=720, steps=4, seed=1)
        )
