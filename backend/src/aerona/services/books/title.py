from aerona.db.tables.cosmos import CosmosRow
from aerona.services.library.manifest import read_manifest
from aerona.settings import Settings


def universe_title(settings: Settings, cosmos: CosmosRow | None) -> str:
    fallback = cosmos.name if cosmos is not None else ""
    if not settings.universe_id:
        return fallback
    manifest = read_manifest(settings.process.universe(settings.universe_id).manifest)
    named = manifest.name.strip() if manifest is not None else ""
    return named or fallback
