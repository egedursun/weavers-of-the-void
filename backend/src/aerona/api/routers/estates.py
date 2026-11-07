from collections.abc import Mapping

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.estates import (
    CompanyView,
    EstatesView,
    EstateView,
    GuildMemberView,
    GuildView,
    HolyOrderView,
    PoliticalMovementView,
    PoliticalSupportView,
    ShareView,
)
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.estates import CAUSE_LABELS, ESTATE_NAMES, PRIVILEGE_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import (
    CompanyProfileRow,
    CompanyShareRow,
    EstatePrivilegeRow,
    EstateProfileRow,
    GuildSecretRow,
    HolyOrderProfileRow,
    MovementProfileRow,
    MovementSupportRow,
)
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind, FactionRank

router = APIRouter(tags=["estates"])
NO_NODE = "Nothing lives there."
GUILD_RANKS = {FactionRank.NOVICE: "Apprentice", FactionRank.MEMBER: "Journeyman", FactionRank.OFFICER: "Master", FactionRank.LEADER: "Grandmaster"}
GUILDS = (FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD)
REASON = (
    "Estates and movements belong to realms and their communities; companies, holy orders and guilds are factions. This kind holds none, but may hold shares."
)


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


@router.get("/estates/{node_id}", response_model=EstatesView)
async def estates_view(services: ServicesDep, node_id: int = Path(ge=1)) -> EstatesView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError(NO_NODE)
        entity = await session.get(EntityRow, node_id)
        estates = list(
            await session.scalars(
                select(EstateProfileRow)
                .where(or_(EstateProfileRow.polity_entity_id == node_id, EstateProfileRow.faction_entity_id == node_id))
                .order_by(EstateProfileRow.faction_entity_id)
            )
        )
        supported = select(MovementSupportRow.movement_entity_id).where(MovementSupportRow.community_entity_id == node_id)
        movements = list(
            await session.scalars(
                select(MovementProfileRow)
                .where(
                    or_(
                        MovementProfileRow.polity_entity_id == node_id,
                        MovementProfileRow.faction_entity_id == node_id,
                        MovementProfileRow.faction_entity_id.in_(supported),
                    )
                )
                .order_by(MovementProfileRow.faction_entity_id)
            )
        )
        companies = list(
            await session.scalars(
                select(CompanyProfileRow)
                .where(or_(CompanyProfileRow.polity_entity_id == node_id, CompanyProfileRow.faction_entity_id == node_id))
                .order_by(CompanyProfileRow.faction_entity_id)
            )
        )
        orders = list(
            await session.scalars(
                select(HolyOrderProfileRow).where(
                    or_(
                        HolyOrderProfileRow.cult_entity_id == node_id,
                        HolyOrderProfileRow.faction_entity_id == node_id,
                        HolyOrderProfileRow.fortress_entity_id == node_id,
                    )
                )
            )
        )
        guild_profiles = list(
            await session.scalars(
                select(FactionProfileRow).where(
                    FactionProfileRow.kind.in_(list(GUILDS)), or_(FactionProfileRow.faction_entity_id == node_id, FactionProfileRow.home_entity_id == node_id)
                )
            )
        )
        holdings = list(await session.scalars(select(CompanyShareRow).where(CompanyShareRow.holder_node_id == node_id)))
        membership = await session.scalar(
            select(FactionMembershipRow)
            .join(FactionProfileRow, FactionProfileRow.faction_entity_id == FactionMembershipRow.faction_entity_id)
            .where(FactionMembershipRow.mortal_entity_id == node_id, FactionProfileRow.kind.in_(list(GUILDS)))
            .limit(1)
        )
        supports = {
            row.faction_entity_id: list(
                await session.scalars(
                    select(MovementSupportRow).where(MovementSupportRow.movement_entity_id == row.faction_entity_id).order_by(MovementSupportRow.share.desc())
                )
            )
            for row in movements
        }
        shares = {
            row.faction_entity_id: list(
                await session.scalars(
                    select(CompanyShareRow).where(CompanyShareRow.company_entity_id == row.faction_entity_id).order_by(CompanyShareRow.share.desc())
                )
            )
            for row in companies
        }
        members = {
            row.faction_entity_id: list(
                await session.scalars(
                    select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == row.faction_entity_id).order_by(FactionMembershipRow.rank)
                )
            )
            for row in guild_profiles
        }
        secrets = {
            row.faction_entity_id: list(await session.scalars(select(GuildSecretRow.technique).where(GuildSecretRow.guild_entity_id == row.faction_entity_id)))
            for row in guild_profiles
        }
        known = {
            row.faction_entity_id: list(
                await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == row.home_entity_id))
            )
            if row.home_entity_id is not None
            else []
            for row in guild_profiles
        }
        privileges = {
            row.faction_entity_id: list(
                await session.scalars(select(EstatePrivilegeRow.privilege).where(EstatePrivilegeRow.estate_entity_id == row.faction_entity_id))
            )
            for row in estates
        }
        ids = {
            node_id,
            *(item for row in estates for item in (row.faction_entity_id, row.polity_entity_id)),
            *(item for row in movements for item in (row.faction_entity_id, row.polity_entity_id)),
            *(item.community_entity_id for rows in supports.values() for item in rows),
            *(item for row in companies for item in (row.faction_entity_id, row.polity_entity_id, row.route_entity_id, row.region_entity_id)),
            *(item.holder_node_id for rows in shares.values() for item in rows),
            *(item for row in orders for item in (row.faction_entity_id, row.cult_entity_id, row.fortress_entity_id)),
            *(row.faction_entity_id for row in guild_profiles),
            *(item.mortal_entity_id for rows in members.values() for item in rows),
            *(row.company_entity_id for row in holdings),
        }
        refs = await node_refs(session, [item for item in ids if item is not None])
        can_found = entity is not None and entity.entity_type in {EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION}
        return EstatesView(
            node_id=node_id,
            estates=[
                EstateView(
                    estate=refs[row.faction_entity_id],
                    realm=ref(refs, row.polity_entity_id),
                    social_class=row.social_class,
                    class_label=ESTATE_NAMES.get(row.social_class, row.social_class.value),
                    loyalty=row.loyalty,
                    influence=row.influence,
                    privileges=privileges[row.faction_entity_id],
                    held=sorted(row.locked or []),
                )
                for row in estates
                if row.faction_entity_id in refs
            ],
            movements=[
                PoliticalMovementView(
                    movement=refs[row.faction_entity_id],
                    realm=ref(refs, row.polity_entity_id),
                    cause=row.cause,
                    cause_label=CAUSE_LABELS[row.cause],
                    support=row.support,
                    is_party=row.is_party,
                    founded_epoch=row.founded_epoch,
                    communities=[
                        PoliticalSupportView(community=refs[item.community_entity_id], share=item.share, held=item.locked)
                        for item in supports[row.faction_entity_id]
                        if item.community_entity_id in refs
                    ],
                    held=sorted(row.locked or []),
                )
                for row in movements
                if row.faction_entity_id in refs
            ],
            companies=[
                CompanyView(
                    company=refs[row.faction_entity_id],
                    realm=ref(refs, row.polity_entity_id),
                    route=ref(refs, row.route_entity_id),
                    region=ref(refs, row.region_entity_id),
                    commodity=row.commodity,
                    dividend_pct=row.dividend_pct,
                    value=row.value,
                    chartered_epoch=row.chartered_epoch,
                    shares=[
                        ShareView(holder=refs[item.holder_node_id], share=item.share, held=item.locked)
                        for item in shares[row.faction_entity_id]
                        if item.holder_node_id in refs
                    ],
                    held=sorted(row.locked or []),
                )
                for row in companies
                if row.faction_entity_id in refs
            ],
            orders=[
                HolyOrderView(
                    order=refs[row.faction_entity_id],
                    cult=ref(refs, row.cult_entity_id),
                    fortress=ref(refs, row.fortress_entity_id),
                    tithe_share=row.tithe_share,
                    held=sorted(row.locked or []),
                )
                for row in orders
                if row.faction_entity_id in refs
            ],
            guilds=[
                GuildView(
                    guild=refs[row.faction_entity_id],
                    members=[
                        GuildMemberView(member=refs[item.mortal_entity_id], rank=item.rank, rank_label=GUILD_RANKS[item.rank])
                        for item in members[row.faction_entity_id]
                        if item.mortal_entity_id in refs
                    ],
                    secrets=secrets[row.faction_entity_id],
                    known=known[row.faction_entity_id],
                )
                for row in guild_profiles
                if row.faction_entity_id in refs
            ],
            holdings=[ShareView(holder=refs[row.company_entity_id], share=row.share, held=row.locked) for row in holdings if row.company_entity_id in refs],
            guild_rank=GUILD_RANKS[membership.rank] if membership is not None else None,
            classes=[LabelView(key=key.value, label=label) for key, label in ESTATE_NAMES.items()],
            privileges=[LabelView(key=key.value, label=label) for key, label in PRIVILEGE_LABELS.items()],
            causes=[LabelView(key=key.value, label=label) for key, label in CAUSE_LABELS.items()],
            can_found=can_found,
            reason=None if can_found else REASON,
        )
