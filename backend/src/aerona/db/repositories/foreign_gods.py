from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.core.errors import ConflictError
from aerona.db.repositories.base import Repository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.models.stats import StatBlock


@dataclass(frozen=True)
class ForeignGodPowerDraft:
    name: str
    effect: ForeignGodPowerEffect
    description: str


@dataclass(frozen=True)
class ForeignGodDraft:
    name: str
    world_id: int
    domain_primary: Domain
    power: int
    stats: StatBlock
    created_epoch: int
    domain_secondary: Domain | None = None
    title: str | None = None
    stance: int = 0
    status: ForeignGodStatus = ForeignGodStatus.AWAKE
    description: str | None = None
    powers: Sequence[ForeignGodPowerDraft] = ()


class ForeignGodRepository(Repository):
    async def create(self, draft: ForeignGodDraft) -> ForeignGodRow:
        names = NameRepository(self.session)
        if await names.is_taken(draft.name):
            raise ConflictError(f"The name {draft.name} is already taken.")
        god = ForeignGodRow(
            name=draft.name,
            title=draft.title,
            domain_primary=draft.domain_primary,
            domain_secondary=draft.domain_secondary,
            world_id=draft.world_id,
            power=draft.power,
            stance=draft.stance,
            status=draft.status,
            description=draft.description,
            created_epoch=draft.created_epoch,
        )
        god.apply_stats(draft.stats)
        await self.insert(god)
        god.name = await names.claim(god.id, draft.name)
        await self.set_powers(god.id, draft.powers)
        return god

    async def set_powers(self, god_id: int, powers: Sequence[ForeignGodPowerDraft]) -> list[ForeignGodPowerRow]:
        await self.session.execute(delete(ForeignGodPowerRow).where(ForeignGodPowerRow.god_id == god_id))
        rows = [
            ForeignGodPowerRow(god_id=god_id, slot=slot, name=power.name, effect=power.effect, description=power.description)
            for slot, power in enumerate(powers)
        ]
        self.session.add_all(rows)
        await self.flush()
        return rows

    async def in_world(self, world_id: int, statuses: Sequence[ForeignGodStatus] = tuple(ForeignGodStatus)) -> list[ForeignGodRow]:
        statement = select(ForeignGodRow).where(ForeignGodRow.world_id == world_id, ForeignGodRow.status.in_(list(statuses)))
        return list(await self.session.scalars(statement.order_by(ForeignGodRow.id)))
