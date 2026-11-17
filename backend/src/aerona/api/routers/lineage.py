from collections.abc import Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.lineage import (
    AggregateView,
    AlleleView,
    BloodEffectView,
    CarriedAlleleView,
    DwellingKindOption,
    DwellingView,
    FurnishingView,
    GeneView,
    GenomeView,
    GiftView,
    HomeView,
    HouseholdDebtView,
    HouseholdMemberView,
    HouseholdView,
    LikenessView,
    LineageView,
    LocusView,
    PoolView,
    ResemblanceView,
    TiedTraitView,
)
from aerona.api.schemas.mind import LabelView
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.genetic_effects import EFFECT_POINTS, GENETIC_EFFECT_LABELS
from aerona.catalog.genetics import GIFT_STANCE_LABELS, HARMFUL, HOUSEHOLD_DECISION_LABELS, HOUSEHOLD_ROLE_LABELS, LOCI, LOCUS_GROUP_LABELS
from aerona.catalog.mind import TRAITS
from aerona.core.errors import NotFoundError
from aerona.core.grammar import an
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow, HouseResemblanceRow
from aerona.db.tables.households import DwellingFurnishingRow, DwellingRow, HouseholdAggregateRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.genetics import GeneticEffect
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.genetics.genome import appearance_text, aptitudes, carried_alleles, describe_effects, effect_pct, pair_of, phenotype, score_of, tied_traits
from aerona.engine.households.dwelling_kinds import dwelling_kind_row
from aerona.engine.households.homes import expectation, furnishings
from aerona.engine.mind.book import traits_of
from aerona.rules.registry import Rules

router = APIRouter(tags=["lineage"])
BLOODLESS = "has no blood of its own; mortals carry genomes, peoples allele pools and houses a family likeness."
HOMELESS = "keeps no household; mortals belong to households and communities hold them."
NO_NODE = "Nothing lives there."
GENOME_REASON = {
    NodeKind.CREATOR: "The Creator stands outside any bloodline.",
    NodeKind.SON: "A son is made of divinity, not blood; its line shows as divine blood in the mortals it begets or blesses.",
    NodeKind.FOREIGN_GOD: "A foreign god has no mortal blood to read.",
    NodeKind.WORLD: "A world is land and sky, not a lineage; the peoples on it keep allele pools.",
    NodeKind.STAR: "A star bears no blood.",
    NodeKind.GALAXY: "A galaxy bears no blood.",
    NodeKind.CLUSTER: "A cluster of galaxies bears no blood.",
    NodeKind.DIMENSION: "A dimension is a layer of existence, not a lineage.",
}
HOME_REASON = {
    NodeKind.CREATOR: "The Creator dwells nowhere and keeps no household.",
    NodeKind.SON: "A son keeps temples, not a household.",
    NodeKind.FOREIGN_GOD: "A foreign god keeps no mortal household.",
    NodeKind.WORLD: "A world holds settlements; each keeps its households.",
    NodeKind.STAR: "A star holds no households.",
    NodeKind.GALAXY: "A galaxy holds worlds; each keeps its households.",
    NodeKind.CLUSTER: "A cluster holds galaxies; their worlds keep the households.",
    NodeKind.DIMENSION: "A dimension holds worlds; each keeps its households.",
}


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


def kind_label(kind: EntityType | None) -> str:
    return kind.value.replace("_", " ") if kind is not None else "thing"


def class_label(social_class: SocialClass) -> str:
    return social_class.value.replace("_", " ").capitalize()


def loci_views(rules: Rules, frequencies: Mapping[str, Mapping[str, int]] | None) -> list[LocusView]:
    return [
        LocusView(
            locus=locus,
            label=spec.label,
            group=spec.group,
            group_label=LOCUS_GROUP_LABELS[spec.group],
            alleles=[
                AlleleView(
                    key=allele.key,
                    label=allele.label,
                    frequency=(frequencies or {}).get(locus.value, {}).get(allele.key) if frequencies else None,
                    effects=describe_effects(rules, locus, allele.score),
                )
                for allele in spec.alleles
            ],
        )
        for locus, spec in LOCI.items()
    ]


