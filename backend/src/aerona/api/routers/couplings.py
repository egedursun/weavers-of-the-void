from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.couplings import (
    CarrionView,
    CouplingNodeView,
    ElderMemoryView,
    FieldAgreementView,
    HappeningChoice,
    NoveltyView,
    SealLinkChoice,
    SealView,
    SignOriginView,
    SinecureView,
    SociolectView,
    SpiritTeachingView,
    WarChoice,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.core.grammar import spoken
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.couplings import (
    CaptiveRestraintRow,
    CarrionPulseRow,
    DeepSealRow,
    FieldAgreementRow,
    NoveltyStockRow,
    RiteComponentRow,
    SignOriginRow,
    SociolectRow,
    TeachingRow,
)
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.discovery import ArtFormProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import OathRow, OfficeRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.warfare import CaptiveRow, WarRow, WarSideRow
from aerona.domain.enums.collective import AccountKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.polity import OathStatus
from aerona.domain.enums.powers import PowerState
from aerona.domain.enums.war import CaptiveStatus, WarStatus
from aerona.engine.couplings.teachers import learners_of
from aerona.engine.lore.tellings import node_names
from aerona.engine.primitives.manual import manual_context

router = APIRouter(tags=["couplings"])
NodeId = Annotated[int, Path(ge=1)]
TEACHERS = (EntityType.SPIRIT, EntityType.BEAST)
PLACES = (EntityType.PLACE, EntityType.RESOURCE, EntityType.REGION, EntityType.SETTLEMENT)
HAPPENINGS_OFFERED = 40


@dataclass(frozen=True)
class SealChoices:
    oaths: list[SealLinkChoice]
    powers: list[SealLinkChoice]
    lines: list[SealLinkChoice]
    minds: list[SealLinkChoice]


async def seal_links(session: AsyncSession) -> SealChoices:
    oaths = list(await session.scalars(select(OathRow).where(OathRow.status == OathStatus.SWORN).order_by(OathRow.id.desc())))
    powers = list(await session.scalars(select(PowerRow).where(PowerRow.state == PowerState.ACTIVE).order_by(PowerRow.strength.desc(), PowerRow.id)))
    lines = list(await session.scalars(select(LivingLineRow).where(LivingLineRow.escaped.is_(False)).order_by(LivingLineRow.id)))
    minds = list(await session.scalars(select(MindProfileRow.node_id).where(MindProfileRow.dormant.is_(False)).order_by(MindProfileRow.node_id)))
    names = await node_names(session, [row.swearer_entity_id for row in oaths] + [row.holder_node_id for row in powers] + minds)
    return SealChoices(
        oaths=[SealLinkChoice(id=row.id, label=f"{names.get(row.swearer_entity_id, 'Someone')}'s oath of {spoken(row.kind)}") for row in oaths],
        powers=[SealLinkChoice(id=row.id, label=f"{names.get(row.holder_node_id, 'Someone')}'s power of {spoken(row.form)}") for row in powers],
        lines=[SealLinkChoice(id=row.id, label=row.name) for row in lines],
        minds=[SealLinkChoice(id=mind, label=names.get(mind, "A made mind")) for mind in minds],
    )


@router.get("/couplings/of/{node_id}", response_model=CouplingNodeView)
async def node_couplings(services: ServicesDep, node_id: NodeId) -> CouplingNodeView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        entity = await session.get(EntityRow, node.id)
        kind = entity.entity_type if entity is not None else None
        captive = await session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == node.id, CaptiveRow.status == CaptiveStatus.HELD).limit(1))
        sociolects = list(
            await session.scalars(
                select(SociolectRow).where(or_(SociolectRow.holder_entity_id == node.id, SociolectRow.language_entity_id == node.id)).order_by(SociolectRow.id)
            )
        )
        signs = list(
            await session.scalars(
                select(SignOriginRow)
                .where(or_(SignOriginRow.community_entity_id == node.id, SignOriginRow.language_entity_id == node.id))
                .order_by(SignOriginRow.language_entity_id)
            )
        )
        teachings = list(
            await session.scalars(
                select(TeachingRow).where(or_(TeachingRow.teacher_node_id == node.id, TeachingRow.learner_entity_id == node.id)).order_by(TeachingRow.id)
            )
        )
        agreements = list(
            await session.scalars(
                select(FieldAgreementRow)
                .where(
                    or_(
                        FieldAgreementRow.commander_entity_id == node.id,
                        FieldAgreementRow.counterpart_entity_id == node.id,
                        FieldAgreementRow.place_entity_id == node.id,
                    )
                )
                .order_by(FieldAgreementRow.id)
            )
        )
        seals = list(await session.scalars(select(DeepSealRow).where(DeepSealRow.place_entity_id == node.id).order_by(DeepSealRow.id)))
        links = await seal_links(session)
        sinecures = list(
            await session.scalars(select(OfficeRow).where(OfficeRow.polity_entity_id == node.id, OfficeRow.sinecure.is_(True)).order_by(OfficeRow.id))
        )
        memories = list(
            await session.scalars(
                select(AccountRow).where(AccountRow.holder_entity_id == node.id, AccountRow.kind == AccountKind.ELDER_MEMORY).order_by(AccountRow.id)
            )
        )
        collections = {
            row.id: row.name
            for row in await session.scalars(
                select(CollectionRow).where(CollectionRow.id.in_([memory.collection_id for memory in memories if memory.collection_id]))
            )
        }
        offered = list(
            await session.scalars(
                select(CollectionRow)
                .where(CollectionRow.world_id == (entity.world_id if entity is not None else None))
                .order_by(CollectionRow.start_epoch.desc(), CollectionRow.id.desc())
                .limit(HAPPENINGS_OFFERED)
            )
        )
        if kind in TEACHERS and entity is not None:
            partners = await learners_of(await manual_context(session, "couplings_view", rules), entity)
        elif kind in COMMUNITY_TYPES and entity is not None and entity.location_id is not None:
            partners = list(
                await session.scalars(
                    select(EntityRow)
                    .where(EntityRow.location_id == entity.location_id, EntityRow.entity_type.in_(TEACHERS), EntityRow.status == EntityStatus.CANON)
                    .order_by(EntityRow.id)
                )
            )
        else:
            partners = []
        sides = select(WarSideRow.war_id).where(WarSideRow.entity_id == node.id, WarSideRow.left_epoch.is_(None))
        wars = list(await session.scalars(select(WarRow).where(WarRow.id.in_(sides), WarRow.status != WarStatus.ENDED).order_by(WarRow.id)))
        war_names = await node_refs(session, [war.event_entity_id for war in wars])
        linked = [
            *[node for row in sociolects for node in (row.language_entity_id, row.holder_entity_id)],
            *[node for row in signs for node in (row.language_entity_id, row.community_entity_id) if node is not None],
            *[node for row in teachings for node in (row.teacher_node_id, row.learner_entity_id, row.subject_node_id) if node is not None],
            *[node for row in agreements for node in (row.commander_entity_id, row.counterpart_entity_id, row.place_entity_id) if node is not None],
            *[row.sealer_node_id for row in seals if row.sealer_node_id is not None],
            *[row.holder_entity_id for row in sinecures if row.holder_entity_id is not None],
            *[partner.id for partner in partners],
            node.id,
        ]
        refs = await node_refs(session, linked)
        carrion = await session.get(CarrionPulseRow, node.id)
        novelty = await session.get(NoveltyStockRow, node.id)
        fashion = (
            await session.get(ArtFormProfileRow, node.id) is not None
            or await session.scalar(select(DishRow.id).where(DishRow.entity_id == node.id)) is not None
        )
        return CouplingNodeView(
            node=refs[node.id],
            is_rite=await session.get(RiteProfileRow, node.id) is not None,
            rite_parts=sorted(await session.scalars(select(RiteComponentRow.component).where(RiteComponentRow.rite_entity_id == node.id))),
            captive_id=captive.id if captive is not None else None,
            restraints=sorted(await session.scalars(select(CaptiveRestraintRow.restraint).where(CaptiveRestraintRow.captive_id == captive.id)))
            if captive is not None
            else [],
            is_community=kind in COMMUNITY_TYPES,
            is_region=kind is EntityType.REGION,
            is_teacher=kind in TEACHERS,
            is_beast=kind is EntityType.BEAST,
            is_place=kind in PLACES,
            is_fashion=fashion,
            is_realm=kind is EntityType.POLITY,
            sociolects=[
                SociolectView(
                    id=row.id,
                    language=refs.get(row.language_entity_id),
                    holder=refs.get(row.holder_entity_id),
                    kind=row.kind,
                    prestige=row.prestige,
                    secret=row.secret,
                    salience=row.salience,
                    since_epoch=row.since_epoch,
                    faded_epoch=row.faded_epoch,
                    locked=row.locked,
                )
                for row in sociolects
            ],
            signs=[
                SignOriginView(
                    language=refs[row.language_entity_id],
                    community=refs.get(row.community_entity_id) if row.community_entity_id is not None else None,
                    cause=row.cause,
                    since_epoch=row.since_epoch,
                    locked=row.locked,
                )
                for row in signs
                if row.language_entity_id in refs
            ],
            carrion=CarrionView(
                carrion=carrion.carrion,
                scavenged=carrion.scavenged,
                preserved=carrion.preserved,
                rest=carrion.rest,
                kept=carrion.kept,
                epoch=carrion.epoch,
                locked=carrion.locked,
            )
            if carrion is not None
            else None,
            teachings=[
                SpiritTeachingView(
                    id=row.id,
                    teacher=refs.get(row.teacher_node_id),
                    learner=refs.get(row.learner_entity_id),
                    kind=row.kind,
                    subject=refs.get(row.subject_node_id) if row.subject_node_id is not None else None,
                    fidelity=row.fidelity,
                    state=row.state,
                    price=row.price,
                    epoch=row.epoch,
                    locked=row.locked,
                )
                for row in teachings
            ],
            partners=[refs[partner.id] for partner in partners if partner.id in refs],
            memories=[
                ElderMemoryView(
                    id=row.id,
                    happening=collections.get(row.collection_id) if row.collection_id is not None else None,
                    fidelity=row.fidelity,
                    credence=row.credence,
                    epoch=row.epoch,
                )
                for row in memories
            ],
            happenings=[HappeningChoice(id=row.id, name=row.name) for row in offered],
            agreements=[
                FieldAgreementView(
                    id=row.id,
                    war_id=row.war_id,
                    kind=row.kind,
                    state=row.state,
                    commander=refs.get(row.commander_entity_id) if row.commander_entity_id is not None else None,
                    counterpart=refs.get(row.counterpart_entity_id) if row.counterpart_entity_id is not None else None,
                    place=refs.get(row.place_entity_id) if row.place_entity_id is not None else None,
                    term_epoch=row.term_epoch,
                    honour=row.honour,
                    epoch=row.epoch,
                    ended_epoch=row.ended_epoch,
                    locked=row.locked,
                )
                for row in agreements
            ],
            wars=[WarChoice(id=war.id, name=war_names[war.event_entity_id].name if war.event_entity_id in war_names else "a war") for war in wars],
            seals=[
                SealView(
                    id=row.id,
                    kind=row.kind,
                    strength=row.strength,
                    decay=row.decay,
                    sealer=refs.get(row.sealer_node_id) if row.sealer_node_id is not None else None,
                    epoch=row.epoch,
                    broken_epoch=row.broken_epoch,
                    pact_oath_id=row.pact_oath_id,
                    power_id=row.power_id,
                    living_line_id=row.living_line_id,
                    made_mind_id=row.made_mind_id,
                    locked=row.locked,
                )
                for row in seals
            ],
            oath_choices=links.oaths,
            power_choices=links.powers,
            line_choices=links.lines,
            mind_choices=links.minds,
            novelty=NoveltyView(
                novelty=novelty.novelty,
                adoption=novelty.adoption,
                peak_epoch=novelty.peak_epoch,
                revivals=novelty.revivals,
                updated_epoch=novelty.updated_epoch,
                locked=novelty.locked,
            )
            if novelty is not None
            else None,
            sinecures=[
                SinecureView(id=row.id, holder=refs.get(row.holder_entity_id) if row.holder_entity_id is not None else None, since_epoch=row.since_epoch)
                for row in sinecures
            ],
        )
