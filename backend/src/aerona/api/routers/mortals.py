from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.mortals import AbilityView, FamilyTreeView, KinLink, MarriageView, MortalProfileView, SlotView, TreePerson
from aerona.api.views.common import node_ref, node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.mortal import MarriageRow, MortalEquipmentRow, MortalProfileRow
from aerona.domain.enums.bond import KIN_BOND_KINDS, BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.mortal import Ability, EquipmentSlot, LifeStage, MortalSex
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.mortal.equipment import SLOT_COLUMNS
from aerona.engine.mortal.kinship import marriages_of
from aerona.engine.mortal.life import sex_of_stats
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["mortals"])
NO_MORTAL = "No such mortal."
TREE_DEPTH = 3
KIN_STATES = (BondState.ACTIVE, BondState.PAST)


async def mortal_row(session: AsyncSession, mortal_id: int) -> EntityRow:
    found = await session.get(EntityRow, mortal_id)
    if found is None or found.entity_type is not EntityType.MORTAL:
        raise NotFoundError(NO_MORTAL)
    return found


def sex_of(mortal: EntityRow) -> MortalSex:
    return sex_of_stats(mortal)


async def pinned(session: AsyncSession, mortal_id: int) -> set[str]:
    rows = await session.scalars(select(ModifierRow.target_key).where(ModifierRow.target_node_id == mortal_id, ModifierRow.source_kind == ModifierSource.PIN))
    return set(rows)


async def kin_links(session: AsyncSession, mortal_id: int) -> list[KinLink]:
    rows = list(
        await session.scalars(
            select(BondRow)
            .where(BondRow.kind.in_(list(KIN_BOND_KINDS)), BondRow.state.in_(list(KIN_STATES)))
            .where(or_(BondRow.source_node_id == mortal_id, BondRow.target_node_id == mortal_id))
            .order_by(BondRow.id)
        )
    )
    others = [row.target_node_id if row.source_node_id == mortal_id else row.source_node_id for row in rows]
    refs = await node_refs(session, others)
    status = {row.id: row.status for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(others)))} if others else {}
    links = []
    for row, other in zip(rows, others, strict=True):
        ref = refs.get(other)
        if ref is None:
            continue
        links.append(
            KinLink(bond_id=row.id, kind=row.kind, other=ref, outgoing=row.source_node_id == mortal_id, living=status.get(other) is EntityStatus.CANON)
        )
    return links


async def marriage_views(session: AsyncSession, mortal_id: int) -> list[MarriageView]:
    rows = await marriages_of(session, mortal_id)
    views = []
    for row in rows:
        spouse_id = row.second_id if row.first_id == mortal_id else row.first_id
        views.append(
            MarriageView(
                id=row.id,
                spouse=await node_ref(session, spouse_id),
                kind=row.kind,
                treaty=await node_ref(session, row.treaty_id),
                start_epoch=row.start_epoch,
                end_epoch=row.end_epoch,
                cause_end=row.cause_end,
                forced=row.forced,
            )
        )
    return views


async def slot_views(session: AsyncSession, mortal_id: int) -> list[SlotView]:
    row = await session.get(MortalEquipmentRow, mortal_id)
    locked = set(row.locked or []) if row is not None else set()
    views = []
    for slot in EquipmentSlot:
        column = SLOT_COLUMNS[slot]
        item_id = getattr(row, column) if row is not None else None
        views.append(SlotView(slot=slot, item=await node_ref(session, item_id), held=column in locked))
    return views


