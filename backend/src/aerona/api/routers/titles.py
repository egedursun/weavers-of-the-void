from collections.abc import Iterable, Mapping

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.titles import TitleClaimView, TitleDetail, TitleDriftView, TitleHolderView, TitleSummary, TitlesView
from aerona.api.views.common import node_refs
from aerona.catalog.titles import RANK_WORDS, TENURE_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.tables.titles import DeJureLinkRow, TitleHolderRow, TitleProfileRow

router = APIRouter(tags=["titles"])
NO_NODE = "Nothing lives there."
CHAIN_LIMIT = 12


def refs_of(refs: Mapping[int, NodeRef], ids: Iterable[int | None]) -> list[NodeRef]:
    return [refs[node_id] for node_id in ids if node_id is not None and node_id in refs]


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def lands_of(session: AsyncSession, title_id: int) -> list[int]:
    return list(
        await session.scalars(select(DeJureLinkRow.member_entity_id).where(DeJureLinkRow.title_entity_id == title_id).order_by(DeJureLinkRow.member_entity_id))
    )


async def summary(session: AsyncSession, row: TitleProfileRow, refs: Mapping[int, NodeRef]) -> TitleSummary | None:
    title = refs.get(row.title_entity_id)
    if title is None:
        return None
    return TitleSummary(
        title=title,
        rank=row.rank,
        rank_label=RANK_WORDS[row.rank],
        holder=ref(refs, row.holder_node_id),
        lands=len(await lands_of(session, row.title_entity_id)),
        dormant=row.holder_node_id is None,
    )


async def chain_of(session: AsyncSession, node_id: int) -> list[TitleProfileRow]:
    found: list[TitleProfileRow] = []
    link = await session.scalar(select(DeJureLinkRow).where(DeJureLinkRow.member_entity_id == node_id).limit(1))
    current = await session.get(TitleProfileRow, link.title_entity_id) if link is not None else await session.get(TitleProfileRow, node_id)
    seen: set[int] = set()
    while current is not None and current.title_entity_id not in seen and len(found) < CHAIN_LIMIT:
        seen.add(current.title_entity_id)
        found.append(current)
        current = await session.get(TitleProfileRow, current.de_jure_liege_entity_id) if current.de_jure_liege_entity_id is not None else None
    return found


@router.get("/titles/{node_id}", response_model=TitlesView)
async def titles_view(services: ServicesDep, node_id: int = Path(ge=1)) -> TitlesView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError(NO_NODE)
        profile = await session.get(TitleProfileRow, node_id)
        vassals = list(
            await session.scalars(select(TitleProfileRow).where(TitleProfileRow.de_jure_liege_entity_id == node_id).order_by(TitleProfileRow.title_entity_id))
        )
        holders = list(
            await session.scalars(
                select(TitleHolderRow).where(TitleHolderRow.title_entity_id == node_id).order_by(TitleHolderRow.since_epoch, TitleHolderRow.id)
            )
        )
        held_rows = list(
            await session.scalars(
                select(TitleProfileRow)
                .where(or_(TitleProfileRow.holder_node_id == node_id, TitleProfileRow.polity_entity_id == node_id))
                .order_by(TitleProfileRow.title_entity_id)
            )
        )
        claims = list(
            await session.scalars(select(ClaimRow).where(ClaimRow.claimant_entity_id == node_id, ClaimRow.title_entity_id.is_not(None)).order_by(ClaimRow.id))
        )
        chain = await chain_of(session, node_id) if profile is None else []
        lands = await lands_of(session, node_id) if profile is not None else []
        ids = {
            node_id,
            *lands,
            *(item for row in [*vassals, *held_rows, *chain] for item in (row.title_entity_id, row.holder_node_id)),
            *(row.holder_node_id for row in holders),
            *(row.title_entity_id for row in claims),
            *(
                (
                    profile.de_jure_liege_entity_id,
                    profile.holder_node_id,
                    profile.polity_entity_id,
                    profile.capital_entity_id,
                    profile.succession_law_entity_id,
                    *profile.regalia,
                    *(int(key) for key in profile.drift),
                )
                if profile is not None
                else ()
            ),
        }
        refs = await node_refs(session, [item for item in ids if item is not None])
        detail = None
        if profile is not None:
            detail = TitleDetail(
                rank=profile.rank,
                rank_label=RANK_WORDS[profile.rank],
                liege=ref(refs, profile.de_jure_liege_entity_id),
                holder=ref(refs, profile.holder_node_id),
                polity=ref(refs, profile.polity_entity_id),
                capital=ref(refs, profile.capital_entity_id),
                succession_law=ref(refs, profile.succession_law_entity_id),
                emblem=profile.emblem,
                prestige=profile.prestige,
                regalia=refs_of(refs, profile.regalia),
                drift=[TitleDriftView(land=ref(refs, int(key)), epochs=value) for key, value in sorted(profile.drift.items())],
                created_epoch=profile.created_epoch,
                destroyed_epoch=profile.destroyed_epoch,
                lands=refs_of(refs, lands),
                vassal_titles=[item for row in vassals if (item := await summary(session, row, refs)) is not None],
                holders=[
                    TitleHolderView(
                        holder=ref(refs, row.holder_node_id),
                        tenure=row.tenure,
                        tenure_label=TENURE_LABELS[row.tenure],
                        since_epoch=row.since_epoch,
                        until_epoch=row.until_epoch,
                    )
                    for row in holders
                ],
                held=sorted(profile.locked or []),
            )
        return TitlesView(
            node_id=node_id,
            detail=detail,
            titles_held=[item for row in held_rows if row.holder_node_id == node_id and (item := await summary(session, row, refs)) is not None],
            claims=[
                TitleClaimView(title=refs[row.title_entity_id], strength=row.strength, since_epoch=row.since_epoch)
                for row in claims
                if row.title_entity_id in refs
            ],
            realm_titles=[item for row in held_rows if row.polity_entity_id == node_id and (item := await summary(session, row, refs)) is not None],
            de_jure_chain=[item for row in chain if (item := await summary(session, row, refs)) is not None],
            ranks=[LabelView(key=rank.value, label=label) for rank, label in RANK_WORDS.items()],
        )
