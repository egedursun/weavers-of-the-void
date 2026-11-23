from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.arcana import (
    ChargeView,
    CosmicOfficeView,
    GeasView,
    GrammarView,
    HeroquestView,
    LabTextView,
    LongevityView,
    MantlingView,
    NodeArcanaView,
    NodeMythicView,
    ServitorView,
    UpkeepView,
    VisView,
    WarpingView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.mythic import trial_at
from aerona.core.errors import NotFoundError
from aerona.db.tables.arcana import LabTextRow, LawUpkeepRow, LongevityRow, RiteGrammarRow, VisStockRow, WarpingRow
from aerona.db.tables.culture import ItemEnchantmentRow, LegendProfileRow
from aerona.db.tables.mythic import CosmicOfficeRow, GeasRow, HeroquestMemberRow, HeroquestRow, MantlingRow, ServitorRow
from aerona.db.tables.nature_kinds import DivineOfficeKindRow, RealmKindRow
from aerona.domain.enums.mythic import CosmicOffice, HeroquestState, OfficeChoice
from aerona.engine.kinds.nature import office_duty

router = APIRouter(tags=["arcana"])
Id = Annotated[int, Path(ge=1)]


async def refs_for(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, [value for value in ids if value is not None])


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def upkeep_views(session: AsyncSession, rows: list[LawUpkeepRow]) -> list[UpkeepView]:
    refs = await refs_for(session, [value for row in rows for value in (row.law_entity_id, row.caster_node_id)])
    return [
        UpkeepView(
            law=at(refs, row.law_entity_id),
            caster=at(refs, row.caster_node_id),
            source=row.source,
            essence_upkeep=row.essence_upkeep,
            vis_form=row.vis_form,
            vis_upkeep=row.vis_upkeep,
            dispel_resistance=row.dispel_resistance,
            unpaid_epochs=row.unpaid_epochs,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def text_views(session: AsyncSession, rows: list[LabTextRow]) -> list[LabTextView]:
    refs = await refs_for(session, [value for row in rows for value in (row.book_entity_id, row.rite_entity_id, row.author_entity_id)])
    return [
        LabTextView(
            book=at(refs, row.book_entity_id),
            rite=at(refs, row.rite_entity_id),
            author=at(refs, row.author_entity_id),
            fidelity=row.fidelity,
            epoch=row.epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def grammar_view(session: AsyncSession, row: RiteGrammarRow | None) -> GrammarView | None:
    if row is None:
        return None
    refs = await refs_for(session, [row.paradigm_entity_id, row.myth_entity_id])
    return GrammarView(
        technique=row.technique,
        form=row.form,
        range=row.range,
        duration=row.duration,
        target=row.target,
        condition=row.condition,
        condition_act=row.condition_act,
        condition_epoch=row.condition_epoch,
        difficulty=row.difficulty,
        paradigm=at(refs, row.paradigm_entity_id),
        myth=at(refs, row.myth_entity_id),
        locked=list(row.locked),
    )


@router.get("/arcana/of/{node_id}", response_model=NodeArcanaView)
async def node_arcana(services: ServicesDep, node_id: Id) -> NodeArcanaView:
    async with reader(services) as session:
        node = (await node_refs(session, [node_id])).get(node_id)
        if node is None:
            raise NotFoundError("No such node.")
        texts = list(
            await session.scalars(
                select(LabTextRow)
                .where(or_(LabTextRow.rite_entity_id == node_id, LabTextRow.book_entity_id == node_id, LabTextRow.author_entity_id == node_id))
                .order_by(LabTextRow.epoch.desc(), LabTextRow.book_entity_id)
            )
        )
        vis = await session.scalars(select(VisStockRow).where(VisStockRow.holder_node_id == node_id).order_by(VisStockRow.form))
        warping = await session.get(WarpingRow, node_id)
        longevity = await session.get(LongevityRow, node_id)
        charges = await session.scalars(select(ItemEnchantmentRow).where(ItemEnchantmentRow.item_entity_id == node_id).order_by(ItemEnchantmentRow.effect))
        upkeep = await session.get(LawUpkeepRow, node_id)
        kept = list(await session.scalars(select(LawUpkeepRow).where(LawUpkeepRow.caster_node_id == node_id).order_by(LawUpkeepRow.law_entity_id)))
        return NodeArcanaView(
            node=node,
            grammar=await grammar_view(session, await session.get(RiteGrammarRow, node_id)),
            lab_texts=await text_views(session, texts),
            vis=[VisView(form=row.form, amount=row.amount, locked=list(row.locked)) for row in vis],
            warping=WarpingView.model_validate(warping) if warping is not None else None,
            longevity=LongevityView.model_validate(longevity) if longevity is not None else None,
            charges=[
                ChargeView(effect=row.effect, strength=row.strength, charges=row.charges, capacity=row.capacity, recharge=row.recharge, overuse=row.overuse)
                for row in charges
            ],
            upkeep=(await upkeep_views(session, [upkeep]))[0] if upkeep is not None else None,
            kept=await upkeep_views(session, kept),
        )


async def quest_views(session: AsyncSession, rows: list[HeroquestRow]) -> list[HeroquestView]:
    ids = [row.id for row in rows]
    members = list(await session.scalars(select(HeroquestMemberRow).where(HeroquestMemberRow.heroquest_id.in_(ids)))) if ids else []
    refs = await refs_for(
        session,
        [
            *(value for row in rows for value in (row.quester_entity_id, row.legend_entity_id, row.god_node_id, row.place_entity_id)),
            *(item.entity_id for item in members),
        ],
    )
    legends = [row.legend_entity_id for row in rows if row.legend_entity_id is not None]
    found = select(LegendProfileRow.legend_entity_id, LegendProfileRow.archetype).where(LegendProfileRow.legend_entity_id.in_(legends))
    archetypes = {legend_id: archetype for legend_id, archetype in await session.execute(found)} if legends else {}
    realm_ids = [row.realm_kind_id for row in rows if row.realm_kind_id is not None]
    realm_names = {kind.id: kind.name for kind in await session.scalars(select(RealmKindRow).where(RealmKindRow.id.in_(realm_ids)))}
    return [
        HeroquestView(
            id=row.id,
            quester=at(refs, row.quester_entity_id),
            legend=at(refs, row.legend_entity_id),
            god=at(refs, row.god_node_id),
            realm=row.realm,
            realm_kind_id=row.realm_kind_id,
            realm_kind_name=realm_names.get(row.realm_kind_id) if row.realm_kind_id is not None else None,
            place=at(refs, row.place_entity_id),
            steps=row.steps,
            step=row.step,
            fidelity=row.fidelity,
            deviated=row.deviated,
            state=row.state,
            boon=row.boon,
            interference=row.interference,
            trial=row.trial,
            next_trial=row.trial or trial_at(archetypes.get(row.legend_entity_id) if row.legend_entity_id is not None else None, row.step)
            if row.state is HeroquestState.QUESTING
            else None,
            members=[refs[item.entity_id] for item in members if item.heroquest_id == row.id and item.entity_id in refs],
            start_epoch=row.start_epoch,
            end_epoch=row.end_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def mantling_views(session: AsyncSession, rows: list[MantlingRow]) -> list[MantlingView]:
    refs = await refs_for(session, [value for row in rows for value in (row.mortal_entity_id, row.god_node_id)])
    return [
        MantlingView(
            mortal=at(refs, row.mortal_entity_id),
            god=at(refs, row.god_node_id),
            deeds=row.deeds,
            worship=row.worship,
            progress=row.progress,
            state=row.state,
            blocked=row.blocked,
            notified=row.notified,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def servitor_views(session: AsyncSession, rows: list[ServitorRow]) -> list[ServitorView]:
    refs = await refs_for(
        session, [value for row in rows for value in (row.spirit_entity_id, row.god_node_id, row.post_entity_id, row.fallen_to_node_id, row.former_god_node_id)]
    )
    return [
        ServitorView(
            spirit=at(refs, row.spirit_entity_id),
            god=at(refs, row.god_node_id),
            origin=row.origin,
            role=row.role,
            post=at(refs, row.post_entity_id),
            loyalty=row.loyalty,
            fallen_to=at(refs, row.fallen_to_node_id),
            former_god=at(refs, row.former_god_node_id),
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def geas_views(session: AsyncSession, rows: list[GeasRow]) -> list[GeasView]:
    refs = await refs_for(session, [value for row in rows for value in (row.bearer_entity_id, row.layer_node_id)])
    return [
        GeasView(
            id=row.id,
            bearer=at(refs, row.bearer_entity_id),
            layer_node=at(refs, row.layer_node_id),
            layer=row.layer,
            mode=row.mode,
            act=row.act,
            state=row.state,
            favour=row.favour,
            laid_epoch=row.laid_epoch,
            last_kept_epoch=row.last_kept_epoch,
            broken_epoch=row.broken_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def office_views(session: AsyncSession, rows: list[CosmicOfficeRow]) -> list[CosmicOfficeView]:
    refs = await refs_for(session, [row.holder_node_id for row in rows])
    kind_ids = [row.office_kind_id for row in rows if row.office_kind_id is not None]
    office_names = {kind.id: kind.name for kind in await session.scalars(select(DivineOfficeKindRow).where(DivineOfficeKindRow.id.in_(kind_ids)))}
    return [
        CosmicOfficeView(
            office=row.office,
            holder=at(refs, row.holder_node_id),
            chosen_by=row.chosen_by,
            since_epoch=row.since_epoch,
            neglect=row.neglect,
            duty=row.duty,
            office_kind_id=row.office_kind_id,
            office_duty=(await office_duty(session, row))[0],
            office_name=office_names.get(row.office_kind_id) if row.office_kind_id is not None else None,
            locked=list(row.locked),
        )
        for row in rows
    ]


@router.get("/mythic/of/{node_id}", response_model=NodeMythicView)
async def node_mythic(services: ServicesDep, node_id: Id) -> NodeMythicView:
    async with reader(services) as session:
        node = (await node_refs(session, [node_id])).get(node_id)
        if node is None:
            raise NotFoundError("No such node.")
        quests = list(
            await session.scalars(
                select(HeroquestRow)
                .where(or_(HeroquestRow.quester_entity_id == node_id, HeroquestRow.god_node_id == node_id, HeroquestRow.legend_entity_id == node_id))
                .order_by(HeroquestRow.start_epoch.desc(), HeroquestRow.id.desc())
            )
        )
        mantling = await session.get(MantlingRow, node_id)
        walkers = list(await session.scalars(select(MantlingRow).where(MantlingRow.god_node_id == node_id).order_by(MantlingRow.progress.desc())))
        servitor = await session.get(ServitorRow, node_id)
        servitors = list(await session.scalars(select(ServitorRow).where(ServitorRow.god_node_id == node_id).order_by(ServitorRow.spirit_entity_id)))
        geasa = list(await session.scalars(select(GeasRow).where(GeasRow.bearer_entity_id == node_id).order_by(GeasRow.id)))
        laid = list(await session.scalars(select(GeasRow).where(GeasRow.layer_node_id == node_id).order_by(GeasRow.id)))
        offices = list(await session.scalars(select(CosmicOfficeRow).where(CosmicOfficeRow.holder_node_id == node_id).order_by(CosmicOfficeRow.office)))
        return NodeMythicView(
            node=node,
            heroquests=await quest_views(session, quests),
            mantling=(await mantling_views(session, [mantling]))[0] if mantling is not None else None,
            walkers=await mantling_views(session, walkers),
            servitor=(await servitor_views(session, [servitor]))[0] if servitor is not None else None,
            servitors=await servitor_views(session, servitors),
            geasa=await geas_views(session, geasa),
            laid=await geas_views(session, laid),
            offices=await office_views(session, offices),
        )


@router.get("/mythic/offices", response_model=list[CosmicOfficeView])
async def cosmic_offices(services: ServicesDep) -> list[CosmicOfficeView]:
    async with reader(services) as session:
        rows = {row.office: row for row in await session.scalars(select(CosmicOfficeRow))}
        listed = [rows.get(office) or CosmicOfficeRow(office=office, chosen_by=OfficeChoice.CREATOR, neglect=0, duty=0, locked=[]) for office in CosmicOffice]
        return await office_views(session, listed)
