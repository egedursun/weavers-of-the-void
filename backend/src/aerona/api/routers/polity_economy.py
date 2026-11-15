from collections import Counter, defaultdict
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import func, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.polity_economy import MemberOutputView, PactView, PolityChainStepView, PolityProductionView, PolityStockView
from aerona.catalog.production import CHAIN_STEPS
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.economy import CommunityStockRow, ProductionRunRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, TreatyClauseRow, TreatyProfileRow
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.polity import ClauseKind
from aerona.engine.primitives.numbers import round_half_up

router = APIRouter(tags=["economy"])
Id = Annotated[int, Path(ge=1)]


@router.get("/resources/{resource_id}/pacts", response_model=list[PactView])
async def resource_pacts(services: ServicesDep, resource_id: Id) -> list[PactView]:
    async with reader(services) as session:
        resource = await session.get(EntityRow, resource_id)
        if resource is None or resource.entity_type is not EntityType.RESOURCE:
            raise NotFoundError("No such resource.")
        rows = list(
            await session.execute(
                select(TreatyClauseRow, TreatyProfileRow, EntityRow)
                .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
                .join(EntityRow, EntityRow.id == TreatyClauseRow.treaty_entity_id)
                .where(TreatyClauseRow.kind == ClauseKind.RESOURCE_DEMAND, TreatyClauseRow.beneficiary_node_id == resource_id)
                .order_by(TreatyProfileRow.signed_epoch.desc(), TreatyClauseRow.id.desc())
            )
        )
        keepers = [clause.obligor_node_id for clause, _, _ in rows if clause.obligor_node_id is not None]
        owners = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(keepers)))} if keepers else {}
        views: list[PactView] = []
        for clause, profile, treaty in rows:
            params = clause.params or {}
            wanted = str(params.get("commodity") or "")
            views.append(
                PactView(
                    treaty_id=treaty.id,
                    name=treaty.name,
                    status=profile.status,
                    owner_id=clause.obligor_node_id,
                    owner_name=owners.get(clause.obligor_node_id, "") if clause.obligor_node_id is not None else "",
                    demand=str(params.get("demand") or ""),
                    commodity=CommodityKind(wanted) if wanted in CommodityKind._value2member_map_ else None,
                    units=int(params.get("units", 0)),
                    cost=int(params.get("cost", 0)),
                    every=int(params.get("every", 1)),
                    paid_epoch=int(params.get("paid_epoch", profile.signed_epoch)),
                    signed_epoch=profile.signed_epoch,
                    until_epoch=profile.until_epoch,
                    misread=bool(params.get("misread", False)),
                )
            )
        return views


@router.get("/polities/{polity_id}/production", response_model=PolityProductionView)
async def polity_production(services: ServicesDep, polity_id: Id) -> PolityProductionView:
    async with reader(services) as session:
        polity = await session.get(EntityRow, polity_id)
        if polity is None or polity.entity_type is not EntityType.POLITY:
            raise NotFoundError("No such polity.")
        cosmos = await CosmosRepository(session).get()
        member_ids = list(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))
        members = [
            row
            for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(member_ids)).order_by(EntityRow.id))
            if row.entity_type in SOCIETY_TYPES
        ]
        ids = [row.id for row in members]
        workshops: dict[int, set[WorkshopKind]] = defaultdict(set)
        levels: Counter[str] = Counter()
        for shop in await session.scalars(select(WorkshopRow).where(WorkshopRow.community_entity_id.in_(ids))):
            workshops[shop.community_entity_id].add(shop.kind)
            levels[shop.kind.value] += shop.level
        latest = {
            community: epoch
            for community, epoch in await session.execute(
                select(ProductionRunRow.community_entity_id, func.max(ProductionRunRow.epoch))
                .where(ProductionRunRow.community_entity_id.in_(ids))
                .group_by(ProductionRunRow.community_entity_id)
            )
        }
        runs: dict[str, list[ProductionRunRow]] = defaultdict(list)
        output: Counter[int] = Counter()
        starved: Counter[int] = Counter()
        for community, epoch in latest.items():
            for run in await session.scalars(
                select(ProductionRunRow).where(ProductionRunRow.community_entity_id == community, ProductionRunRow.epoch == epoch).order_by(ProductionRunRow.id)
            ):
                runs[run.step].append(run)
                output[community] += run.quantity
                starved[community] += run.bottleneck is not None
        chain: list[PolityChainStepView] = []
        for step in CHAIN_STEPS:
            done = runs.get(step.key, [])
            blocked = Counter(run.bottleneck for run in done if run.bottleneck is not None)
            chain.append(
                PolityChainStepView(
                    key=step.key,
                    label=step.label,
                    workshop=step.workshop,
                    inputs={commodity.value: amount for commodity, amount in step.inputs},
                    output=step.output,
                    output_qty=step.output_qty,
                    made=sum(run.quantity for run in done),
                    quality=max((run.quality for run in done if run.quantity), default=0),
                    material=next((run.material for run in done if run.material is not None), None),
                    bottleneck=max(blocked, key=lambda kind: (blocked[kind], kind.value)) if blocked else None,
                    starved_ids=sorted({run.community_entity_id for run in done if run.bottleneck is not None}),
                    running_ids=sorted({run.community_entity_id for run in done if run.quantity > 0}),
                    able_ids=[member for member in ids if step.workshop is None or step.workshop in workshops[member]],
                )
            )
        totals: Counter[CommodityKind] = Counter()
        weighted: Counter[CommodityKind] = Counter()
        for lot in await session.scalars(select(CommunityStockRow).where(CommunityStockRow.community_entity_id.in_(ids), CommunityStockRow.quantity > 0)):
            totals[lot.commodity] += lot.quantity
            weighted[lot.commodity] += lot.quantity * lot.quality
        return PolityProductionView(
            polity_id=polity.id,
            name=polity.name,
            epoch=cosmos.epoch if cosmos is not None else 0,
            members=[
                MemberOutputView(
                    community_id=row.id,
                    name=row.name,
                    epoch=latest.get(row.id),
                    made=output[row.id],
                    bottlenecks=starved[row.id],
                    workshops=len(workshops[row.id]),
                )
                for row in members
            ],
            chain=chain,
            stocks=[
                PolityStockView(commodity=kind, quantity=totals[kind], quality=round_half_up(weighted[kind] / totals[kind]))
                for kind in CommodityKind
                if totals[kind] > 0
            ],
            workshops=dict(sorted(levels.items())),
        )
