from sqlalchemy import or_, select

from aerona.agents.context.scope import Scope
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import RARITY_LABELS
from aerona.catalog.stats import EXISTENCE_BAND_LABELS, existence_band, max_hp
from aerona.db.repositories.sons import ordered_pair
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.sons import SonRelationRow, SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.son import SonRelationLabel, SonStatus
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import RelationToViewer, SiblingLine, SiblingsContext
from aerona.rules.registry import Rules


def relation_label(rules: Rules, value: int) -> SonRelationLabel:
    thresholds = rules.son_relations
    if value >= thresholds.devotion:
        return SonRelationLabel.DEVOTION
    if value >= thresholds.friendship:
        return SonRelationLabel.FRIENDSHIP
    if value > -thresholds.hostility:
        return SonRelationLabel.DISTANCE
    if value > -thresholds.hatred:
        return SonRelationLabel.HOSTILITY
    return SonRelationLabel.HATRED


async def relations_of(scope: Scope, viewer_id: int) -> dict[int, int]:
    rows = await scope.session.scalars(select(SonRelationRow).where(or_(SonRelationRow.son_a_id == viewer_id, SonRelationRow.son_b_id == viewer_id)))
    return {row.son_b_id if row.son_a_id == viewer_id else row.son_a_id: row.value for row in rows}


async def covenants_of(scope: Scope, viewer_id: int, son_ids: list[int]) -> set[int]:
    statement = select(BondRow).where(
        BondRow.kind == BondKind.ALLY,
        BondRow.state == BondState.ACTIVE,
        or_(BondRow.source_node_id == viewer_id, BondRow.target_node_id == viewer_id),
    )
    return {bond.other_end(viewer_id) for bond in await scope.session.scalars(statement)} & set(son_ids)


def sibling_line(scope: Scope, son: SonRow, viewer: SonRow | None, relations: dict[int, int], covenants: set[int]) -> SiblingLine:
    rules = scope.rules
    value = relations.get(son.id) if viewer is not None else None
    if value is None and viewer is not None:
        value = 0
    return SiblingLine(
        id=son.id,
        name=son.name,
        title=son.title,
        rarity_label=RARITY_LABELS[son.rarity],
        stars=son.stars,
        existence_label=EXISTENCE_BAND_LABELS[existence_band(rules, son.existence)],
        domain_1=DOMAIN_LABELS[son.domain_primary],
        domain_2=DOMAIN_LABELS[son.domain_secondary],
        world=scope.world_name(son.current_world_id) or None if scope.multi_world else None,
        other_world=viewer is not None and son.current_world_id != viewer.current_world_id,
        level=son.level,
        hp=son.hp,
        max_hp=max_hp(rules, son.endurance),
        faith=son.faith,
        fame=son.fame,
        status_label=None if son.status is SonStatus.ACTIVE else son.status.value,
        sleep_left=son.sleep_epochs_left or None if son.status is SonStatus.ASLEEP else None,
        relation=RelationToViewer(label=relation_label(rules, value).value, value=value) if value is not None and viewer is not None else None,
        covenant=son.id in covenants,
        rebel=son.rebel,
    )


async def sibling_lines(scope: Scope, viewer: SonRow | None) -> list[SiblingLine]:
    sons = [son for son in await scope.session.scalars(select(SonRow).order_by(SonRow.id)) if viewer is None or son.id != viewer.id]
    relations = await relations_of(scope, viewer.id) if viewer is not None else {}
    covenants = await covenants_of(scope, viewer.id, [son.id for son in sons]) if viewer is not None else set()
    return [sibling_line(scope, son, viewer, relations, covenants) for son in sons]


async def siblings(scope: Scope, viewer: SonRow | None) -> str:
    return render(PromptId.SIBLINGS, SiblingsContext(siblings=await sibling_lines(scope, viewer)))


def pair_key(first: int, second: int) -> tuple[int, int]:
    return ordered_pair(first, second)
