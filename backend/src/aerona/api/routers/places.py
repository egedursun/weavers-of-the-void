from fastapi import APIRouter, Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.missing import NO_PLACE
from aerona.api.schemas.places import PlaceProfileView, PlaceSecretView
from aerona.catalog.place_terrain import kind_spec
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.entity import EntityFlag
from aerona.engine.environment.places import SacredInputs, mystery_held, relics_at, sacred_target, temples_at
from aerona.engine.primitives.queries import flags_by_entity
from aerona.engine.primitives.stats import stat_or

router = APIRouter(tags=["environment"])


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(sorted(ids))))}


@router.get("/places/{place_id}/profile", response_model=PlaceProfileView | None)
async def place_profile(services: ServicesDep, place_id: int = Path(ge=1)) -> PlaceProfileView | None:
    rules = services.rules.current
    async with reader(services) as session:
        place = await session.get(EntityRow, place_id)
        profile = await session.get(PlaceProfileRow, place_id)
        if place is None:
            raise NotFoundError(NO_PLACE)
        if profile is None:
            return None
        ground = await session.get(PlaceEnvironmentRow, place_id)
        secrets = list(await session.scalars(select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id == place_id).order_by(PlaceSecretRow.id)))
        names = await names_of(session, {item for secret in secrets for item in (secret.revealed_by_entity_id, secret.result_entity_id) if item is not None})
        marked = place_id in await flags_by_entity(session, EntityFlag.PILGRIMAGE_SITE)
        nexus = ground is not None and ground.nexus
        inputs = SacredInputs((await temples_at(session, [place_id])).get(place_id, 0), (await relics_at(session, [place_id])).get(place_id, 0), marked, nexus)
        battles = await session.scalar(select(func.count()).select_from(BattleRow).where(BattleRow.place_entity_id == place_id)) or 0
        spec = kind_spec(profile.kind)
        return PlaceProfileView(
            place_id=place_id,
            kind=profile.kind,
            sacred_class=spec.sacred,
            deep=spec.deep,
            sacredness=profile.sacredness,
            sacred_target=sacred_target(rules, profile.kind, inputs),
            pilgrims=profile.pilgrims,
            holy_site=nexus or profile.sacredness >= rules.places.holy_site_threshold,
            pilgrimage_site=marked,
            nexus=nexus,
            mystery=stat_or(place, "mystery", 0),
            mystery_held=await mystery_held(session, place_id),
            battles=battles,
            locked=sorted({*profile.locked, *(ground.locked if ground is not None else [])}),
            secrets=[
                PlaceSecretView(
                    id=secret.id,
                    kind=secret.kind,
                    strength=secret.strength,
                    sealed=secret.sealed,
                    held=secret.held,
                    origin=secret.origin,
                    material=secret.material,
                    school=secret.school,
                    branch=secret.branch,
                    hidden_by_son_id=secret.hidden_by_son_id,
                    created_epoch=secret.created_epoch,
                    revealed_epoch=secret.revealed_epoch,
                    revealed_by=secret.revealed_by,
                    revealed_by_entity_id=secret.revealed_by_entity_id,
                    revealed_by_name=names.get(secret.revealed_by_entity_id) if secret.revealed_by_entity_id is not None else None,
                    released_epoch=secret.released_epoch,
                    result_entity_id=secret.result_entity_id,
                    result_name=names.get(secret.result_entity_id) if secret.result_entity_id is not None else None,
                )
                for secret in secrets
            ],
        )