async def blood_views(session: AsyncSession, rules: Rules, row: GenomeRow) -> tuple[list[TiedTraitView], list[CarriedAlleleView], list[BloodEffectView]]:
    owned = await traits_of(session, row.holder_node_id)
    tied = [
        TiedTraitView(trait=trait, trait_label=TRAITS[trait].label, locus=locus, locus_label=LOCI[locus].label, held=trait in owned)
        for locus, trait in tied_traits(row.genes)
    ]
    carried = [
        CarriedAlleleView(
            locus=locus,
            locus_label=LOCI[locus].label,
            allele=allele,
            allele_label=LOCI[locus].allele(allele).label,
            harmful=HARMFUL.get(locus) == allele,
        )
        for locus, allele in carried_alleles(row.genes)
    ]
    effects = [
        BloodEffectView(effect=channel, label=GENETIC_EFFECT_LABELS[channel], amount=amount, per_epoch=channel in EFFECT_POINTS)
        for channel in GeneticEffect
        if (amount := effect_pct(rules, row.genes, channel))
    ]
    return tied, carried, effects


async def genome_view(session: AsyncSession, rules: Rules, row: GenomeRow) -> GenomeView:
    gifts = aptitudes(rules, row.genes)
    tied, carried, effects = await blood_views(session, rules, row)
    parents = await node_refs(session, [int(key) for key in row.likeness])
    return GenomeView(
        genes=[
            GeneView(
                locus=locus,
                label=spec.label,
                group=spec.group,
                group_label=LOCUS_GROUP_LABELS[spec.group],
                first=pair_of(row.genes, locus)[0],
                second=pair_of(row.genes, locus)[1],
                shown=phenotype(row.genes, locus),
                shown_label=spec.allele(phenotype(row.genes, locus)).label,
                effects=describe_effects(rules, locus, score_of(row.genes, locus)),
            )
            for locus, spec in LOCI.items()
        ],
        gifts=[
            GiftView(
                school=school,
                aptitude=value,
                gifted=value >= rules.gift.gifted_at,
            )
            for school, value in sorted(gifts.items(), key=lambda item: (-item[1], item[0].value))
            if isinstance(school, MagicSchool)
        ],
        appearance=appearance_text(row.genes, row.marks),
        marks=row.marks,
        beauty=row.beauty,
        inbreeding=row.inbreeding,
        recognisability=row.recognisability,
        potential=dict(row.potential),
        divine_son=await node_ref(session, row.divine_son_id),
        likeness=[LikenessView(parent=parents[int(key)], likeness=value) for key, value in sorted(row.likeness.items()) if int(key) in parents],
        tied_traits=tied,
        carried=carried,
        blood_effects=effects,
        epoch=row.epoch,
        held=sorted(row.locked or []),
    )


def pool_view(rules: Rules, row: AllelePoolRow) -> PoolView:
    return PoolView(
        loci=loci_views(rules, row.frequencies),
        gift_stance=row.gift_stance,
        gift_stance_label=GIFT_STANCE_LABELS[row.gift_stance],
        gifted_share=row.gifted_share,
        cohort_shares=[LabelView(key=key, label=str(value)) for key, value in sorted(row.cohort_shares.items())],
        epoch=row.epoch,
        held=sorted(row.locked or []),
    )


def resemblance_view(row: HouseResemblanceRow) -> ResemblanceView:
    spec = LOCI[row.locus]
    return ResemblanceView(
        locus=row.locus,
        locus_label=spec.label,
        allele=row.allele,
        allele_label=spec.allele(row.allele).label,
        share=row.share,
        since_epoch=row.since_epoch,
        held=sorted(row.locked or []),
    )


