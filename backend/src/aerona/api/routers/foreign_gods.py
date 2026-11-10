from fastapi import APIRouter, Path, Query
from sqlalchemy import select

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.gods import FolkView, ForeignGodDetail, ForeignGodWorshipper
from aerona.api.schemas.records import EntitySummary, ForeignGodPower, ForeignGodRecord, NodeRef, WorldRecord
from aerona.api.views.common import bond_count, bond_views, chronicle_lines, foreign_god_record, foreign_god_records, images_of
from aerona.constants.api import RELATION_PAGE_DEFAULT, RELATION_PAGE_MAX
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.lore import ChronicleRow, FolkBeliefRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.engine.gods.acts import foreign_drain_for, foreign_kill_cost_for
from aerona.services.images.records import cover_of

router = APIRouter(tags=["foreign_gods"])

NO_GOD = "No such foreign god."
DEATHLESS_CAPTION = "Deathless: killing costs {multiplier} times more."
GID = {"god_id": "god_id"}

ALIASES = (
    Alias("POST", "/foreign-gods", "foreign_god:place"),
    Alias("PATCH", "/foreign-gods/{god_id}", "foreign_god:edit", path_fields=GID),
    Alias("POST", "/foreign-gods/{god_id}/deepen", "foreign_god:deepen", path_fields=GID),
    Alias("POST", "/foreign-gods/{god_id}/drain", "drain:foreign_god", path_fields=GID),
    Alias("POST", "/foreign-gods/{god_id}/kill", "kill:foreign_god", path_fields=GID),
)


@router.get("/foreign-gods", response_model=list[ForeignGodRecord])
async def list_foreign_gods(services: ServicesDep) -> list[ForeignGodRecord]:
    async with reader(services) as session:
        return await foreign_god_records(session)


@router.get("/foreign-gods/{god_id}", response_model=ForeignGodDetail)
async def read_foreign_god(
    services: ServicesDep,
    god_id: int = Path(ge=1),
    bond_offset: int = Query(default=0, ge=0),
    bond_limit: int = Query(default=RELATION_PAGE_DEFAULT, ge=1, le=RELATION_PAGE_MAX),
) -> ForeignGodDetail:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        god = await session.get(ForeignGodRow, god_id)
        if god is None:
            raise NotFoundError(NO_GOD)
        power_rows = await session.scalars(select(ForeignGodPowerRow).where(ForeignGodPowerRow.god_id == god.id).order_by(ForeignGodPowerRow.slot))
        world = await session.get(WorldRow, god.world_id)
        powers = list(power_rows)
        immortal = any(row.effect is ForeignGodPowerEffect.DEATHLESS for row in powers)
        drain_amount = foreign_drain_for(rules, god.power)
        worshippers = list(
            await session.scalars(
                select(EntityRow)
                .join(BondRow, BondRow.source_node_id == EntityRow.id)
                .where(BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
                .order_by(EntityRow.id)
            )
        )
        lines = list(
            await session.scalars(
                select(ChronicleRow)
                .where(ChronicleRow.visible.is_(True), ChronicleRow.kind == ChronicleKind.FOREIGN_GOD, ChronicleRow.world_id == god.world_id)
                .order_by(ChronicleRow.id.desc())
                .limit(rules.server.foreign_god_chronicle_lines)
            )
        )
        sons = await session.scalars(select(SonRow).where(SonRow.current_world_id == god.world_id).order_by(SonRow.id))
        beliefs = await session.execute(
            select(FolkBeliefRow, EntityRow.name)
            .join(EntityRow, EntityRow.id == FolkBeliefRow.people_entity_id)
            .where(FolkBeliefRow.god_node_id == god.id)
            .order_by(FolkBeliefRow.epoch.desc(), FolkBeliefRow.people_entity_id)
        )
        return ForeignGodDetail(
            god=await foreign_god_record(session, god),
            powers=[ForeignGodPower(slot=row.slot, name=row.name, effect=row.effect.value, description=row.description) for row in powers],
            kill_cost=foreign_kill_cost_for(rules, god.power, immortal),
            deathless=immortal,
            deathless_caption=DEATHLESS_CAPTION.format(multiplier=rules.god_power.kill_immortal_foreign_mult) if immortal else None,
            drain_amount=drain_amount,
            drain_gain=drain_amount * rules.god_power.foreign_essence_per_strength,
            world=WorldRecord.model_validate(world) if world else None,
            worshippers=[ForeignGodWorshipper(entity=EntitySummary.model_validate(row), cover=await cover_of(session, row.id)) for row in worshippers],
            bonds=await bond_views(session, god.id, offset=bond_offset, limit=bond_limit),
            bond_total=await bond_count(session, god.id, active_only=False),
            chronicle=await chronicle_lines(session, list(reversed(lines))),
            sons_here=[NodeRef(id=son.id, kind=son.kind, name=son.name) for son in sons],
            folk_views=[
                FolkView(
                    people_id=row.people_entity_id,
                    people_name=name,
                    local_name=row.local_name,
                    account=row.account,
                    misconception=row.misconception,
                    epoch=row.epoch,
                )
                for row, name in beliefs
            ],
            images=await images_of(session, god.id),
            cover=await cover_of(session, god.id),
        )


mount_all(router, ALIASES, tag="foreign_gods")
