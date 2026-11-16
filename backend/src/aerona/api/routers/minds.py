from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import func, or_, select

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.routers.foundations import current_epoch
from aerona.api.schemas.minds import (
    AugmentEffectView,
    AugmentsNodeView,
    AugmentView,
    CompanyHoldingView,
    CompanyPowerView,
    CompanyPresenceView,
    DataContentView,
    DataStoreView,
    DoctrineStancesView,
    EnclaveView,
    FabricationView,
    IntrusionView,
    MadeRealmView,
    MadeRelicView,
    MadeWorldNodeView,
    MindArchiveView,
    MindLawView,
    MindLineageView,
    MindMakingView,
    MindNodeView,
    MindSeatPartView,
    MindStateView,
    MindWillChangeView,
    NetworkGatewayView,
    NetworkMemberView,
    NetworkNodeView,
    NetworkOutageView,
    NetworkProfileView,
    PatternRightView,
    RecordTrustView,
    RemoteBodyView,
    ReplicatorLineView,
    ReplicatorPresenceView,
    SalvageView,
    ScarcityView,
    SubstrateView,
    SurveillanceView,
    TrustView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.made import (
    AugmentEffectRow,
    AugmentRow,
    CompanyHoldingRow,
    CompanyPresenceRow,
    DataStoreContentRow,
    DataStoreRow,
    EnclaveRow,
    FabricationRow,
    InformationTrustRow,
    IntrusionRow,
    MadeRealmRow,
    MadeRelicRow,
    MarketScarcityRow,
    PatternRightRow,
    PeopleSubstrateRow,
    ReplicatorLineRow,
    ReplicatorPresenceRow,
    SalvageSiteRow,
    SurveillanceProfileRow,
)
from aerona.db.tables.minds import SPEED_MAX, MindArchiveRow, MindMakingRow, MindProfileRow, MindSeatRow, MindStateRow, MindWillChangeRow, RemoteBodyRow
from aerona.db.tables.networks import NetworkGatewayRow, NetworkNodeRow, NetworkOutageRow, NetworkProfileRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.minds import MindSeat
from aerona.engine.augments import BEARER_TYPES
from aerona.engine.minds.profiles import profile_from, seed_for, world_of
from aerona.engine.minds.souls import soul_law
from aerona.engine.networks.book import running

router = APIRouter(tags=["minds"])
NodeId = Annotated[int, Path(ge=1)]
LINEAGE = (
    BondKind.COPY_OF,
    BondKind.MERGED_INTO,
    BondKind.DIVIDED_FROM,
    BondKind.TRANSFERRED_FROM,
    BondKind.RESTORED_FROM,
    BondKind.MADE_MIND_OF,
    BondKind.HOSTED_BY,
    BondKind.LINKED_WITH,
)


def ref(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


@router.get("/minds/of/{node_id}", response_model=MindNodeView)
async def node_mind(services: ServicesDep, node_id: NodeId) -> MindNodeView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError("No such thing.")
        profile = await session.get(MindProfileRow, node_id) or profile_from(node_id, await seed_for(session, rules, node), await current_epoch(session))
        seats = list(await session.scalars(select(MindSeatRow).where(MindSeatRow.mind_node_id == node_id).order_by(MindSeatRow.id)))
        states = list(
            await session.scalars(
                select(MindStateRow).where(or_(MindStateRow.mind_node_id == node_id, MindStateRow.owner_node_id == node_id)).order_by(MindStateRow.id)
            )
        )
        makings = list(await session.scalars(select(MindMakingRow).where(MindMakingRow.mind_node_id == node_id).order_by(MindMakingRow.id)))
        changes = list(await session.scalars(select(MindWillChangeRow).where(MindWillChangeRow.mind_node_id == node_id).order_by(MindWillChangeRow.id)))
        bonds = list(
            await session.scalars(
                select(BondRow).where(BondRow.kind.in_(LINEAGE), or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id)).order_by(BondRow.id)
            )
        )
        remote = list(
            await session.scalars(
                select(RemoteBodyRow)
                .where(or_(RemoteBodyRow.mind_node_id == node_id, RemoteBodyRow.body_node_id == node_id))
                .order_by(RemoteBodyRow.body_node_id)
            )
        )
        archive = await session.get(MindArchiveRow, node_id)
        world_id = await world_of(session, node_id)
        law = await soul_law(session, node_id) if world_id is not None and await session.get(WorldRow, world_id) is not None else None
        linked = [node_id, profile.seat_node_id, profile.made_by_node_id, world_id]
        linked += [row.part_node_id for row in seats]
        linked += [item for row in states for item in (row.mind_node_id, row.holder_node_id, row.owner_node_id)]
        linked += [row.maker_node_id for row in makings]
        linked += [item for row in bonds for item in (row.source_node_id, row.target_node_id)]
        linked += [item for row in remote for item in (row.body_node_id, row.mind_node_id)]
        linked += [archive.holder_node_id] if archive is not None else []
        refs = await node_refs(session, [item for item in linked if item is not None])
        return MindNodeView(
            node=refs[node_id],
            seat=profile.seat,
            seat_node=ref(refs, profile.seat_node_id),
            origin=profile.origin,
            will=profile.will,
            affect=profile.affect,
            purpose=profile.purpose,
            capacity=profile.capacity,
            speed_pct=profile.speed_pct,
            stability=profile.stability,
            fidelity_pct=profile.fidelity_pct,
            upkeep=profile.upkeep,
            upkeep_energy=profile.upkeep_energy,
            pausable=profile.pausable,
            copyable=profile.copyable,
            restorable=profile.restorable,
            mergeable=profile.mergeable,
            transferable=profile.transferable,
            dormant=profile.dormant,
            perfect_recall=profile.perfect_recall,
            souled=profile.souled,
            made_by=ref(refs, profile.made_by_node_id),
            maker_bond=profile.maker_bond,
            drift_pct=profile.drift_pct,
            run_epochs=profile.run_epochs,
            locked=list(profile.locked or []),
            seats=[
                MindSeatPartView(id=row.id, part=ref(refs, row.part_node_id), share_pct=row.share_pct, vital=row.vital, locked=list(row.locked))
                for row in seats
            ],
            states=[
                MindStateView(
                    id=row.id,
                    mind=ref(refs, row.mind_node_id),
                    taken_epoch=row.taken_epoch,
                    fidelity_pct=row.fidelity_pct,
                    holder=ref(refs, row.holder_node_id),
                    medium_kind=row.medium_kind,
                    sealed=row.sealed,
                    copies=row.copies,
                    owner=ref(refs, row.owner_node_id),
                    locked=list(row.locked),
                )
                for row in states
            ],
            makings=[
                MindMakingView(id=row.id, maker=ref(refs, row.maker_node_id), method=row.method, quality=row.quality, outcome=row.outcome, epoch=row.epoch)
                for row in makings
            ],
            will_changes=[MindWillChangeView(id=row.id, from_will=row.from_will, to_will=row.to_will, cause=row.cause, epoch=row.epoch) for row in changes],
            lineage=[
                MindLineageView(
                    kind=row.kind,
                    other=refs[row.target_node_id if row.source_node_id == node_id else row.source_node_id],
                    outgoing=row.source_node_id == node_id,
                    epoch=row.epoch,
                )
                for row in bonds
                if (row.target_node_id if row.source_node_id == node_id else row.source_node_id) in refs
            ],
            remote_bodies=[
                RemoteBodyView(
                    body=ref(refs, row.body_node_id),
                    mind=ref(refs, row.mind_node_id),
                    feedback_pct=row.feedback_pct,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in remote
            ],
            archive=MindArchiveView(
                holder=ref(refs, archive.holder_node_id),
                upkeep=archive.upkeep,
                access=archive.access,
                unpaid_epochs=archive.unpaid_epochs,
                locked=list(archive.locked),
            )
            if archive is not None
            else None,
            law=MindLawView(
                world=refs[world_id],
                made_minds=law.made_minds,
                made_mind_souls=law.made_mind_souls,
                soul_continuity=law.soul_continuity,
                locked=list(law.locked or []),
            )
            if law is not None and world_id is not None and world_id in refs
            else None,
            speed_max=SPEED_MAX,
            soul_grant_cost=rules.minds.soul_grant_cost,
        )


def member_view(refs: dict[int, NodeRef], row: NetworkNodeRow) -> NetworkMemberView:
    return NetworkMemberView(
        id=row.id,
        network=ref(refs, row.network_entity_id),
        member=ref(refs, row.member_node_id),
        role=row.role,
        dependency_pct=row.dependency_pct,
        security=row.security,
        joined_epoch=row.joined_epoch,
        locked=list(row.locked),
    )


@router.get("/networks/of/{node_id}", response_model=NetworkNodeView)
async def node_networks(services: ServicesDep, node_id: NodeId) -> NetworkNodeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        epoch = await current_epoch(session)
        profile = await session.get(NetworkProfileRow, node_id)
        members = list(await session.scalars(select(NetworkNodeRow).where(NetworkNodeRow.network_entity_id == node_id).order_by(NetworkNodeRow.id)))
        gateways = list(
            await session.scalars(
                select(NetworkGatewayRow)
                .where(or_(NetworkGatewayRow.first_network_id == node_id, NetworkGatewayRow.second_network_id == node_id))
                .order_by(NetworkGatewayRow.id)
            )
        )
        outages = list(
            await session.scalars(select(NetworkOutageRow).where(NetworkOutageRow.network_entity_id == node_id).order_by(NetworkOutageRow.id.desc()))
        )
        memberships = list(await session.scalars(select(NetworkNodeRow).where(NetworkNodeRow.member_node_id == node_id).order_by(NetworkNodeRow.id)))
        linked = [node_id, profile.owner_node_id if profile is not None else None]
        linked += [item for row in [*members, *memberships] for item in (row.network_entity_id, row.member_node_id)]
        linked += [item for row in gateways for item in (row.first_network_id, row.second_network_id, row.owner_node_id)]
        refs = await node_refs(session, [item for item in linked if item is not None])
        return NetworkNodeView(
            node=refs[node_id],
            profile=NetworkProfileView(
                carrier=profile.carrier,
                access=profile.access,
                carries_messages=profile.carries_messages,
                carries_records=profile.carries_records,
                carries_control=profile.carries_control,
                carries_money=profile.carries_money,
                carries_minds=profile.carries_minds,
                carries_opinion=profile.carries_opinion,
                capacity=profile.capacity,
                delay_days=profile.delay_days,
                security=profile.security,
                reliability=profile.reliability,
                curation=profile.curation,
                censorship=profile.censorship,
                owner=ref(refs, profile.owner_node_id),
                tech_level=profile.tech_level,
                down_until_epoch=profile.down_until_epoch,
                founded_epoch=profile.founded_epoch,
                running=running(profile, epoch),
                locked=list(profile.locked),
            )
            if profile is not None
            else None,
            members=[member_view(refs, row) for row in members],
            gateways=[
                NetworkGatewayView(
                    id=row.id,
                    first=ref(refs, row.first_network_id),
                    second=ref(refs, row.second_network_id),
                    toll=row.toll,
                    filter_pct=row.filter_pct,
                    owner=ref(refs, row.owner_node_id),
                    locked=list(row.locked),
                )
                for row in gateways
            ],
            outages=[NetworkOutageView(id=row.id, cause=row.cause, epoch=row.epoch, epochs=row.epochs, severity=row.severity) for row in outages],
            memberships=[member_view(refs, row) for row in memberships],
        )


@router.get("/augments/of/{node_id}", response_model=AugmentsNodeView)
async def node_augments(services: ServicesDep, node_id: NodeId) -> AugmentsNodeView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        bears = entity is not None and entity.entity_type in BEARER_TYPES
        reason = None if bears else "Only a being with a body bears augments; worlds, stars, gods and made things hold their parts in their own records."
        augments = list(await session.scalars(select(AugmentRow).where(AugmentRow.bearer_node_id == node_id).order_by(AugmentRow.id)))
        effects = list(
            await session.scalars(select(AugmentEffectRow).where(AugmentEffectRow.augment_id.in_([row.id for row in augments])).order_by(AugmentEffectRow.id))
        )
        refs = await node_refs(session, [node_id, *(row.installed_by_node_id for row in augments if row.installed_by_node_id is not None)])
        return AugmentsNodeView(
            node=refs[node_id],
            bears=bears,
            reason=reason,
            augments=[
                AugmentView(
                    id=row.id,
                    slot=row.slot,
                    part=row.part,
                    kind=row.kind,
                    make=row.make,
                    quality=row.quality,
                    upkeep=row.upkeep,
                    integration=row.integration,
                    strain=row.strain,
                    installed_by=ref(refs, row.installed_by_node_id),
                    installed_epoch=row.installed_epoch,
                    locked=list(row.locked),
                    effects=[
                        AugmentEffectView(id=effect.id, target=effect.target, target_key=effect.target_key, amount=effect.amount, locked=list(effect.locked))
                        for effect in effects
                        if effect.augment_id == row.id
                    ],
                )
                for row in augments
            ],
        )


@router.get("/made-world/of/{node_id}", response_model=MadeWorldNodeView)
async def node_made_world(services: ServicesDep, node_id: NodeId) -> MadeWorldNodeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        intrusions = list(
            await session.scalars(
                select(IntrusionRow)
                .where(or_(IntrusionRow.actor_node_id == node_id, IntrusionRow.target_node_id == node_id, IntrusionRow.blamed_node_id == node_id))
                .order_by(IntrusionRow.id.desc())
            )
        )
        stores = list(
            await session.scalars(
                select(DataStoreRow).where(or_(DataStoreRow.holder_node_id == node_id, DataStoreRow.owner_node_id == node_id)).order_by(DataStoreRow.id)
            )
        )
        contents = list(
            await session.scalars(
                select(DataStoreContentRow).where(DataStoreContentRow.store_id.in_([row.id for row in stores])).order_by(DataStoreContentRow.id)
            )
        )
        surveillance = await session.get(SurveillanceProfileRow, node_id)
        trust = await session.get(InformationTrustRow, node_id)
        company = await session.get(CompanyProfileRow, node_id)
        holdings = list(await session.scalars(select(CompanyHoldingRow).where(CompanyHoldingRow.company_entity_id == node_id).order_by(CompanyHoldingRow.id)))
        presences = list(
            await session.scalars(
                select(CompanyPresenceRow)
                .where(or_(CompanyPresenceRow.company_entity_id == node_id, CompanyPresenceRow.polity_entity_id == node_id))
                .order_by(CompanyPresenceRow.company_entity_id, CompanyPresenceRow.polity_entity_id)
            )
        )
        enclaves = list(await session.scalars(select(EnclaveRow).where(EnclaveRow.company_entity_id == node_id).order_by(EnclaveRow.settlement_entity_id)))
        enclave = await session.get(EnclaveRow, node_id)
        lines = list(
            await session.scalars(
                select(ReplicatorLineRow)
                .where(or_(ReplicatorLineRow.owner_node_id == node_id, ReplicatorLineRow.maker_node_id == node_id, ReplicatorLineRow.mind_node_id == node_id))
                .order_by(ReplicatorLineRow.id)
            )
        )
        line_presences = list(
            await session.scalars(
                select(ReplicatorPresenceRow).where(ReplicatorPresenceRow.line_id.in_([row.id for row in lines])).order_by(ReplicatorPresenceRow.id)
            )
        )
        here = list(
            await session.scalars(select(ReplicatorPresenceRow).where(ReplicatorPresenceRow.place_node_id == node_id).order_by(ReplicatorPresenceRow.id))
        )
        names = {
            row.id: row.name
            for row in await session.scalars(select(ReplicatorLineRow).where(ReplicatorLineRow.id.in_([row.line_id for row in [*here, *line_presences]])))
        }
        fabrication = await session.get(FabricationRow, node_id)
        scarcity = list(
            await session.scalars(select(MarketScarcityRow).where(MarketScarcityRow.settlement_entity_id == node_id).order_by(MarketScarcityRow.commodity))
        )
        patterns = list(await session.scalars(select(PatternRightRow).where(PatternRightRow.holder_node_id == node_id).order_by(PatternRightRow.id)))
        relic = await session.get(MadeRelicRow, node_id)
        salvage = await session.get(SalvageSiteRow, node_id)
        substrates = list(
            await session.scalars(select(PeopleSubstrateRow).where(PeopleSubstrateRow.people_entity_id == node_id).order_by(PeopleSubstrateRow.seat))
        )
        realms = list(
            await session.scalars(
                select(MadeRealmRow)
                .where(or_(MadeRealmRow.dimension_id == node_id, MadeRealmRow.host_node_id == node_id, MadeRealmRow.keeper_node_id == node_id))
                .order_by(MadeRealmRow.dimension_id)
            )
        )
        inside = {
            realm.dimension_id: int(
                await session.scalar(select(func.count()).where(MindProfileRow.seat == MindSeat.REALM, MindProfileRow.seat_node_id == realm.dimension_id)) or 0
            )
            for realm in realms
        }
        doctrine = await session.get(CultDoctrineRow, node_id)
        records = list(await session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == node_id).order_by(AccountRow.id.desc())))
        linked: list[int | None] = [node_id]
        linked += [item for row in records for item in (row.subject_node_id, row.author_node_id)]
        linked += [item for row in intrusions for item in (row.actor_node_id, row.target_node_id, row.blamed_node_id)]
        linked += [item for row in stores for item in (row.holder_node_id, row.owner_node_id)]
        linked += [row.subject_node_id for row in contents]
        linked += [company.headquarters_entity_id] if company is not None else []
        linked += [row.holding_node_id for row in holdings]
        linked += [item for row in presences for item in (row.company_entity_id, row.polity_entity_id)]
        linked += [item for row in [*enclaves, *([enclave] if enclave is not None else [])] for item in (row.settlement_entity_id, row.company_entity_id)]
        linked += [item for row in lines for item in (row.owner_node_id, row.maker_node_id, row.mind_node_id)]
        linked += [row.place_node_id for row in [*here, *line_presences]]
        linked += [row.holder_node_id for row in patterns]
        linked += [salvage.rights_holder_node_id] if salvage is not None else []
        linked += [item for row in realms for item in (row.dimension_id, row.host_node_id, row.keeper_node_id)]
        refs = await node_refs(session, [item for item in linked if item is not None])

        def presence(row: ReplicatorPresenceRow) -> ReplicatorPresenceView:
            return ReplicatorPresenceView(
                id=row.id,
                line_id=row.line_id,
                line_name=names.get(row.line_id, ""),
                place=ref(refs, row.place_node_id),
                mass=row.mass,
                growth=row.growth,
                locked=list(row.locked),
            )

        def enclave_view(row: EnclaveRow) -> EnclaveView:
            return EnclaveView(
                settlement=ref(refs, row.settlement_entity_id), company=ref(refs, row.company_entity_id), since_epoch=row.since_epoch, locked=list(row.locked)
            )

        return MadeWorldNodeView(
            node=refs[node_id],
            intrusions=[
                IntrusionView(
                    id=row.id,
                    actor=ref(refs, row.actor_node_id),
                    target=row.target,
                    target_node=ref(refs, row.target_node_id),
                    approach=row.approach,
                    aim=row.aim,
                    stealth=row.stealth,
                    detection=row.detection,
                    attribution=row.attribution,
                    blamed=ref(refs, row.blamed_node_id),
                    outcome=row.outcome,
                    epoch=row.epoch,
                    locked=list(row.locked),
                )
                for row in intrusions
            ],
            stores=[
                DataStoreView(
                    id=row.id,
                    holder=ref(refs, row.holder_node_id),
                    security=row.security,
                    owner=ref(refs, row.owner_node_id),
                    locked=list(row.locked),
                    contents=[
                        DataContentView(
                            id=item.id,
                            content=item.content,
                            subject=ref(refs, item.subject_node_id),
                            reference=item.reference,
                            epoch=item.epoch,
                            locked=list(item.locked),
                        )
                        for item in contents
                        if item.store_id == row.id
                    ],
                )
                for row in stores
            ],
            surveillance=SurveillanceView(
                capacity=surveillance.capacity,
                reach_pct=surveillance.reach_pct,
                focus=surveillance.focus,
                updated_epoch=surveillance.updated_epoch,
                locked=list(surveillance.locked),
            )
            if surveillance is not None
            else None,
            trust=TrustView(
                information_trust=trust.information_trust,
                shared_account_pct=trust.shared_account_pct,
                updated_epoch=trust.updated_epoch,
                locked=list(trust.locked),
            )
            if trust is not None
            else None,
            company=CompanyPowerView(
                charter=company.charter,
                headquarters=ref(refs, company.headquarters_entity_id),
                locked=list(company.locked or []),
                holdings=[CompanyHoldingView(id=row.id, holding=ref(refs, row.holding_node_id), kind=row.kind, locked=list(row.locked)) for row in holdings],
                presences=[
                    CompanyPresenceView(
                        company=ref(refs, row.company_entity_id),
                        polity=ref(refs, row.polity_entity_id),
                        licensed=row.licensed,
                        influence=row.influence,
                        locked=list(row.locked),
                    )
                    for row in presences
                ],
                enclaves=[enclave_view(row) for row in enclaves],
            )
            if company is not None
            else None,
            enclave=enclave_view(enclave) if enclave is not None else None,
            lines=[
                ReplicatorLineView(
                    id=row.id,
                    name=row.name,
                    scale=row.scale,
                    feedstock=row.feedstock,
                    output=row.output,
                    growth_pct=row.growth_pct,
                    error_pct=row.error_pct,
                    containment=row.containment,
                    kill_switch=row.kill_switch,
                    owner=ref(refs, row.owner_node_id),
                    maker=ref(refs, row.maker_node_id),
                    mind=ref(refs, row.mind_node_id),
                    stage=row.stage,
                    founded_epoch=row.founded_epoch,
                    locked=list(row.locked),
                    presences=[presence(item) for item in line_presences if item.line_id == row.id],
                )
                for row in lines
            ],
            presences=[presence(row) for row in here],
            fabrication=FabricationView(
                share_pct=fabrication.share_pct, dividend_pct=fabrication.dividend_pct, updated_epoch=fabrication.updated_epoch, locked=list(fabrication.locked)
            )
            if fabrication is not None
            else None,
            scarcity=[
                ScarcityView(commodity=row.commodity, scarcity=row.scarcity, updated_epoch=row.updated_epoch, locked=list(row.locked)) for row in scarcity
            ],
            patterns=[
                PatternRightView(
                    id=row.id,
                    commodity=row.commodity,
                    holder=ref(refs, row.holder_node_id),
                    licence_fee=row.licence_fee,
                    open=row.open,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in patterns
            ],
            relic=MadeRelicView(
                make_knowledge=relic.make_knowledge,
                repair_knowledge=relic.repair_knowledge,
                function_state=relic.function_state,
                understood_pct=relic.understood_pct,
                use=relic.use,
                is_relic=relic.is_relic,
                updated_epoch=relic.updated_epoch,
                locked=list(relic.locked),
            )
            if relic is not None
            else None,
            salvage=SalvageView(
                yield_left=salvage.yield_left,
                rights_holder=ref(refs, salvage.rights_holder_node_id),
                last_salvaged_epoch=salvage.last_salvaged_epoch,
                locked=list(salvage.locked),
            )
            if salvage is not None
            else None,
            substrates=[SubstrateView(seat=row.seat, origin=row.origin, share_pct=row.share_pct, locked=list(row.locked)) for row in substrates],
            realms=[
                MadeRealmView(
                    dimension=refs[row.dimension_id],
                    host=ref(refs, row.host_node_id),
                    keeper=ref(refs, row.keeper_node_id),
                    realm_purpose=row.realm_purpose,
                    time_ratio_pct=row.time_ratio_pct,
                    fidelity=row.fidelity,
                    entry=row.entry,
                    aware_inside=row.aware_inside,
                    upkeep=row.upkeep,
                    frozen_until_epoch=row.frozen_until_epoch,
                    sealed=row.sealed,
                    locked=list(row.locked),
                    minds_inside=inside[row.dimension_id],
                )
                for row in realms
                if row.dimension_id in refs
            ],
            doctrine=DoctrineStancesView(
                made_mind_stance=doctrine.made_mind_stance,
                copy_stance=doctrine.copy_stance,
                augment_stance=doctrine.augment_stance,
                made_afterlife_stance=doctrine.made_afterlife_stance,
                relic_stance=doctrine.relic_stance,
                locked=list(doctrine.locked or []),
            )
            if doctrine is not None
            else None,
            records=[
                RecordTrustView(
                    id=row.id,
                    kind=row.kind,
                    subject=ref(refs, row.subject_node_id),
                    author=ref(refs, row.author_node_id),
                    authenticity=row.authenticity,
                    credence=row.credence,
                    epoch=row.epoch,
                )
                for row in records
            ],
        )