@router.get("/lineage/{node_id}", response_model=LineageView)
async def lineage_view(services: ServicesDep, node_id: int = Path(ge=1)) -> LineageView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError(NO_NODE)
        rules = services.rules.current
        entity = await session.get(EntityRow, node_id)
        kind = entity.entity_type if entity is not None else None
        genome_row = await session.get(GenomeRow, node_id)
        pool_row = await session.get(AllelePoolRow, node_id)
        likeness_row = await session.get(HouseResemblanceRow, node_id)
        can_genome = kind is EntityType.MORTAL
        can_pool = kind is EntityType.PEOPLE
        can_likeness = kind is EntityType.HOUSE
        reason = None
        if not (can_genome or can_pool or can_likeness):
            reason = GENOME_REASON.get(
                node.kind,
                f"{an(kind_label(kind), capital=True)} {BLOODLESS}",
            )
        return LineageView(
            node_id=node_id,
            node_kind=kind if kind is not None else node.kind,
            can_hold_genome=can_genome,
            can_hold_pool=can_pool,
            can_hold_likeness=can_likeness,
            reason=reason,
            genome=await genome_view(session, rules, genome_row) if genome_row is not None else None,
            pool=pool_view(rules, pool_row) if pool_row is not None else None,
            resemblance=resemblance_view(likeness_row) if likeness_row is not None else None,
            loci=loci_views(rules, None),
            stances=labels(GIFT_STANCE_LABELS),
        )


async def dwelling_options(session: AsyncSession) -> list[DwellingKindOption]:
    rows = await session.scalars(
        select(DwellingKindRow).where(DwellingKindRow.retired.is_(False)).order_by(DwellingKindRow.built_in.desc(), DwellingKindRow.id)
    )
    return [DwellingKindOption(id=row.id, name=row.name, level=row.category, built_in=row.built_in) for row in rows]


async def dwelling_view(session: AsyncSession, rules: Rules, row: DwellingRow, social_class: SocialClass | None) -> DwellingView:
    items = list(
        await session.scalars(select(DwellingFurnishingRow).where(DwellingFurnishingRow.dwelling_id == row.id).order_by(DwellingFurnishingRow.item_node_id))
    )
    refs = await node_refs(session, [item.item_node_id for item in items])
    district = await session.get(DistrictRow, row.district_id) if row.district_id is not None else None
    count = await furnishings(session, row.id)
    kind = await dwelling_kind_row(session, row.dwelling_kind_id)
    return DwellingView(
        dwelling_kind_id=row.dwelling_kind_id,
        kind_name=kind.name,
        level=kind.category,
        quality=row.quality,
        effective_quality=min(100, row.quality + count * rules.households.furnishing_quality),
        expected_quality=expectation(social_class),
        rooms=row.rooms,
        district_id=row.district_id,
        district_kind=district.kind if district is not None else None,
        settlement=await node_ref(session, row.settlement_node_id),
        furnishings=[FurnishingView(item=refs[item.item_node_id], placed_epoch=item.placed_epoch) for item in items if item.item_node_id in refs],
        tenure=row.tenure,
        heating=row.heating,
        light=row.light,
        crowding=row.crowding,
        built_epoch=row.built_epoch,
        held=sorted(row.locked or []),
    )


