from collections.abc import Mapping

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.statecraft import BackerView, CrisisView, DiplomacyView, RegardView, SphereView, StatecraftView, SubjectView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import VassalageRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.subjects import pays_tribute, sends_levies

router = APIRouter(tags=["statecraft"])
NO_NODE = "Nothing lives there."


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


@router.get("/statecraft/{node_id}", response_model=StatecraftView)
async def statecraft_view(services: ServicesDep, node_id: int = Path(ge=1)) -> StatecraftView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError(NO_NODE)
        rules = rules_from_snapshot((await CosmosRepository(session).require_cosmos()).rules_snapshot)
        book = await RealmBook.load(session)
        realm = book.realm_for(node_id)
        if realm is None:
            return StatecraftView(
                node_id=node_id,
                realm=None,
                standing=None,
                coalition_threshold=rules.diplomacy.coalition_threshold,
                liberty_revolt=rules.statecraft.liberty_revolt,
                diplomacy=None,
                felt=[],
                feared=[],
                crises=[],
                spheres=[],
                subjects=[],
            )
        realm_id = realm.entity.id
        felt = list(await session.scalars(select(PolityRegardRow).where(PolityRegardRow.holder_entity_id == realm_id).order_by(PolityRegardRow.threat.desc())))
        feared = list(
            await session.scalars(select(PolityRegardRow).where(PolityRegardRow.subject_entity_id == realm_id).order_by(PolityRegardRow.threat.desc()))
        )
        backed = select(CrisisBackerRow.crisis_id).where(CrisisBackerRow.backer_entity_id == realm_id)
        crises = list(
            await session.scalars(
                select(CrisisRow)
                .where(or_(CrisisRow.demander_entity_id == realm_id, CrisisRow.target_entity_id == realm_id, CrisisRow.id.in_(backed)))
                .order_by(CrisisRow.id.desc())
            )
        )
        backers = list(await session.scalars(select(CrisisBackerRow).where(CrisisBackerRow.crisis_id.in_([row.id for row in crises]))))
        spheres = list(
            await session.scalars(
                select(SphereRow).where(or_(SphereRow.power_entity_id == realm_id, SphereRow.client_entity_id == realm_id)).order_by(SphereRow.strength.desc())
            )
        )
        subjects = list(
            await session.scalars(
                select(VassalageRow)
                .where(or_(VassalageRow.vassal_entity_id == realm_id, VassalageRow.overlord_entity_id == realm_id))
                .order_by(VassalageRow.vassal_entity_id)
            )
        )
        diplomacy = await session.get(DiplomacyProfileRow, realm_id)
        ids: set[int] = {realm_id}
        ids.update(item for row in [*felt, *feared] for item in (row.holder_entity_id, row.subject_entity_id))
        ids.update(item for row in crises for item in (row.demander_entity_id, row.target_entity_id, row.subject_node_id) if item is not None)
        ids.update(row.backer_entity_id for row in backers)
        ids.update(item for row in spheres for item in (row.power_entity_id, row.client_entity_id))
        ids.update(item for row in subjects for item in (row.vassal_entity_id, row.overlord_entity_id))
        refs = await node_refs(session, ids)
        return StatecraftView(
            node_id=node_id,
            realm=refs.get(realm_id),
            standing=realm.profile.standing,
            coalition_threshold=rules.diplomacy.coalition_threshold,
            liberty_revolt=rules.statecraft.liberty_revolt,
            diplomacy=DiplomacyView(capacity=diplomacy.capacity, relations=diplomacy.relations, strain=diplomacy.strain, locked=list(diplomacy.locked or []))
            if diplomacy is not None
            else None,
            felt=[
                RegardView(
                    holder=refs[row.holder_entity_id], subject=refs[row.subject_entity_id], threat=row.threat, trust=row.trust, locked=list(row.locked or [])
                )
                for row in felt
                if row.holder_entity_id in refs and row.subject_entity_id in refs
            ],
            feared=[
                RegardView(
                    holder=refs[row.holder_entity_id], subject=refs[row.subject_entity_id], threat=row.threat, trust=row.trust, locked=list(row.locked or [])
                )
                for row in feared
                if row.holder_entity_id in refs and row.subject_entity_id in refs
            ],
            crises=[
                CrisisView(
                    id=row.id,
                    demander=ref(refs, row.demander_entity_id),
                    target=ref(refs, row.target_entity_id),
                    demand=row.demand,
                    subject=ref(refs, row.subject_node_id),
                    amount=row.amount,
                    escalation=row.escalation,
                    steps=rules.statecraft.crisis_steps,
                    state=row.state,
                    opened_epoch=row.opened_epoch,
                    resolved_epoch=row.resolved_epoch,
                    locked=list(row.locked or []),
                    backers=[
                        BackerView(backer=refs[backer.backer_entity_id], side=backer.side, promised=backer.promised, swing=backer.swing, locked=backer.locked)
                        for backer in backers
                        if backer.crisis_id == row.id and backer.backer_entity_id in refs
                    ],
                )
                for row in crises
            ],
            spheres=[
                SphereView(
                    power=refs[row.power_entity_id], client=refs[row.client_entity_id], strength=row.strength, since_epoch=row.since_epoch, locked=row.locked
                )
                for row in spheres
                if row.power_entity_id in refs and row.client_entity_id in refs
            ],
            subjects=[
                SubjectView(
                    vassal=refs[row.vassal_entity_id],
                    overlord=refs[row.overlord_entity_id],
                    kind=row.kind,
                    tribute_pct=row.tribute_pct,
                    levy_pct=row.levy_pct,
                    loyalty=row.loyalty,
                    liberty=row.liberty,
                    private_war=row.private_war,
                    coinage=row.coinage,
                    confirm_succession=row.confirm_succession,
                    pays_tribute=pays_tribute(row),
                    sends_levies=sends_levies(row),
                    since_epoch=row.since_epoch,
                    locked=list(row.locked or []),
                )
                for row in subjects
                if row.vassal_entity_id in refs and row.overlord_entity_id in refs
            ],
        )
