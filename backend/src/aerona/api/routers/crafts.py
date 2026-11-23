from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.crafts import (
    AffinityMaterialChoice,
    AffinityView,
    AidView,
    ChemicalWorksView,
    ClockView,
    CraftsNodeView,
    GroundView,
    HeldRightView,
    InsurancePolicyView,
    InsurerView,
    LinkView,
    NumberReadingView,
    NumbersView,
    RightLinkChoice,
    SpiritView,
    TechniqueChoice,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.techniques import TECHNIQUES
from aerona.core.errors import NotFoundError
from aerona.core.grammar import spoken
from aerona.db.tables.crafts import (
    AssistiveAidRow,
    CatchGroundRow,
    ChemicalWorksRow,
    EmotionSpiritRow,
    IncorporealRightRow,
    InsurancePolicyRow,
    InsurerRow,
    MaterialAffinityRow,
    NumberSystemRow,
    PublicClockRow,
    SympatheticLinkRow,
)
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import ResourceProfileRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.relations import ContestRow
from aerona.domain.enums.folk_knowledge import NumberReading
from aerona.domain.enums.node import NodeKind
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.distance import RegionAtlas

router = APIRouter(tags=["crafts"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def material_name(row: WorldMaterialRow) -> str:
    return row.name or (spoken(row.base_kind) if row.base_kind is not None else f"material of world {row.world_id}")


@router.get("/crafts/of/{node_id}", response_model=CraftsNodeView)
async def node_crafts(services: ServicesDep, node_id: NodeId) -> CraftsNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        folk = await people_of(session, entity) if entity is not None else None
        region_id = (await RegionAtlas.load(session)).top_region(node_id)
        near = [item for item in (node_id, region_id, entity.location_id if entity is not None else None) if item is not None]
        grounds = list(
            await session.scalars(
                select(CatchGroundRow)
                .where(or_(CatchGroundRow.source_entity_id == node_id, CatchGroundRow.region_entity_id.in_(near), CatchGroundRow.owner_node_id == node_id))
                .order_by(CatchGroundRow.source_entity_id, CatchGroundRow.region_entity_id)
            )
        )
        works = list(await session.scalars(select(ChemicalWorksRow).where(ChemicalWorksRow.settlement_entity_id == node_id).order_by(ChemicalWorksRow.product)))
        insurer = await session.get(InsurerRow, node_id)
        policies = list(
            await session.scalars(
                select(InsurancePolicyRow)
                .where(or_(InsurancePolicyRow.holder_node_id == node_id, InsurancePolicyRow.insurer_entity_id == node_id))
                .order_by(InsurancePolicyRow.id.desc())
            )
        )
        rights = list(
            await session.scalars(
                select(IncorporealRightRow)
                .where(
                    or_(
                        IncorporealRightRow.holder_node_id == node_id,
                        IncorporealRightRow.subject_node_id == node_id,
                        IncorporealRightRow.licensed_to_node_id == node_id,
                    )
                )
                .order_by(IncorporealRightRow.id.desc())
            )
        )
        aids = list(await session.scalars(select(AssistiveAidRow).where(AssistiveAidRow.holder_node_id == node_id).order_by(AssistiveAidRow.kind)))
        clock = await session.get(PublicClockRow, node_id)
        numbers = await session.get(NumberSystemRow, folk.id) if folk is not None else None
        profile = await session.get(ResourceProfileRow, node_id)
        world_id = entity.world_id if entity is not None else None
        materials = (
            list(await session.scalars(select(WorldMaterialRow).where(WorldMaterialRow.world_id == world_id).order_by(WorldMaterialRow.id)))
            if world_id is not None
            else []
        )
        mine = [profile.world_material_id] if profile is not None and profile.world_material_id is not None else [row.id for row in materials]
        affinities = list(
            await session.execute(
                select(MaterialAffinityRow, WorldMaterialRow)
                .join(WorldMaterialRow, WorldMaterialRow.id == MaterialAffinityRow.material_id)
                .where(MaterialAffinityRow.material_id.in_(mine))
                .order_by(MaterialAffinityRow.material_id, MaterialAffinityRow.school)
            )
        )
        links = list(
            await session.scalars(
                select(SympatheticLinkRow)
                .where(or_(SympatheticLinkRow.holder_node_id == node_id, SympatheticLinkRow.target_node_id == node_id))
                .order_by(SympatheticLinkRow.id.desc())
            )
        )
        spirits = list(await session.scalars(select(EmotionSpiritRow).where(EmotionSpiritRow.region_entity_id.in_(near)).order_by(EmotionSpiritRow.id.desc())))
        dishes = {
            int(key): name
            for key, name in await session.execute(
                select(DishRow.id, DishRow.name)
                .where(or_(DishRow.world_id == world_id, DishRow.id.in_([row.dish_id for row in rights if row.dish_id is not None])))
                .order_by(DishRow.id)
            )
        }
        known = sorted(
            set(await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == node_id))), key=lambda item: item.value
        )
        contests = list(
            await session.scalars(
                select(ContestRow).where(or_(ContestRow.challenger_node_id == node_id, ContestRow.defender_node_id == node_id)).order_by(ContestRow.id.desc())
            )
        )
        unions = list(
            await session.scalars(select(MarriageRow).where(or_(MarriageRow.first_id == node_id, MarriageRow.second_id == node_id)).order_by(MarriageRow.id))
        )
        contest_names = {
            int(key): name
            for key, name in await session.execute(
                select(NodeRow.id, NodeRow.name).where(
                    NodeRow.id.in_(
                        sorted(
                            {
                                *(side for row in contests for side in (row.challenger_node_id, row.defender_node_id)),
                                *(side for row in unions for side in (row.first_id, row.second_id)),
                            }
                        )
                    )
                )
            )
        }
        refs = await refs_of(
            session,
            [
                node_id,
                folk.id if folk is not None else None,
                region_id,
                *(item for row in grounds for item in (row.source_entity_id, row.region_entity_id, row.owner_node_id)),
                *(row.settlement_entity_id for row in works),
                *(item for row in policies for item in (row.insurer_entity_id, row.holder_node_id)),
                *(item for row in rights for item in (row.holder_node_id, row.subject_node_id, row.licensed_to_node_id)),
                *(item for row in links for item in (row.holder_node_id, row.target_node_id)),
                *(item for row in spirits for item in (row.region_entity_id, row.bound_by_node_id)),
            ],
        )
    return CraftsNodeView(
        node=ref(refs, node_id),
        people=at(refs, folk.id if folk is not None else None),
        region=at(refs, region_id),
        grounds=[
            GroundView(
                source=ref(refs, row.source_entity_id),
                region=ref(refs, row.region_entity_id),
                ground=row.ground,
                gear=row.gear,
                right=row.right,
                owner=at(refs, row.owner_node_id),
                effort=row.effort,
                collapse_at=row.collapse_at,
                collapsed=row.collapsed,
                last_catch=row.last_catch,
                first_stock=row.first_stock,
                stock=row.stock,
                locked=row.locked,
            )
            for row in grounds
        ],
        works=[
            ChemicalWorksView(
                settlement=ref(refs, row.settlement_entity_id),
                product=row.product,
                output=row.output,
                hazard=row.hazard,
                pollution=row.pollution,
                accidents=row.accidents,
                founded_epoch=row.founded_epoch,
                locked=row.locked,
            )
            for row in works
        ],
        insurer=InsurerView(
            insurer=ref(refs, insurer.insurer_entity_id),
            pool=insurer.pool,
            risk_belief=insurer.risk_belief,
            premium_pct=insurer.premium_pct,
            ruined=insurer.ruined,
            claims_seen=insurer.claims_seen,
            locked=insurer.locked,
        )
        if insurer is not None
        else None,
        policies=[
            InsurancePolicyView(
                id=row.id,
                insurer=ref(refs, row.insurer_entity_id),
                holder=ref(refs, row.holder_node_id),
                cover=row.cover,
                premium=row.premium,
                sum_insured=row.sum_insured,
                active=row.active,
                since_epoch=row.since_epoch,
                claims=row.claims,
                locked=row.locked,
            )
            for row in policies
        ],
        rights=[
            HeldRightView(
                id=row.id,
                holder=ref(refs, row.holder_node_id),
                kind=row.kind,
                subject=at(refs, row.subject_node_id),
                name=row.name,
                acquired=row.acquired,
                licensed_to=at(refs, row.licensed_to_node_id),
                dish_id=row.dish_id,
                dish=dishes.get(row.dish_id) if row.dish_id is not None else None,
                technique=row.technique,
                technique_label=TECHNIQUES[row.technique].label if row.technique is not None else None,
                contest_id=row.contest_id,
                marriage_id=row.marriage_id,
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in rights
        ],
        aids=[AidView(kind=row.kind, quality=row.quality, since_epoch=row.since_epoch, locked=row.locked) for row in aids],
        clock=ClockView(kind=clock.kind, precision=clock.precision, built_epoch=clock.built_epoch, locked=clock.locked) if clock is not None else None,
        numbers=NumbersView(
            base=numbers.base,
            notation=numbers.notation,
            zero=numbers.zero,
            numeracy=numbers.numeracy,
            numerology=[
                NumberReadingView(number=int(number), reading=NumberReading(reading))
                for number, reading in sorted(numbers.numerology.items(), key=lambda item: int(item[0]))
                if number.isdigit() and reading in set(NumberReading)
            ],
            locked=numbers.locked,
        )
        if numbers is not None
        else None,
        affinities=[
            AffinityView(material_id=row.material_id, material=material_name(stuff), school=row.school, mode=row.mode, power=row.power, locked=row.locked)
            for row, stuff in affinities
        ],
        links=[
            LinkView(
                id=row.id,
                holder=ref(refs, row.holder_node_id),
                target=ref(refs, row.target_node_id),
                token=row.token,
                strength=row.strength,
                obtained_epoch=row.obtained_epoch,
                locked=row.locked,
            )
            for row in links
        ],
        spirits=[
            SpiritView(
                id=row.id,
                region=ref(refs, row.region_entity_id),
                emotion=row.emotion,
                strength=row.strength,
                born_epoch=row.born_epoch,
                lifetime=row.lifetime,
                bound_by=at(refs, row.bound_by_node_id),
                locked=row.locked,
            )
            for row in spirits
        ],
        materials=[AffinityMaterialChoice(id=row.id, name=material_name(row)) for row in materials],
        dish_choices=[RightLinkChoice(id=key, name=name) for key, name in sorted(dishes.items())],
        technique_choices=[TechniqueChoice(technique=item, label=TECHNIQUES[item].label) for item in known],
        contest_choices=[
            RightLinkChoice(
                id=row.id,
                name=f"{contest_names.get(row.challenger_node_id, 'someone')} against {contest_names.get(row.defender_node_id, 'someone')}, epoch {row.epoch}",
            )
            for row in contests
        ],
        union_choices=[
            RightLinkChoice(id=row.id, name=f"{contest_names.get(row.first_id, 'someone')} and {contest_names.get(row.second_id, 'someone')}") for row in unions
        ],
    )
