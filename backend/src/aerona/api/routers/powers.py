from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.powers import (
    DensityView,
    GiftedAttitudeView,
    HiddenTruthView,
    MagicSystemsNodeView,
    MagicSystemView,
    PowerChoice,
    PowerRegistryView,
    PowerRestrictionView,
    PowersNodeView,
    PowerSourceView,
    PowerSpanView,
    PowerTriggerView,
    PowerView,
    PublicKnowledgeView,
    SeekerView,
    SourceCostView,
    SourceHazardView,
    SourceInteractionView,
    SourceKnowledgeView,
    SourceLawView,
    SourceResistanceView,
    SourcesNodeView,
    SourceStanceView,
    SourceTideView,
    SystemGrammarView,
    SystemLinkView,
    SystemRestrictionView,
    SystemSourceView,
    TruthBreachView,
    TruthKeeperView,
    TruthsNodeView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.concealment import BreachRow, HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.db.tables.powers import (
    GiftedAttitudeRow,
    MagicSystemGrammarRow,
    MagicSystemLinkRow,
    MagicSystemRow,
    MagicSystemSourceRow,
    PowerRegistryRow,
    PowerRestrictionRow,
    PowerRow,
    PowerSourceCostRow,
    PowerSourceHazardRow,
    PowerSourceInteractionRow,
    PowerSourceKnowledgeRow,
    PowerSourceResistanceRow,
    PowerSourceRow,
    PowerSpanRow,
    PowerTriggerRow,
    SourceDensityRow,
    SourceLawRow,
    SourceStanceRow,
    SourceTideRow,
    SystemRestrictionRow,
)
from aerona.engine.powers.control import TRUTH_METHODS

router = APIRouter(tags=["powers"])
NodeId = Annotated[int, Path(ge=1)]


def ref(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def must_exist(session: AsyncSession, node_id: int) -> None:
    if await session.get(NodeRow, node_id) is None:
        raise NotFoundError("No such thing.")


async def names_of(session: AsyncSession, table: type[PowerSourceRow] | type[MagicSystemRow]) -> dict[int, str]:
    return {int(row_id): str(name) for row_id, name in (await session.execute(select(table.id, table.name))).all()}


async def power_views(session: AsyncSession, powers: list[PowerRow]) -> list[PowerView]:
    ids = [power.id for power in powers]
    restrictions = list(await session.scalars(select(PowerRestrictionRow).where(PowerRestrictionRow.power_id.in_(ids)).order_by(PowerRestrictionRow.id)))
    triggers = list(await session.scalars(select(PowerTriggerRow).where(PowerTriggerRow.power_id.in_(ids)).order_by(PowerTriggerRow.id)))
    spans = list(await session.scalars(select(PowerSpanRow).where(PowerSpanRow.power_id.in_(ids)).order_by(PowerSpanRow.id)))
    sources, systems = await names_of(session, PowerSourceRow), await names_of(session, MagicSystemRow)
    wanted = [*(p.holder_node_id for p in powers), *(p.granted_by_node_id for p in powers), *(p.item_node_id for p in powers)]
    wanted += [*(r.ref_node_id for r in restrictions), *(s.target_node_id for s in spans)]
    refs = await node_refs(session, [node for node in wanted if node is not None])
    return [
        PowerView(
            id=power.id,
            holder=refs[power.holder_node_id],
            system_id=power.system_id,
            system_name=systems.get(power.system_id) if power.system_id is not None else None,
            source_id=power.source_id,
            source_name=sources.get(power.source_id) if power.source_id is not None else None,
            technique=power.technique,
            form=power.form,
            range_km=power.range_km,
            duration_days=power.duration_days,
            on_others=power.on_others,
            strength=power.strength,
            control=power.control,
            origin=power.origin,
            state=power.state,
            visibility=power.visibility,
            strain=power.strain,
            strain_cap=power.strain_cap,
            granted_by=ref(refs, power.granted_by_node_id),
            item=ref(refs, power.item_node_id),
            uses=power.uses,
            gained_epoch=power.gained_epoch,
            last_used_epoch=power.last_used_epoch,
            locked=list(power.locked),
            restrictions=[
                PowerRestrictionView(
                    id=row.id,
                    kind=row.kind,
                    ref=ref(refs, row.ref_node_id),
                    detail=row.detail,
                    strength_gain_pct=row.strength_gain_pct,
                    broken=row.broken,
                    locked=list(row.locked),
                )
                for row in restrictions
                if row.power_id == power.id
            ],
            triggers=[PowerTriggerView(id=row.id, trigger=row.trigger, locked=list(row.locked)) for row in triggers if row.power_id == power.id],
            spans=[
                PowerSpanView(
                    id=row.id, effect=row.effect, target=ref(refs, row.target_node_id), amount=row.amount, until_epoch=row.until_epoch, locked=list(row.locked)
                )
                for row in spans
                if row.power_id == power.id
            ],
        )
        for power in powers
    ]


def choices(names: dict[int, str]) -> list[PowerChoice]:
    return [PowerChoice(id=row_id, name=name) for row_id, name in sorted(names.items())]


@router.get("/powers/of/{node_id}", response_model=PowersNodeView)
async def node_powers(services: ServicesDep, node_id: NodeId) -> PowersNodeView:
    async with reader(services) as session:
        await must_exist(session, node_id)
        rules = await world_rules(services, session)
        held_powers = list(await session.scalars(select(PowerRow).where(PowerRow.holder_node_id == node_id).order_by(PowerRow.id)))
        given = list(await session.scalars(select(PowerRow).where(PowerRow.granted_by_node_id == node_id).order_by(PowerRow.id)))
        registry = list(
            await session.scalars(
                select(PowerRegistryRow)
                .where(or_(PowerRegistryRow.holder_node_id == node_id, PowerRegistryRow.polity_entity_id == node_id))
                .order_by(PowerRegistryRow.id)
            )
        )
        attitude = await session.get(GiftedAttitudeRow, node_id)
        house = await session.get(HouseProfileRow, node_id)
        refs = await node_refs(session, [node_id, *(row.polity_entity_id for row in registry), *(row.holder_node_id for row in registry)])
        return PowersNodeView(
            node=refs[node_id],
            powers=await power_views(session, held_powers),
            granted=await power_views(session, given),
            registry=[
                PowerRegistryView(
                    id=row.id,
                    polity=refs[row.polity_entity_id],
                    holder=refs[row.holder_node_id],
                    licensed=row.licensed,
                    conscripted=row.conscripted,
                    registered_epoch=row.registered_epoch,
                    locked=list(row.locked),
                )
                for row in registry
            ],
            attitude=GiftedAttitudeView(
                attitude=attitude.attitude,
                gifted_share=attitude.gifted_share,
                registered_share=attitude.registered_share,
                updated_epoch=attitude.updated_epoch,
                locked=list(attitude.locked),
            )
            if attitude is not None
            else None,
            bloodline_rule=house.bloodline_rule if house is not None else None,
            sources=choices(await names_of(session, PowerSourceRow)),
            systems=choices(await names_of(session, MagicSystemRow)),
            grant_cost=rules.powers.grant_cost,
        )


async def source_views(session: AsyncSession, sources: list[PowerSourceRow], names: dict[int, str]) -> list[PowerSourceView]:
    ids = [row.id for row in sources]
    costs = list(await session.scalars(select(PowerSourceCostRow).where(PowerSourceCostRow.source_id.in_(ids)).order_by(PowerSourceCostRow.id)))
    resists = list(
        await session.scalars(select(PowerSourceResistanceRow).where(PowerSourceResistanceRow.source_id.in_(ids)).order_by(PowerSourceResistanceRow.id))
    )
    hazards = list(await session.scalars(select(PowerSourceHazardRow).where(PowerSourceHazardRow.source_id.in_(ids)).order_by(PowerSourceHazardRow.id)))
    tides = list(await session.scalars(select(SourceTideRow).where(SourceTideRow.source_id.in_(ids)).order_by(SourceTideRow.id)))
    meets = list(
        await session.scalars(
            select(PowerSourceInteractionRow).where(PowerSourceInteractionRow.first_source_id.in_(ids)).order_by(PowerSourceInteractionRow.id)
        )
    )
    refs = await node_refs(session, [row.scope_node_id for row in sources if row.scope_node_id is not None])
    return [
        PowerSourceView(
            id=row.id,
            name=row.name,
            description=row.description,
            scope=ref(refs, row.scope_node_id),
            drawn_from=row.drawn_from,
            renewal=row.renewal,
            access=row.access,
            visibility=row.visibility,
            stability=row.stability,
            built_in=row.built_in,
            founded_epoch=row.founded_epoch,
            locked=list(row.locked),
            costs=[SourceCostView(id=c.id, cost=c.cost, weight=c.weight, locked=list(c.locked)) for c in costs if c.source_id == row.id],
            resistances=[
                SourceResistanceView(id=r.id, resistance=r.resistance, material=r.material, locked=list(r.locked)) for r in resists if r.source_id == row.id
            ],
            hazards=[SourceHazardView(id=h.id, hazard=h.hazard, weight=h.weight, locked=list(h.locked)) for h in hazards if h.source_id == row.id],
            tides=[
                SourceTideView(id=t.id, cycle=t.cycle, period=t.period, amplitude=t.amplitude, phase=t.phase, locked=list(t.locked))
                for t in tides
                if t.source_id == row.id
            ],
            interactions=[
                SourceInteractionView(
                    id=m.id,
                    other_id=m.second_source_id,
                    other_name=names.get(m.second_source_id, ""),
                    relation=m.relation,
                    strength=m.strength,
                    locked=list(m.locked),
                )
                for m in meets
                if m.first_source_id == row.id
            ],
        )
        for row in sources
    ]


@router.get("/sources/of/{node_id}", response_model=SourcesNodeView)
async def node_sources(services: ServicesDep, node_id: NodeId) -> SourcesNodeView:
    async with reader(services) as session:
        await must_exist(session, node_id)
        names = await names_of(session, PowerSourceRow)
        here = list(await session.scalars(select(PowerSourceRow).where(PowerSourceRow.scope_node_id == node_id).order_by(PowerSourceRow.id)))
        densities = list(await session.scalars(select(SourceDensityRow).where(SourceDensityRow.region_entity_id == node_id).order_by(SourceDensityRow.id)))
        known = list(
            await session.scalars(select(PowerSourceKnowledgeRow).where(PowerSourceKnowledgeRow.holder_node_id == node_id).order_by(PowerSourceKnowledgeRow.id))
        )
        laws = list(await session.scalars(select(SourceLawRow).where(SourceLawRow.polity_entity_id == node_id).order_by(SourceLawRow.id)))
        stances = list(await session.scalars(select(SourceStanceRow).where(SourceStanceRow.cult_entity_id == node_id).order_by(SourceStanceRow.id)))
        doctrine = await session.get(CultDoctrineRow, node_id)
        refs = await node_refs(session, [node_id])
        return SourcesNodeView(
            node=refs[node_id],
            sources=await source_views(session, here, names),
            densities=[
                DensityView(
                    id=row.id,
                    source_id=row.source_id,
                    source_name=names.get(row.source_id, ""),
                    density=row.density,
                    base_density=row.base_density,
                    renewal_pct=row.renewal_pct,
                    last_drawn_epoch=row.last_drawn_epoch,
                    depleted=row.depleted,
                    locked=list(row.locked),
                )
                for row in densities
            ],
            knowledge=[
                SourceKnowledgeView(
                    id=row.id,
                    source_id=row.source_id,
                    source_name=names.get(row.source_id, ""),
                    level=row.level,
                    learned_epoch=row.learned_epoch,
                    locked=list(row.locked),
                )
                for row in known
            ],
            laws=[
                SourceLawView(id=row.id, source_id=row.source_id, source_name=names.get(row.source_id, ""), level=row.level, locked=list(row.locked))
                for row in laws
            ],
            stances=[
                SourceStanceView(id=row.id, source_id=row.source_id, source_name=names.get(row.source_id, ""), stance=row.stance, locked=list(row.locked))
                for row in stances
            ],
            power_stance=doctrine.power_stance if doctrine is not None else None,
            every_source=choices(names),
        )


@router.get("/magic-systems/of/{node_id}", response_model=MagicSystemsNodeView)
async def node_systems(services: ServicesDep, node_id: NodeId) -> MagicSystemsNodeView:
    async with reader(services) as session:
        await must_exist(session, node_id)
        systems = list(await session.scalars(select(MagicSystemRow).where(MagicSystemRow.scope_node_id == node_id).order_by(MagicSystemRow.id)))
        ids = [row.id for row in systems]
        sources, names = await names_of(session, PowerSourceRow), await names_of(session, MagicSystemRow)
        tied = list(await session.scalars(select(MagicSystemSourceRow).where(MagicSystemSourceRow.system_id.in_(ids)).order_by(MagicSystemSourceRow.id)))
        links = list(await session.scalars(select(MagicSystemLinkRow).where(MagicSystemLinkRow.first_system_id.in_(ids)).order_by(MagicSystemLinkRow.id)))
        grammar = list(await session.scalars(select(MagicSystemGrammarRow).where(MagicSystemGrammarRow.system_id.in_(ids)).order_by(MagicSystemGrammarRow.id)))
        limits = list(await session.scalars(select(SystemRestrictionRow).where(SystemRestrictionRow.system_id.in_(ids)).order_by(SystemRestrictionRow.id)))
        refs = await node_refs(session, [node_id])
        return MagicSystemsNodeView(
            node=refs[node_id],
            systems=[
                MagicSystemView(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    structure=row.structure,
                    predictability=row.predictability,
                    prevalence=row.prevalence,
                    cost_severity=row.cost_severity,
                    visibility=row.visibility,
                    access=row.access,
                    learnability=row.learnability,
                    founded_epoch=row.founded_epoch,
                    locked=list(row.locked),
                    sources=[
                        SystemSourceView(id=s.id, source_id=s.source_id, source_name=sources.get(s.source_id, ""), locked=list(s.locked))
                        for s in tied
                        if s.system_id == row.id
                    ],
                    links=[
                        SystemLinkView(
                            id=link.id,
                            other_id=link.second_system_id,
                            other_name=names.get(link.second_system_id, ""),
                            relation=link.relation,
                            locked=list(link.locked),
                        )
                        for link in links
                        if link.first_system_id == row.id
                    ],
                    grammar=[SystemGrammarView(id=g.id, technique=g.technique, form=g.form, locked=list(g.locked)) for g in grammar if g.system_id == row.id],
                    restrictions=[SystemRestrictionView(id=r.id, kind=r.kind, detail=r.detail, locked=list(r.locked)) for r in limits if r.system_id == row.id],
                )
                for row in systems
            ],
            every_system=choices(names),
            every_source=choices(sources),
        )


async def truth_views(session: AsyncSession, truths: list[HiddenTruthRow]) -> list[HiddenTruthView]:
    ids = [row.id for row in truths]
    keepers = list(await session.scalars(select(TruthKeeperRow).where(TruthKeeperRow.truth_id.in_(ids)).order_by(TruthKeeperRow.id)))
    seekers = list(await session.scalars(select(TruthSeekerRow).where(TruthSeekerRow.truth_id.in_(ids)).order_by(TruthSeekerRow.id)))
    known = list(await session.scalars(select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id.in_(ids)).order_by(PublicKnowledgeRow.id)))
    breaches = list(await session.scalars(select(BreachRow).where(BreachRow.truth_id.in_(ids)).order_by(BreachRow.id)))
    wanted = [*(t.subject_node_id for t in truths), *(t.scope_node_id for t in truths), *(k.keeper_node_id for k in keepers)]
    wanted += [*(s.seeker_node_id for s in seekers), *(k.population_node_id for k in known), *(b.place_node_id for b in breaches)]
    wanted += [node for b in breaches for node in b.witness_node_ids]
    refs = await node_refs(session, [node for node in wanted if node is not None])
    titles = {row.id: row.title for row in truths}
    return [
        HiddenTruthView(
            id=row.id,
            title=row.title,
            description=row.description,
            subject=refs[row.subject_node_id],
            kind=row.kind,
            hidden_from=row.hidden_from,
            scope=ref(refs, row.scope_node_id),
            strength=row.strength,
            methods=[method for method in TRUTH_METHODS if getattr(row, method)],
            sanity_cost=row.sanity_cost,
            revealed=row.revealed,
            founded_epoch=row.founded_epoch,
            tended_epoch=row.tended_epoch,
            locked=list(row.locked),
            keepers=[TruthKeeperView(id=k.id, keeper=refs[k.keeper_node_id], role=k.role, locked=list(k.locked)) for k in keepers if k.truth_id == row.id],
            seekers=[
                SeekerView(id=s.id, seeker=refs[s.seeker_node_id], aim=s.aim, progress=s.progress, began_epoch=s.began_epoch, locked=list(s.locked))
                for s in seekers
                if s.truth_id == row.id
            ],
            knowledge=[knowledge_view(k, refs, titles) for k in known if k.truth_id == row.id],
            breaches=[
                TruthBreachView(
                    id=b.id,
                    epoch=b.epoch,
                    cause=b.cause,
                    witnesses=[refs[node] for node in b.witness_node_ids if node in refs],
                    place=ref(refs, b.place_node_id),
                    spread=b.spread,
                    response=b.response,
                )
                for b in breaches
                if b.truth_id == row.id
            ],
        )
        for row in truths
    ]


def knowledge_view(row: PublicKnowledgeRow, refs: dict[int, NodeRef], titles: dict[int, str]) -> PublicKnowledgeView:
    return PublicKnowledgeView(
        id=row.id,
        truth_id=row.truth_id,
        truth_title=titles.get(row.truth_id, ""),
        population=refs[row.population_node_id],
        know_pct=row.know_pct,
        believe_pct=row.believe_pct,
        attitude=row.attitude,
        revealed_epoch=row.revealed_epoch,
        updated_epoch=row.updated_epoch,
        locked=list(row.locked),
    )


@router.get("/truths/of/{node_id}", response_model=TruthsNodeView)
async def node_truths(services: ServicesDep, node_id: NodeId) -> TruthsNodeView:
    async with reader(services) as session:
        await must_exist(session, node_id)
        about = list(await session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.subject_node_id == node_id).order_by(HiddenTruthRow.id)))
        kept_ids = select(TruthKeeperRow.truth_id).where(TruthKeeperRow.keeper_node_id == node_id)
        sought_ids = select(TruthSeekerRow.truth_id).where(TruthSeekerRow.seeker_node_id == node_id)
        kept = list(await session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.id.in_(kept_ids)).order_by(HiddenTruthRow.id)))
        sought = list(await session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.id.in_(sought_ids)).order_by(HiddenTruthRow.id)))
        here = list(await session.scalars(select(PublicKnowledgeRow).where(PublicKnowledgeRow.population_node_id == node_id).order_by(PublicKnowledgeRow.id)))
        titles = {row.id: row.title for row in await session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.id.in_([k.truth_id for k in here])))}
        refs = await node_refs(session, [node_id])
        return TruthsNodeView(
            node=refs[node_id],
            about=await truth_views(session, about),
            kept=await truth_views(session, kept),
            sought=await truth_views(session, sought),
            known_here=[knowledge_view(row, refs, titles) for row in here],
            methods=list(TRUTH_METHODS),
        )