@router.get("/mortals/{mortal_id}/profile", response_model=MortalProfileView)
async def mortal_profile(services: ServicesDep, mortal_id: int = Path(ge=1)) -> MortalProfileView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        mortal = await mortal_row(session, mortal_id)
        profile = await session.get(MortalProfileRow, mortal_id) or MortalProfileRow(entity_id=mortal_id, locked=[], life_stage=LifeStage.ADULT)
        pins = await pinned(session, mortal_id)
        abilities = [AbilityView(ability=ability, value=stat(mortal, ability.value) or 0, held=ability.value in pins) for ability in Ability]
        ref = await node_ref(session, mortal_id)
        if ref is None:
            raise NotFoundError(NO_MORTAL)
        return MortalProfileView(
            mortal=ref,
            sex=sex_of(mortal),
            abilities=abilities,
            life_stage=profile.life_stage or LifeStage.ADULT,
            fertility=profile.fertility or 0,
            health=profile.health if profile.health is not None else 100,
            stress=profile.stress or 0,
            wealth=profile.wealth or 0,
            renown=profile.renown or 0,
            honour=profile.honour if profile.honour is not None else 50,
            infamy=profile.infamy or 0,
            legitimacy=profile.legitimacy,
            education=profile.education or 0,
            polity=await node_ref(session, profile.polity_id),
            loyalty_liege=profile.loyalty_liege if profile.loyalty_liege is not None else 50,
            loyalty_community=profile.loyalty_community if profile.loyalty_community is not None else 50,
            loyalty_god=profile.loyalty_god if profile.loyalty_god is not None else 50,
            career=profile.career,
            last_break=profile.last_break,
            last_break_epoch=profile.last_break_epoch,
            cause_of_death=profile.cause_of_death,
            death_place=await node_ref(session, profile.death_place_id),
            social_class=mortal.social_class.value if mortal.social_class is not None else None,
            held=sorted(set(profile.locked or [])),
            marriages=await marriage_views(session, mortal_id),
            kin=await kin_links(session, mortal_id),
            equipment=await slot_views(session, mortal_id),
            stress_threshold=rules.stress.break_threshold,
        )


async def parents_map(session: AsyncSession, ids: set[int]) -> dict[int, list[int]]:
    rows = await session.scalars(
        select(BondRow).where(
            BondRow.kind == BondKind.PARENT_OF, BondRow.state.in_(list(KIN_STATES)), or_(BondRow.target_node_id.in_(ids), BondRow.source_node_id.in_(ids))
        )
    )
    found: dict[int, list[int]] = {}
    for row in rows:
        found.setdefault(row.target_node_id, []).append(row.source_node_id)
    return found


@router.get("/mortals/{mortal_id}/family", response_model=FamilyTreeView)
async def family_tree(services: ServicesDep, mortal_id: int = Path(ge=1)) -> FamilyTreeView:
    async with reader(services) as session:
        await mortal_row(session, mortal_id)
        generations: dict[int, int] = {mortal_id: 0}
        frontier = {mortal_id}
        for _ in range(TREE_DEPTH):
            links = await parents_map(session, frontier)
            grown: set[int] = set()
            for child, parents in links.items():
                for parent in parents:
                    if child in generations and parent not in generations:
                        generations[parent] = generations[child] - 1
                        grown.add(parent)
                    if parent in generations and child not in generations:
                        generations[child] = generations[parent] + 1
                        grown.add(child)
            if not grown:
                break
            frontier = grown
        spouses: dict[int, list[int]] = {}
        unions = await session.scalars(
            select(MarriageRow).where(or_(MarriageRow.first_id.in_(list(generations)), MarriageRow.second_id.in_(list(generations))))
        )
        for union in unions:
            spouses.setdefault(union.first_id, []).append(union.second_id)
            spouses.setdefault(union.second_id, []).append(union.first_id)
            for spouse, partner in ((union.first_id, union.second_id), (union.second_id, union.first_id)):
                if spouse not in generations and partner in generations:
                    generations[spouse] = generations[partner]
        lineage = await parents_map(session, set(generations))
        people = []
        for person in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(generations))).order_by(EntityRow.id)):
            people.append(
                TreePerson(
                    id=person.id,
                    name=person.name,
                    living=person.status is EntityStatus.CANON,
                    sex=sex_of(person) if isinstance(person.stats, MortalStats) else None,
                    parents=[parent for parent in lineage.get(person.id, []) if parent in generations],
                    spouses=sorted(set(spouses.get(person.id, [])) & set(generations)),
                    generation=generations[person.id],
                )
            )
        return FamilyTreeView(root=mortal_id, people=people)
