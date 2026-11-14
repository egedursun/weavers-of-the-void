from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.base import Repository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.sons import SonPowerRow, SonRelationRow, SonRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.limits import POWER_SLOTS, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import PowerEffect, SonStatus, Stat
from aerona.domain.models.profiles import ExistenceProfile, Personality
from aerona.domain.models.stats import PassionBlock, StatBlock


@dataclass(frozen=True)
class PowerDraft:
    name: str
    description: str
    effect: PowerEffect
    param_entity_type: EntityType | None = None
    param_stat: Stat | None = None


@dataclass(frozen=True)
class SonDraft:
    name: str
    title: str
    rarity: Rarity
    domains: tuple[Domain, Domain]
    stats: StatBlock
    passions: PassionBlock
    personality: Personality
    existence: int
    hp: int
    essence: int
    birth_epoch: int
    powers: Sequence[PowerDraft] = ()
    existence_profile: ExistenceProfile | None = None
    parent_son_id: int | None = None
    co_parent_son_id: int | None = None
    current_world_id: int | None = None
    image_prompt: str | None = None


def ordered_pair(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


class SonRepository(Repository):
    async def create(self, draft: SonDraft) -> SonRow:
        if len(draft.powers) > POWER_SLOTS:
            raise ValidationFailedError(f"A son has at most {several(POWER_SLOTS, 'power', 'powers')}.")
        names = NameRepository(self.session)
        if await names.is_taken(draft.name):
            raise ConflictError(f"The name {draft.name} is already taken.")
        son = SonRow(
            name=draft.name,
            title=draft.title,
            rarity=draft.rarity,
            domain_primary=draft.domains[0],
            domain_secondary=draft.domains[1],
            personality=draft.personality,
            existence_profile=draft.existence_profile,
            existence=draft.existence,
            hp=draft.hp,
            essence=draft.essence,
            birth_epoch=draft.birth_epoch,
            parent_son_id=draft.parent_son_id,
            co_parent_son_id=draft.co_parent_son_id,
            current_world_id=draft.current_world_id,
            image_prompt=draft.image_prompt,
        )
        son.apply_stats(draft.stats)
        son.apply_passions(draft.passions)
        await self.insert(son)
        son.name = await names.claim(son.id, draft.name)
        await self.set_powers(son.id, draft.powers)
        return son

    async def set_powers(self, son_id: int, powers: Sequence[PowerDraft]) -> list[SonPowerRow]:
        await self.session.execute(delete(SonPowerRow).where(SonPowerRow.son_id == son_id))
        rows = [
            SonPowerRow(
                son_id=son_id,
                slot=slot,
                name=power.name,
                description=power.description,
                effect=power.effect,
                param_entity_type=power.param_entity_type,
                param_stat=power.param_stat,
            )
            for slot, power in enumerate(powers)
        ]
        self.session.add_all(rows)
        await self.flush()
        return rows

    async def powers(self, son_id: int) -> list[SonPowerRow]:
        statement = select(SonPowerRow).where(SonPowerRow.son_id == son_id).order_by(SonPowerRow.slot)
        return list(await self.session.scalars(statement))

    async def get(self, son_id: int) -> SonRow | None:
        return await self.session.get(SonRow, son_id)

    async def require_son(self, son_id: int) -> SonRow:
        return await self.require(SonRow, son_id, "son")

    async def all_sons(self) -> list[SonRow]:
        return list(await self.session.scalars(select(SonRow).order_by(SonRow.id)))

    async def living(self) -> list[SonRow]:
        statement = select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)
        return list(await self.session.scalars(statement))

    async def relation(self, first: int, second: int) -> int:
        if first == second:
            return 0
        row = await self.session.get(SonRelationRow, ordered_pair(first, second))
        return row.value if row is not None else 0

    async def change_relation(self, first: int, second: int, delta: float, note: str | None = None) -> int:
        if first == second:
            return 0
        await self.require_son(first)
        await self.require_son(second)
        key = ordered_pair(first, second)
        row = await self.session.get(SonRelationRow, key)
        if row is None:
            row = SonRelationRow(son_a_id=key[0], son_b_id=key[1], value=0)
            self.session.add(row)
        row.value = max(RELATION_MIN, min(RELATION_MAX, round(row.value + delta)))
        if note is not None:
            row.note = note
        await self.flush()
        return row.value
