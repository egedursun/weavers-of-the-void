from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.realms import names_of
from aerona.api.schemas.factions import FactionActionView, FactionGoalView, FactionMemberView, FactionSlice, FactionView
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionActionRow, FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.factions.balance import power_balance
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["factions"])


@router.get("/factions/{faction_id}", response_model=FactionView)
async def faction(services: ServicesDep, faction_id: int = Path(ge=1)) -> FactionView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, faction_id)
        profile = await session.get(FactionProfileRow, faction_id)
        if entity is None or entity.entity_type is not EntityType.FACTION or profile is None:
            raise NotFoundError("No such faction.")
        goals = list(await session.scalars(select(FactionGoalRow).where(FactionGoalRow.faction_entity_id == faction_id).order_by(FactionGoalRow.id)))
        members = list(await session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == faction_id)))
        actions = list(
            await session.scalars(
                select(FactionActionRow).where(FactionActionRow.faction_entity_id == faction_id).order_by(FactionActionRow.epoch, FactionActionRow.id)
            )
        )
        book = await RealmBook.load(session)
        realm = book.realm_of(profile.home_entity_id)
        cosmos = await CosmosRepository(session).require_cosmos()
        ctx = await manual_context(session, "faction_view", rules_from_snapshot(cosmos.rules_snapshot))
        shares = await power_balance(ctx, realm) if realm is not None else {}
        ids = {
            *(int(key) for key in profile.influence_over),
            *(row.mortal_entity_id for row in members),
            *(row.target_node_id for row in goals if row.target_node_id),
            *(row.target_node_id for row in actions if row.target_node_id),
            *shares,
            *(item for item in (profile.home_entity_id, profile.leader_entity_id, profile.chartered_by_entity_id, profile.employer_entity_id) if item),
        }
        names = await names_of(session, ids)
        alive = set(await session.scalars(select(EntityRow.id).where(EntityRow.id.in_(list(ids) or [-1]), EntityRow.status == EntityStatus.CANON)))
        kinds = {
            row.faction_entity_id: row.kind.value
            for row in await session.scalars(select(FactionProfileRow).where(FactionProfileRow.faction_entity_id.in_(list(shares) or [-1])))
        }
        whole = sum(shares.values()) or 1
        return FactionView(
            id=entity.id,
            name=entity.name,
            kind=profile.kind,
            scale=profile.scale,
            treasury=profile.treasury,
            cohesion=profile.cohesion,
            secrecy=profile.secrecy,
            armed=profile.armed,
            reputation=profile.reputation,
            strength=stat(entity, "strength") or 0,
            wealth=stat(entity, "wealth") or 0,
            sway=stat(entity, "sway") or 0,
            influence_over=dict(profile.influence_over),
            influence_names={key: names.get(int(key), "") for key in profile.influence_over},
            cohort_share=dict(profile.cohort_share),
            home_id=profile.home_entity_id,
            home=names.get(profile.home_entity_id) if profile.home_entity_id else None,
            leader_id=profile.leader_entity_id,
            leader=names.get(profile.leader_entity_id) if profile.leader_entity_id else None,
            outlawed=profile.outlawed,
            chartered_by_id=profile.chartered_by_entity_id,
            chartered_by=names.get(profile.chartered_by_entity_id) if profile.chartered_by_entity_id else None,
            monopoly=profile.monopoly,
            employer_id=profile.employer_entity_id,
            employer=names.get(profile.employer_entity_id) if profile.employer_entity_id else None,
            contract_id=profile.contract_entity_id,
            pay=profile.pay,
            loyalty=profile.loyalty,
            unpaid_epochs=profile.unpaid_epochs,
            locked=list(profile.locked),
            goals=[
                FactionGoalView(
                    id=row.id,
                    kind=row.kind,
                    target_id=row.target_node_id,
                    target=names.get(row.target_node_id) if row.target_node_id else None,
                    target_key=row.target_key,
                    priority=row.priority,
                    progress=row.progress,
                    since_epoch=row.since_epoch,
                    set_by_player=row.set_by_player,
                    locked=list(row.locked),
                )
                for row in goals
                if row.achieved_epoch is None
            ],
            members=[
                FactionMemberView(
                    id=row.mortal_entity_id,
                    name=names.get(row.mortal_entity_id, ""),
                    rank=row.rank,
                    joined_epoch=row.joined_epoch,
                    alive=row.mortal_entity_id in alive,
                )
                for row in members
            ],
            actions=[
                FactionActionView(
                    id=row.id,
                    epoch=row.epoch,
                    kind=row.kind,
                    target_id=row.target_node_id,
                    target=names.get(row.target_node_id) if row.target_node_id else None,
                    success=row.success,
                    amount=row.amount,
                    note=row.note,
                )
                for row in actions
            ],
            realm_id=realm.entity.id if realm is not None else None,
            balance=[
                FactionSlice(id=key, name=names.get(key, ""), kind=kinds.get(key, ""), share=round(value * 100 / whole))
                for key, value in sorted(shares.items())
            ],
        )
