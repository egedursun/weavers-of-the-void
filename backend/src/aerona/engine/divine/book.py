from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domain_effects import DOMAIN_EFFECTS, SYNERGY_OF
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.divine import DivineWoundRow, WorldDomainHookRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.divine import DivineWoundKind, DomainHook
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class GodView:
    node_id: int
    domains: tuple[Domain, ...]
    severed: frozenset[Domain]
    potency: float

    @property
    def living_domains(self) -> tuple[Domain, ...]:
        return tuple(domain for domain in self.domains if domain not in self.severed)


@dataclass
class DivineBook:
    rules: Rules
    gods: dict[int, GodView] = field(default_factory=dict)
    patrons: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    overrides: dict[tuple[int, Domain, DomainHook], int] = field(default_factory=dict)
    places: dict[int, tuple[int | None, int | None, int]] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "DivineBook":
        book = cls(rules)
        severed: dict[int, set[Domain]] = defaultdict(set)
        wounds = select(DivineWoundRow.god_node_id, DivineWoundRow.domain).where(
            DivineWoundRow.kind == DivineWoundKind.SEVERED_DOMAIN, DivineWoundRow.healed < PERCENT
        )
        for god_id, domain in await session.execute(wounds):
            if domain is not None:
                severed[god_id].add(domain)
        for son in await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD)):
            book.gods[son.id] = GodView(son.id, son.domains, frozenset(severed[son.id]), max(0, son.existence) / PERCENT)
        living_gods = select(ForeignGodRow).where(ForeignGodRow.status.not_in([ForeignGodStatus.DEAD]))
        for god in await session.scalars(living_gods):
            domains = tuple(domain for domain in (god.domain_primary, god.domain_secondary) if domain is not None)
            book.gods[god.id] = GodView(god.id, domains, frozenset(severed[god.id]), max(0, god.power) / PERCENT)
        worship = select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        for source, target in await session.execute(worship):
            if target in book.gods:
                book.patrons[source].append(target)
        for row in await session.scalars(select(WorldDomainHookRow)):
            book.overrides[(row.world_id, row.domain, row.hook)] = row.pct
        return book

    async def place_of(self, session: AsyncSession, entity_id: int) -> tuple[int | None, int | None, int]:
        if entity_id not in self.places:
            row = await session.get(EntityRow, entity_id)
            self.places[entity_id] = (row.location_id, row.affiliated_entity_id, row.world_id) if row is not None else (None, None, 0)
        return self.places[entity_id]

    async def faithful_of(self, session: AsyncSession, entity_id: int) -> tuple[list[int], int]:
        location, affiliation, world_id = await self.place_of(session, entity_id)
        for holder in (entity_id, location, affiliation):
            if holder is not None and self.patrons.get(holder):
                return self.patrons[holder], world_id
        if location is not None:
            outer, _, _ = await self.place_of(session, location)
            if outer is not None and self.patrons.get(outer):
                return self.patrons[outer], world_id
        return [], world_id

    def god_pct(self, god_id: int, hook: DomainHook, world_id: int | None) -> float:
        god = self.gods.get(god_id)
        if god is None:
            return 0.0
        table = self.rules.domains
        steps = {2: table.major_hook_pct, 1: table.minor_hook_pct}
        total = 0.0
        living = god.living_domains
        for domain in living:
            weight = DOMAIN_EFFECTS[domain].hooks.get(hook)
            if weight is None:
                continue
            scale = self.overrides.get((world_id, domain, hook), PERCENT) if world_id is not None else PERCENT
            total += steps[weight] * scale / PERCENT
        if len(living) > 1:
            synergy = SYNERGY_OF.get(frozenset(living))
            if synergy is not None and synergy.hook is hook:
                total += table.synergy_pct
        return total * god.potency

    def share(self, god_id: int, hook: DomainHook, world_id: int | None = None) -> float:
        return self.god_pct(god_id, hook, world_id) / max(1, self.rules.domains.major_hook_pct)

    async def pct(self, session: AsyncSession, entity_id: int | None, hook: DomainHook) -> float:
        if entity_id is None:
            return 0.0
        gods, world_id = await self.faithful_of(session, entity_id)
        total = sum(self.god_pct(god_id, hook, world_id) for god_id in gods)
        return min(float(self.rules.domains.hook_cap_pct), total)

    async def factor(self, session: AsyncSession, entity_id: int | None, hook: DomainHook) -> float:
        return 1 + await self.pct(session, entity_id, hook) / PERCENT

    async def easing(self, session: AsyncSession, entity_id: int | None, hook: DomainHook) -> float:
        return max(0.0, 1 - await self.pct(session, entity_id, hook) / PERCENT)
