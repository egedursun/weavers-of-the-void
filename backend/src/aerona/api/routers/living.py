from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import func, or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.living import (
    BankSampleView,
    GeneBankView,
    LineChoice,
    LineSourceView,
    LineTraitView,
    LivingLineView,
    LivingNodeView,
    LivingProfileView,
    LivingStancesView,
    SymbiontView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, LivingLineSourceRow, LivingLineTraitRow, LivingProfileRow, SymbiontRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType

router = APIRouter(tags=["living"])
NodeId = Annotated[int, Path(ge=1)]
NOT_A_BODY = "Only a mortal with a body can be cloned."
NOT_AN_ENTITY = "Gods, worlds and the heavens hold their life in their own nature and sections; only a thing of the world can carry a living profile."


def ref(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


@router.get("/living/of/{node_id}", response_model=LivingNodeView)
async def node_living(services: ServicesDep, node_id: NodeId) -> LivingNodeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        profile = await session.get(LivingProfileRow, node_id)
        lines = list(
            await session.scalars(
                select(LivingLineRow)
                .where(or_(LivingLineRow.owner_node_id == node_id, LivingLineRow.maker_node_id == node_id, LivingLineRow.species_entity_id == node_id))
                .order_by(LivingLineRow.id)
            )
        )
        ids = [line.id for line in lines]
        traits = list(await session.scalars(select(LivingLineTraitRow).where(LivingLineTraitRow.line_id.in_(ids)).order_by(LivingLineTraitRow.id)))
        sources = list(await session.scalars(select(LivingLineSourceRow).where(LivingLineSourceRow.line_id.in_(ids)).order_by(LivingLineSourceRow.id)))
        counts = dict(
            (
                await session.execute(
                    select(LivingProfileRow.line_id, func.count()).where(LivingProfileRow.line_id.in_(ids)).group_by(LivingProfileRow.line_id)
                )
            ).all()
        )
        symbionts = list(
            await session.scalars(
                select(SymbiontRow).where(or_(SymbiontRow.host_node_id == node_id, SymbiontRow.mind_node_id == node_id)).order_by(SymbiontRow.id)
            )
        )
        banks = list(
            await session.scalars(
                select(GeneBankRow)
                .where(or_(GeneBankRow.structure_entity_id == node_id, GeneBankRow.holder_node_id == node_id))
                .order_by(GeneBankRow.structure_entity_id)
            )
        )
        samples = list(
            await session.scalars(
                select(GeneBankSampleRow)
                .where(GeneBankSampleRow.bank_entity_id.in_([bank.structure_entity_id for bank in banks]))
                .order_by(GeneBankSampleRow.id)
            )
        )
        cloned = BondRow.kind == BondKind.CLONE_OF, BondRow.state == BondState.ACTIVE
        clone_of = list(await session.scalars(select(BondRow.target_node_id).where(*cloned, BondRow.source_node_id == node_id)))
        clones = list(await session.scalars(select(BondRow.source_node_id).where(*cloned, BondRow.target_node_id == node_id)))
        names = {int(row_id): str(name) for row_id, name in (await session.execute(select(LivingLineRow.id, LivingLineRow.name))).all()}
        wanted: list[int | None] = [node_id, *clone_of, *clones]
        if profile is not None:
            wanted += [profile.bonded_to_node_id, profile.designed_by_node_id]
        wanted += [node for line in lines for node in (line.owner_node_id, line.maker_node_id, line.species_entity_id)]
        wanted += [row.organism_node_id for row in sources] + [row.organism_node_id for row in samples]
        wanted += [node for row in symbionts for node in (row.host_node_id, row.mind_node_id)]
        wanted += [node for bank in banks for node in (bank.structure_entity_id, bank.holder_node_id)]
        refs = await node_refs(session, [node for node in wanted if node is not None])
        doctrine = await session.get(CultDoctrineRow, node_id)
        return LivingNodeView(
            node=refs[node_id],
            alive_reason=None if entity is not None else NOT_AN_ENTITY,
            clone_reason=None if entity is not None and entity.entity_type is EntityType.MORTAL else NOT_A_BODY,
            profile=LivingProfileView(
                line_id=profile.line_id,
                line_name=names.get(profile.line_id) if profile.line_id is not None else None,
                metabolism=profile.metabolism,
                feed_commodity=profile.feed_commodity,
                feed_per_season=profile.feed_per_season,
                growth_stage=profile.growth_stage,
                size_pct=profile.size_pct,
                regeneration=profile.regeneration,
                health=profile.health,
                temperament=profile.temperament,
                bonded_to=ref(refs, profile.bonded_to_node_id),
                bond=profile.bond,
                fertility=profile.fertility,
                lifespan_years=profile.lifespan_years,
                age_seasons=profile.age_seasons,
                designed_by=ref(refs, profile.designed_by_node_id),
                planted_epoch=profile.planted_epoch,
                locked=list(profile.locked),
            )
            if profile is not None
            else None,
            lines=[
                LivingLineView(
                    id=line.id,
                    name=line.name,
                    method=line.method,
                    outcome=line.outcome,
                    stability=line.stability,
                    generation=line.generation,
                    drift_pct=line.drift_pct,
                    fertility=line.fertility,
                    metabolism=line.metabolism,
                    owner=ref(refs, line.owner_node_id),
                    maker=ref(refs, line.maker_node_id),
                    species=ref(refs, line.species_entity_id),
                    drifted_from_id=line.drifted_from_id,
                    drifted_from_name=names.get(line.drifted_from_id) if line.drifted_from_id is not None else None,
                    licensed=line.licensed,
                    escaped=line.escaped,
                    founded_epoch=line.founded_epoch,
                    living_count=int(counts.get(line.id, 0)),
                    locked=list(line.locked),
                    traits=[
                        LineTraitView(id=row.id, trait=row.trait, strength=row.strength, side_effect=row.side_effect, locked=list(row.locked))
                        for row in traits
                        if row.line_id == line.id
                    ],
                    sources=[
                        LineSourceView(id=row.id, organism=refs[row.organism_node_id], locked=list(row.locked))
                        for row in sources
                        if row.line_id == line.id and row.organism_node_id in refs
                    ],
                )
                for line in lines
            ],
            symbionts=[
                SymbiontView(
                    id=row.id,
                    host=refs[row.host_node_id],
                    line_id=row.line_id,
                    line_name=names.get(row.line_id) if row.line_id is not None else None,
                    mind=ref(refs, row.mind_node_id),
                    placement=row.placement,
                    relation=row.relation,
                    strength=row.strength,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in symbionts
                if row.host_node_id in refs
            ],
            banks=[
                GeneBankView(
                    structure=refs[bank.structure_entity_id],
                    holder=ref(refs, bank.holder_node_id),
                    upkeep=bank.upkeep,
                    unpaid_epochs=bank.unpaid_epochs,
                    locked=list(bank.locked),
                    samples=[
                        BankSampleView(
                            id=row.id, organism=refs[row.organism_node_id], quality=row.quality, taken_epoch=row.taken_epoch, locked=list(row.locked)
                        )
                        for row in samples
                        if row.bank_entity_id == bank.structure_entity_id and row.organism_node_id in refs
                    ],
                )
                for bank in banks
                if bank.structure_entity_id in refs
            ],
            clone_of=[refs[node] for node in clone_of if node in refs],
            clones=[refs[node] for node in clones if node in refs],
            stances=LivingStancesView(
                living_craft_stance=doctrine.living_craft_stance, germline_stance=doctrine.germline_stance, clone_stance=doctrine.clone_stance
            )
            if doctrine is not None
            else None,
            every_line=[LineChoice(id=row_id, name=name) for row_id, name in sorted(names.items())],
        )
