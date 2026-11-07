from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select

from aerona.constants.schema import SINGLETON_ID
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.base import Repository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.genesis import GenesisSettings
from aerona.domain.models.profiles import TravelResource
from aerona.rules.registry import Rules
from aerona.rules.renames import canonical_overrides
from aerona.rules.snapshot import apply_overrides

RulesSnapshot = dict[str, dict[str, float]]


def snapshot_rules(rules: Rules) -> RulesSnapshot:
    return {namespace: {key: float(value) for key, value in values.items()} for namespace, values in asdict(rules).items()}


SNAPSHOT_RULES: dict[tuple[tuple[str, str, float], ...], Rules] = {}
SNAPSHOT_CAP = 16


def rules_from_snapshot(snapshot: RulesSnapshot) -> Rules:
    key = tuple(sorted((namespace, name, float(value)) for namespace, values in snapshot.items() for name, value in values.items()))
    found = SNAPSHOT_RULES.get(key)
    if found is None:
        if len(SNAPSHOT_RULES) >= SNAPSHOT_CAP:
            SNAPSHOT_RULES.clear()
        overrides = canonical_overrides({(namespace, name): value for namespace, name, value in key})
        found = SNAPSHOT_RULES[key] = apply_overrides(Rules(), overrides)
    return found


def snapshot_differences(snapshot: RulesSnapshot, defaults: Rules) -> dict[tuple[str, str], tuple[float, float]]:
    baseline = snapshot_rules(defaults)
    current = canonical_overrides({(namespace, key): value for namespace, values in snapshot.items() for key, value in values.items()})
    return {
        (namespace, key): (value, baseline[namespace][key])
        for (namespace, key), value in current.items()
        if namespace in baseline and key in baseline[namespace] and baseline[namespace][key] != value
    }


@dataclass(frozen=True)
class CosmosDraft:
    name: str
    rng_seed: int
    lore_language: LoreLanguage
    seed_idea: str
    cosmology: str
    tone: str
    rules: Rules
    genesis_settings: GenesisSettings | None = None
    travel_resource: TravelResource | None = None


@dataclass(frozen=True)
class CreatorDraft:
    name: str
    essence: int
    mood_contentment: int
    mood_anger: int
    mood_interest: int
    mood_loneliness: int
    title: str | None = None
    appearance: str | None = None
    temperament: str | None = None


class CosmosRepository(Repository):
    async def get(self) -> CosmosRow | None:
        return await self.session.get(CosmosRow, SINGLETON_ID)

    async def require_cosmos(self) -> CosmosRow:
        cosmos = await self.get()
        if cosmos is None:
            raise NotFoundError("You need to create the world first.")
        return cosmos

    async def create(self, draft: CosmosDraft) -> CosmosRow:
        if await self.get() is not None:
            raise ConflictError("The world already exists.")
        cosmos = CosmosRow(
            id=SINGLETON_ID,
            name=draft.name,
            rng_seed=draft.rng_seed,
            lore_language=draft.lore_language,
            seed_idea=draft.seed_idea,
            cosmology=draft.cosmology,
            tone=draft.tone,
            genesis_settings=draft.genesis_settings,
            travel_resource=draft.travel_resource,
            rules_snapshot=snapshot_rules(draft.rules),
            rules_snapshot_at=datetime.now(UTC),
        )
        return await self.insert(cosmos)

    async def rules(self) -> Rules:
        cosmos = await self.require_cosmos()
        return rules_from_snapshot(cosmos.rules_snapshot)

    async def store_rules(self, rules: Rules) -> None:
        cosmos = await self.require_cosmos()
        cosmos.rules_snapshot = snapshot_rules(rules)
        cosmos.rules_snapshot_at = datetime.now(UTC)
        await self.flush()

    async def creator(self) -> CreatorRow | None:
        row: CreatorRow | None = await self.session.scalar(select(CreatorRow))
        return row

    async def require_creator(self) -> CreatorRow:
        creator = await self.creator()
        if creator is None:
            raise NotFoundError("The Creator has not been made yet.")
        return creator

    async def create_creator(self, draft: CreatorDraft) -> CreatorRow:
        if await self.creator() is not None:
            raise ConflictError("The Creator already exists.")
        names = NameRepository(self.session)
        if await names.is_taken(draft.name):
            raise ConflictError(f"The name {draft.name} is already taken.")
        creator = CreatorRow(
            name=draft.name,
            title=draft.title,
            appearance=draft.appearance,
            temperament=draft.temperament,
            essence=draft.essence,
            mood_contentment=draft.mood_contentment,
            mood_anger=draft.mood_anger,
            mood_interest=draft.mood_interest,
            mood_loneliness=draft.mood_loneliness,
        )
        await self.insert(creator)
        creator.name = await names.claim(creator.id, draft.name)
        return creator

    async def first_world_id(self) -> int | None:
        world_id: int | None = await self.session.scalar(select(func.min(WorldRow.id)))
        return world_id
