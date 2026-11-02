import pytest

from aerona_image_worker.backends.base import BackendSpec
from aerona_image_worker.domain.enums import BackendName, EventKind
from aerona_image_worker.domain.generation import GenerationRequest
from aerona_image_worker.errors import GenerationFailedError, ImageTimeoutError, LoadTimeoutError
from aerona_image_worker.runtime.process import ProcessRunner

REQUEST = GenerationRequest(prompt="an orchard at dusk", width=256, height=256, steps=2, seed=3)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


async def test_process_runner_generates_in_a_child_process_and_unloads() -> None:
    runner = ProcessRunner(BackendSpec(name=BackendName.FAKE, model_id="fake"))
    progress: list[tuple[EventKind, int, int]] = []
    try:
        await runner.ensure_loaded(30.0)
        assert runner.loaded
        image = await runner.generate(REQUEST, 30.0, lambda kind, step, total: progress.append((kind, step, total)))
    finally:
        await runner.unload()
    assert image.startswith(PNG_SIGNATURE)
    assert [kind for kind, _step, _total in progress] == [EventKind.ENCODING, EventKind.STEP, EventKind.STEP, EventKind.DECODING]
    assert not runner.loaded


async def test_process_runner_kills_the_child_on_image_timeout_and_reloads() -> None:
    runner = ProcessRunner(BackendSpec(name=BackendName.FAKE, model_id="fake", fake_step_seconds=5.0))
    try:
        await runner.ensure_loaded(30.0)
        with pytest.raises(ImageTimeoutError):
            await runner.generate(REQUEST, 0.3, lambda _kind, _step, _total: None)
        assert not runner.loaded
        await runner.ensure_loaded(30.0)
        assert runner.loaded
    finally:
        await runner.unload()


async def test_process_runner_reports_load_timeout_and_generation_failure() -> None:
    slow = ProcessRunner(BackendSpec(name=BackendName.FAKE, model_id="fake", fake_load_seconds=5.0))
    with pytest.raises(LoadTimeoutError):
        await slow.ensure_loaded(0.3)
    assert not slow.loaded
    refusing = ProcessRunner(BackendSpec(name=BackendName.FAKE, model_id="fake", fake_failure_prompt="orchard"))
    try:
        await refusing.ensure_loaded(30.0)
        with pytest.raises(GenerationFailedError):
            await refusing.generate(REQUEST, 30.0, lambda _kind, _step, _total: None)
        assert refusing.loaded
    finally:
        await refusing.unload()
