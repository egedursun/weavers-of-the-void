from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import MEMORIES
from aerona.constants.units import PERCENT
from aerona.db.bond_index import bond_lookup
from aerona.db.read_memo import memoized
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow, TraitRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.renown import RulerCurrencyRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.bond import KIN_BOND_KINDS, BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import OpinionComponent, TraitEffect, TraitKind, ValueAxis
from aerona.engine.mind.book import ValueIndex, trait_effect, traits_of, values_for
from aerona.engine.mind.memories import memories_about, strength_of
from aerona.engine.mind.space import NEUTRAL_DISTANCE, memory_weight, value_alignment
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import BondIndex, active_bonds, spoken_language
from aerona.engine.renown.book import standing_with
from aerona.rules.registry import Rules

PAIR_BONDS = (BondKind.ENEMY, BondKind.ALLY, BondKind.TRADES_WITH, BondKind.PAYS_TRIBUTE)
KIN_BONDS = KIN_BOND_KINDS
PAIR_KINDS = frozenset({*KIN_BOND_KINDS, BondKind.ENEMY, BondKind.ALLY, BondKind.TRADES_WITH, BondKind.PAYS_TRIBUTE})
NEGATIVE_COMPONENTS = frozenset({OpinionComponent.GRIEVANCE, OpinionComponent.FEAR})


@dataclass(frozen=True)
class PairFacts:
    same_god: bool = False
    other_god: bool = False
    same_language: bool = False
    enemy: bool = False
    ally: bool = False
    trade: bool = False
    tribute: bool = False
    feud: bool = False
    kin: bool = False
    common_enemies: int = 0
    friendship: int = 0
    rivalry: int = 0
    glory: int = 0
    infamy: int = 0
    dread: int = 0
    tyranny: int = 0


@dataclass(frozen=True)
class OpinionTerm:
    key: str
    value: int


@dataclass(frozen=True)
class WeighedMemory:
    row: MemoryRow
    strength: int
    weight_pct: int
    contribution: int


@dataclass(frozen=True)
class Opinion:
    holder_id: int
    subject_id: int
    value: int
    components: dict[OpinionComponent, int]
    memories: list[WeighedMemory]
    alignment: int
    terms: list[OpinionTerm]


def shared_terms(rules: Rules, facts: PairFacts) -> list[OpinionTerm]:
    table = rules.opinion
    terms = [
        OpinionTerm("shared_god", table.shared_god) if facts.same_god else None,
        OpinionTerm("other_god", -table.other_god) if facts.other_god else None,
        OpinionTerm("shared_language", table.shared_language) if facts.same_language else None,
        OpinionTerm("enemy", -table.enemy) if facts.enemy else None,
        OpinionTerm("ally", table.ally) if facts.ally else None,
        OpinionTerm("trade", table.trade) if facts.trade else None,
        OpinionTerm("tribute", -table.tribute) if facts.tribute else None,
        OpinionTerm("blood_feud", -table.blood_feud) if facts.feud else None,
        OpinionTerm("kin", table.kin) if facts.kin else None,
        OpinionTerm("common_enemies", min(table.common_enemy_cap, facts.common_enemies * table.common_enemy)) if facts.common_enemies else None,
        OpinionTerm("friendship", round(facts.friendship * rules.social.relation_opinion_pct / PERCENT)) if facts.friendship else None,
        OpinionTerm("rivalry", -round(facts.rivalry * rules.social.relation_opinion_pct / PERCENT / 2)) if facts.rivalry else None,
        OpinionTerm("glory", round(facts.glory * rules.local_renown.opinion_pct / PERCENT)) if facts.glory else None,
        OpinionTerm("infamy", -round(facts.infamy * rules.local_renown.opinion_pct / PERCENT)) if facts.infamy else None,
        OpinionTerm("dread", -round(facts.dread * rules.currencies.opinion_pct / PERCENT)) if facts.dread else None,
        OpinionTerm("tyranny", -round(facts.tyranny * rules.currencies.opinion_pct / PERCENT)) if facts.tyranny else None,
    ]
    return [term for term in terms if term is not None]


def weigh(rules: Rules, epoch: int, values: Mapping[ValueAxis, int], memories: Iterable[MemoryRow]) -> list[WeighedMemory]:
    table = rules.opinion
    weighed: list[WeighedMemory] = []
    for row in memories:
        strength = strength_of(row, epoch)
        weight = memory_weight(values, row.kind, floor_pct=table.reading_floor_pct, ceiling_pct=table.reading_ceiling_pct) if values else 1.0
        weighed.append(WeighedMemory(row, round(strength), round(weight * PERCENT), round(strength * weight)))
    return weighed


def components_of(weighed: Iterable[WeighedMemory], trust_term: int) -> dict[OpinionComponent, int]:
    totals: dict[OpinionComponent, float] = defaultdict(float)
    for item in weighed:
        for component, share in MEMORIES[item.row.kind].components.items():
            part = item.contribution * share / PERCENT
            totals[component] += abs(part) if component in NEGATIVE_COMPONENTS and part < 0 else (0 if component in NEGATIVE_COMPONENTS else part)
    totals[OpinionComponent.TRUST] += trust_term
    return {component: clamp_int(totals.get(component, 0), RELATION_MIN, RELATION_MAX) for component in OpinionComponent}


