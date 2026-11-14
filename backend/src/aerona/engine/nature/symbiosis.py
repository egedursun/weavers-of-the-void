from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.nature import SpeciesRelationRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import GROWN, SIZE_ORDER, DomesticationStage
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.nature import SymbiosisKind
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.rules.registry import Rules

K = SymbiosisKind
HOUSED = frozenset({DomesticationStage.DOMESTICATED, DomesticationStage.BREED})


@dataclass
class SymbiosisTally:
    formed: int = 0
    livestock: int = 0


@dataclass
class SymbiosisBook:
    relations: list[SpeciesRelationRow] = field(default_factory=list)
    of_species: dict[int, list[SpeciesRelationRow]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    async def load(cls, session: AsyncSession) -> "SymbiosisBook":
        book = cls(list(await session.scalars(select(SpeciesRelationRow).order_by(SpeciesRelationRow.id))))
        for row in book.relations:
            book.of_species[row.first_species_id].append(row)
            book.of_species[row.second_species_id].append(row)
        return book

    def room(self, rules: Rules, species_id: int, present: dict[int, int]) -> float:
        table = rules.symbiosis
        factor = 1.0
        for row in self.of_species.get(species_id, []):
            other = row.second_species_id if row.first_species_id == species_id else row.first_species_id
            share = present.get(other, 0) / PERCENT * row.strength / PERCENT
            if row.kind is K.MUTUALISM:
                factor += share * table.mutual_pct / PERCENT
            elif row.kind is K.COMMENSALISM and row.first_species_id == species_id:
                factor += share * table.commensal_pct / PERCENT
        return factor

    def drain(self, rules: Rules, species_id: int, present: dict[int, int]) -> float:
        return sum(
            present.get(row.first_species_id, 0) / PERCENT * row.strength / PERCENT * rules.symbiosis.parasite_loss
            for row in self.of_species.get(species_id, [])
            if row.kind is K.PARASITISM and row.second_species_id == species_id
        )

    def shield(self, rules: Rules, species_id: int, present: dict[int, int]) -> float:
        cover = max(
            (
                present.get(row.second_species_id, 0) / PERCENT * row.strength / PERCENT
                for row in self.of_species.get(species_id, [])
                if row.kind is K.MIMICRY and row.first_species_id == species_id
            ),
            default=0.0,
        )
        return 1 - cover * rules.symbiosis.mimic_shield_pct / PERCENT


def kind_between(first: SpeciesProfileRow, second: SpeciesProfileRow, first_traits: set[CreatureTrait]) -> tuple[SymbiosisKind, bool]:
    if (first.species_class in GROWN) != (second.species_class in GROWN):
        return K.MUTUALISM, first.species_class in GROWN
    gap = SIZE_ORDER.index(second.size_class) - SIZE_ORDER.index(first.size_class)
    if CreatureTrait.MIMIC in first_traits and second.aggression > first.aggression:
        return K.MIMICRY, False
    if abs(gap) >= 2:
        return K.PARASITISM, gap < 0
    return K.COMMENSALISM, gap < 0


async def form_relations(ctx: TickContext, tally: SymbiosisTally) -> None:
    table = ctx.rules.symbiosis
    bonded = {frozenset((row.first_species_id, row.second_species_id)) for row in await ctx.session.scalars(select(SpeciesRelationRow))}
    living = set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    by_region: dict[int, list[int]] = defaultdict(list)
    for row in await ctx.session.scalars(
        select(SpeciesRangeRow)
        .where(SpeciesRangeRow.abundance >= table.shared_abundance)
        .order_by(SpeciesRangeRow.region_entity_id, SpeciesRangeRow.species_entity_id)
    ):
        if row.species_entity_id in living:
            by_region[row.region_entity_id].append(row.species_entity_id)
    for region, kinds in sorted(by_region.items()):
        for index, first_id in enumerate(kinds):
            for second_id in kinds[index + 1 :]:
                pair = frozenset((first_id, second_id))
                if pair in bonded or held(first_id) or held(second_id):
                    continue
                if not ctx.rng(seed_of("symbiosis", region, first_id, second_id, ctx.epoch)).chance(table.form_chance):
                    continue
                first, second = await ctx.session.get(SpeciesProfileRow, first_id), await ctx.session.get(SpeciesProfileRow, second_id)
                if first is None or second is None:
                    continue
                kind, swap = kind_between(first, second, await traits_of(ctx.session, first_id))
                lead, follow = (second_id, first_id) if swap else (first_id, second_id)
                ctx.session.add(
                    SpeciesRelationRow(
                        first_species_id=lead, second_species_id=follow, kind=kind, strength=table.start_strength, since_epoch=ctx.epoch, locked=[]
                    )
                )
                bonded.add(pair)
                tally.formed += 1
    await ctx.session.flush()


async def plague_herds(ctx: TickContext, tally: SymbiosisTally) -> None:
    table = ctx.rules.symbiosis
    atlas = await RegionAtlas.load(ctx.session)
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for row in list(await ctx.session.scalars(select(SpeciesRelationRow).where(SpeciesRelationRow.kind == K.PARASITISM).order_by(SpeciesRelationRow.id))):
        host = await ctx.session.get(SpeciesProfileRow, row.second_species_id)
        if host is None or host.stage not in HOUSED:
            continue
        lands = await ctx.session.scalars(
            select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == row.first_species_id, SpeciesRangeRow.abundance > 0)
        )
        for region in list(lands):
            for town in atlas.communities_in(region):
                if held(town):
                    continue
                want = round(table.livestock_loss * row.strength / PERCENT)
                tally.livestock += await ledger.take_units(town, CommodityKind.LIVESTOCK, want, GoodsFlow.LOSS) if want > 0 else 0


async def keep_symbiosis(ctx: TickContext, tally: SymbiosisTally) -> None:
    await form_relations(ctx, tally)
    await plague_herds(ctx, tally)
