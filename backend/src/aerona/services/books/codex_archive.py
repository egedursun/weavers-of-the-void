import os
import tempfile
import zipfile
from pathlib import Path

from anyio import to_thread

from aerona.constants.books import CODEX_FILENAME
from aerona.services.books.assets import write_images, write_maps
from aerona.services.books.render import CodexLinks
from aerona.services.container import Services


def _pack(directory: Path, text: str, stem: str, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{stem}/{CODEX_FILENAME}", text)
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                archive.write(path, f"{stem}/{path.relative_to(directory).as_posix()}", compress_type=zipfile.ZIP_STORED)


async def build_codex_archive(services: Services, text: str, links: CodexLinks, stem: str) -> Path:
    exports = services.settings.exports_dir
    await to_thread.run_sync(lambda: exports.mkdir(parents=True, exist_ok=True))
    handle, name = tempfile.mkstemp(suffix=".zip", dir=exports)
    target = Path(name)
    os.close(handle)
    with tempfile.TemporaryDirectory(dir=exports) as scratch:
        directory = Path(scratch)
        files = {key: directory / relative for key, relative in links.images.items()}
        maps = {world_id: directory / relative for world_id, relative in links.maps.items()}
        for path in [*files.values(), *maps.values()]:
            path.parent.mkdir(parents=True, exist_ok=True)
        await write_images(services, files)
        await write_maps(services, maps)
        for relative, figure in links.heavens.items():
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            await to_thread.run_sync(path.write_text, figure)
        await to_thread.run_sync(_pack, directory, text, stem, target)
    return target