def compose(
    rules: Rules,
    epoch: int,
    *,
    holder_id: int,
    subject_id: int,
    holder_values: Mapping[ValueAxis, int],
    subject_values: Mapping[ValueAxis, int],
    holder_traits: Iterable[TraitKind],
    memories: Iterable[MemoryRow],
    facts: PairFacts,
) -> Opinion:
    table = rules.opinion
    weighed = weigh(rules, epoch, holder_values, memories)
    raw_alignment = value_alignment(holder_values, subject_values) if holder_values and subject_values else 0
    alignment = round(raw_alignment * table.align_weight / NEUTRAL_DISTANCE)
    terms = shared_terms(rules, facts)
    trust = round(trait_effect(holder_traits, TraitEffect.TRUST, rules.traits.effect_scale_pct) * table.trait_trust_pct / PERCENT)
    if trust:
        terms.append(OpinionTerm("temperament", trust))
    total = sum(item.contribution for item in weighed) + alignment + sum(term.value for term in terms)
    return Opinion(
        holder_id,
        subject_id,
        clamp_int(total, RELATION_MIN, RELATION_MAX),
        components_of(weighed, trust),
        sorted(weighed, key=lambda item: (-abs(item.contribution), item.row.id)),
        alignment,
        terms,
    )


@memoized(BondRow)
async def _patron(session: AsyncSession, node_id: int) -> int | None:
    return await BondRepository(session).patron(node_id)


async def _language(session: AsyncSession, node_id: int) -> int | None:
    found = await spoken_language(session, node_id)
    return found.id if found is not None else None


@memoized(BondRow)
async def _enemies(session: AsyncSession, node_id: int) -> frozenset[int]:
    bonds = [*await active_bonds(session, [BondKind.ENEMY], sources=[node_id]), *await active_bonds(session, [BondKind.ENEMY], targets=[node_id])]
    return frozenset(bond.other_end(node_id) for bond in bonds)


@memoized(RelationshipRow)
async def bonds_held(session: AsyncSession, holder_id: int) -> dict[int, RelationshipRow]:
    found: dict[int, RelationshipRow] = {}
    for row in await session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id == holder_id).order_by(RelationshipRow.id)):
        found.setdefault(row.subject_node_id, row)
    return found


async def personal_bond(session: AsyncSession, first: int, second: int) -> RelationshipRow | None:
    return (await bonds_held(session, first)).get(second)


async def pair_facts(session: AsyncSession, first: int, second: int) -> PairFacts:
    bonds = BondRepository(session)
    first_god, second_god = await _patron(session, first), await _patron(session, second)
    first_language, second_language = await _language(session, first), await _language(session, second)
    relation = await session.get(CommunityRelationRow, (min(first, second), max(first, second)))
    kinds = {bond.kind for bond in await bonds.active_between(first, second, PAIR_KINDS)}
    common = (await _enemies(session, first) & await _enemies(session, second)) - {first, second}
    bond = await personal_bond(session, first, second)
    glory, infamy = await standing_with(session, second, first)
    purse = await session.get(RulerCurrencyRow, second)
    return PairFacts(
        same_god=first_god is not None and first_god == second_god,
        other_god=first_god is not None and second_god is not None and first_god != second_god,
        same_language=first_language is not None and first_language == second_language,
        enemy=BondKind.ENEMY in kinds,
        ally=BondKind.ALLY in kinds,
        trade=BondKind.TRADES_WITH in kinds,
        tribute=BondKind.PAYS_TRIBUTE in kinds,
        feud=relation is not None and relation.blood_feud_since_epoch is not None,
        kin=not kinds.isdisjoint(KIN_BONDS),
        common_enemies=len(common),
        friendship=bond.friendship if bond is not None else 0,
        rivalry=bond.rivalry if bond is not None else 0,
        glory=glory,
        infamy=infamy,
        dread=purse.dread if purse is not None else 0,
        tyranny=purse.tyranny if purse is not None else 0,
    )


async def opinion(session: AsyncSession, rules: Rules, epoch: int, holder_id: int, subject_id: int) -> Opinion:
    return compose(
        rules,
        epoch,
        holder_id=holder_id,
        subject_id=subject_id,
        holder_values=await values_for(session, holder_id),
        subject_values=await values_for(session, subject_id),
        holder_traits=await traits_of(session, holder_id),
        memories=await memories_about(session, holder_id, subject_id),
        facts=await pair_facts(session, holder_id, subject_id),
    )


def with_rulers(rules: Rules, base: float, ruler_views: list[int]) -> int:
    if not ruler_views:
        return clamp_int(base, RELATION_MIN, RELATION_MAX)
    weight = rules.opinion.ruler_weight_pct / PERCENT
    return clamp_int(base * (1 - weight) + sum(ruler_views) / len(ruler_views) * weight, RELATION_MIN, RELATION_MAX)