async def household_view(session: AsyncSession, rules: Rules, row: HouseholdRow) -> HouseholdView:
    members = list(
        await session.scalars(
            select(HouseholdMemberRow)
            .where(HouseholdMemberRow.household_id == row.id)
            .order_by(HouseholdMemberRow.joined_epoch, HouseholdMemberRow.member_node_id)
        )
    )
    refs = await node_refs(
        session, [*(member.member_node_id for member in members), *(member.cares_for_node_id for member in members if member.cares_for_node_id)]
    )
    dwelling = await session.scalar(select(DwellingRow).where(DwellingRow.household_id == row.id))
    lenders = {
        household.id: household.name for household in await session.scalars(select(HouseholdRow).where(HouseholdRow.id.in_([int(key) for key in row.debts])))
    }
    return HouseholdView(
        id=row.id,
        name=row.name,
        head=await node_ref(session, row.head_node_id),
        settlement=await node_ref(session, row.settlement_node_id),
        social_class=row.social_class,
        wealth=row.wealth,
        income=row.income,
        expenses=row.expenses,
        servants=row.servants,
        dependents=row.dependents,
        burden=row.burden,
        debts=[
            HouseholdDebtView(household_id=int(key), name=lenders.get(int(key), "a vanished household"), amount=value)
            for key, value in sorted(row.debts.items())
        ],
        last_decision=row.last_decision,
        last_decision_label=HOUSEHOLD_DECISION_LABELS[row.last_decision] if row.last_decision is not None else None,
        decided_epoch=row.decided_epoch,
        formed_epoch=row.formed_epoch,
        form=row.form,
        members=[
            HouseholdMemberView(
                mortal=refs[member.member_node_id],
                role=member.role,
                role_label=HOUSEHOLD_ROLE_LABELS[member.role],
                cares_for=refs.get(member.cares_for_node_id) if member.cares_for_node_id is not None else None,
                joined_epoch=member.joined_epoch,
                held=member.locked,
            )
            for member in members
            if member.member_node_id in refs
        ],
        dwelling=await dwelling_view(session, rules, dwelling, row.social_class) if dwelling is not None else None,
        held=sorted(row.locked or []),
    )


async def aggregate_view(session: AsyncSession, row: HouseholdAggregateRow) -> AggregateView:
    kind = await dwelling_kind_row(session, row.dwelling_kind_id)
    return AggregateView(
        social_class=row.social_class,
        social_class_label=class_label(row.social_class),
        households=row.households,
        mean_size=row.mean_size,
        dwelling_kind_id=row.dwelling_kind_id,
        dwelling_name=kind.name,
        dwelling_level=kind.category,
        quality=row.quality,
        wealth=row.wealth,
        epoch=row.epoch,
        held=sorted(row.locked or []),
    )


@router.get("/home/{node_id}", response_model=HomeView)
async def home_view(services: ServicesDep, node_id: int = Path(ge=1)) -> HomeView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError(NO_NODE)
        rules = services.rules.current
        entity = await session.get(EntityRow, node_id)
        kind = entity.entity_type if entity is not None else None
        member = await session.get(HouseholdMemberRow, node_id) if kind is EntityType.MORTAL else None
        own = await session.get(HouseholdRow, member.household_id) if member is not None else None
        local = (
            list(
                await session.scalars(
                    select(HouseholdRow).where(HouseholdRow.settlement_node_id == node_id).order_by(HouseholdRow.wealth.desc(), HouseholdRow.id)
                )
            )
            if kind in COMMUNITY_TYPES
            else []
        )
        aggregates = (
            list(await session.scalars(select(HouseholdAggregateRow).where(HouseholdAggregateRow.community_node_id == node_id)))
            if kind in COMMUNITY_TYPES
            else []
        )
        can_household = kind is EntityType.MORTAL
        can_aggregates = kind in COMMUNITY_TYPES
        reason = None
        if not (can_household or can_aggregates):
            reason = HOME_REASON.get(
                node.kind,
                f"{an(kind_label(kind), capital=True)} {HOMELESS}",
            )
        nearby: list[HouseholdRow] = (
            list(
                await session.scalars(
                    select(HouseholdRow).where(HouseholdRow.settlement_node_id == own.settlement_node_id, HouseholdRow.id != own.id).order_by(HouseholdRow.name)
                )
            )
            if own is not None and own.settlement_node_id is not None
            else []
        )
        return HomeView(
            node_id=node_id,
            node_kind=kind if kind is not None else node.kind,
            can_hold_household=can_household,
            can_hold_aggregates=can_aggregates,
            reason=reason,
            household=await household_view(session, rules, own) if own is not None else None,
            households=[await household_view(session, rules, row) for row in local],
            aggregates=[await aggregate_view(session, row) for row in sorted(aggregates, key=lambda row: row.social_class.value)],
            roles=labels(HOUSEHOLD_ROLE_LABELS),
            dwellings=await dwelling_options(session),
            classes=[LabelView(key=social.value, label=class_label(social)) for social in SocialClass],
            neighbours=[LabelView(key=str(row.id), label=row.name) for row in nearby],
        )