async def mortal_rulers(session: AsyncSession, community_id: int) -> list[int]:
    lookup = await bond_lookup(session)
    if lookup is not None:
        found = set()
        for bond in lookup.select([BondKind.RULES], [BondState.ACTIVE], targets=[community_id]):
            ruler = await session.get(EntityRow, bond.source_node_id)
            if ruler is not None and ruler.entity_type is EntityType.MORTAL and ruler.status is EntityStatus.CANON:
                found.add(ruler.id)
        return sorted(found)
    statement = (
        select(BondRow.source_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.kind == BondKind.RULES,
            BondRow.state == BondState.ACTIVE,
            BondRow.target_node_id == community_id,
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    return sorted(set(await session.scalars(statement)))


async def pair_relation(session: AsyncSession, rules: Rules, epoch: int, first: int, second: int) -> int:
    forward = await opinion(session, rules, epoch, first, second)
    backward = await opinion(session, rules, epoch, second, first)
    views = [(await opinion(session, rules, epoch, ruler, second)).value for ruler in await mortal_rulers(session, first)]
    views += [(await opinion(session, rules, epoch, ruler, first)).value for ruler in await mortal_rulers(session, second)]
    return with_rulers(rules, (forward.value + backward.value) / 2, views)


@dataclass
class OpinionContext:
    rules: Rules
    epoch: int
    values: ValueIndex
    bonds: BondIndex
    patrons: dict[int, int | None]
    languages: dict[int, int | None]
    feuds: set[tuple[int, int]]
    memories: dict[tuple[int, int], list[MemoryRow]] = field(default_factory=dict)
    traits: dict[int, set[TraitKind]] = field(default_factory=dict)
    rulers: dict[int, list[int]] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules, epoch: int, nodes: Iterable[int], values: ValueIndex) -> "OpinionContext":
        communities = list(dict.fromkeys(nodes))
        rulers = {node: await mortal_rulers(session, node) for node in communities}
        ids = list(dict.fromkeys([*communities, *(ruler for found in rulers.values() for ruler in found)]))
        bonds = await BondIndex.load(session, (*PAIR_BONDS, *KIN_BONDS))
        patrons = {node: await _patron(session, node) for node in ids}
        languages = {node: await _language(session, node) for node in ids}
        feuds = {
            (row.entity_a_id, row.entity_b_id)
            for row in await session.scalars(select(CommunityRelationRow).where(CommunityRelationRow.blood_feud_since_epoch.is_not(None)))
        }
        context = cls(rules, epoch, values, bonds, patrons, languages, feuds, rulers=rulers)
        for row in await session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id.in_(ids))):
            context.memories.setdefault((row.holder_node_id, row.subject_node_id), []).append(row)
        for trait in await session.scalars(select(TraitRow).where(TraitRow.node_id.in_(ids))):
            context.traits.setdefault(trait.node_id, set()).add(trait.trait)
        return context

    def facts(self, first: int, second: int) -> PairFacts:
        first_god, second_god = self.patrons.get(first), self.patrons.get(second)
        first_language = self.languages.get(first)
        enemies_first = {bond.other_end(first) for bond in self.bonds.touching(first, BondKind.ENEMY)}
        enemies_second = {bond.other_end(second) for bond in self.bonds.touching(second, BondKind.ENEMY)}
        return PairFacts(
            same_god=first_god is not None and first_god == second_god,
            other_god=first_god is not None and second_god is not None and first_god != second_god,
            same_language=first_language is not None and first_language == self.languages.get(second),
            enemy=self.bonds.between(first, second, BondKind.ENEMY),
            ally=self.bonds.between(first, second, BondKind.ALLY),
            trade=self.bonds.between(first, second, BondKind.TRADES_WITH),
            tribute=self.bonds.between(first, second, BondKind.PAYS_TRIBUTE),
            feud=(min(first, second), max(first, second)) in self.feuds,
            kin=any(self.bonds.between(first, second, kind) for kind in KIN_BONDS),
            common_enemies=len((enemies_first & enemies_second) - {first, second}),
        )

    def opinion(self, holder_id: int, subject_id: int) -> Opinion:
        return compose(
            self.rules,
            self.epoch,
            holder_id=holder_id,
            subject_id=subject_id,
            holder_values=self.values.of(holder_id),
            subject_values=self.values.of(subject_id),
            holder_traits=self.traits.get(holder_id, set()),
            memories=self.memories.get((holder_id, subject_id), []),
            facts=self.facts(holder_id, subject_id),
        )

    def relation(self, first: int, second: int) -> int:
        base = (self.opinion(first, second).value + self.opinion(second, first).value) / 2
        views = [self.opinion(ruler, second).value for ruler in self.rulers.get(first, [])]
        views += [self.opinion(ruler, first).value for ruler in self.rulers.get(second, [])]
        return with_rulers(self.rules, base, views)
