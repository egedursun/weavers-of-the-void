from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mechanic_hints import LAW_HINTS, RESOURCE_HINTS, SUBTYPE_LEANINGS
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import NaturalLaw, ResourceMechanic
from aerona.engine.cosmos.resources import set_mechanics
from aerona.engine.gods.economy import mechanics_of
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.numbers import stable_roll
from aerona.engine.primitives.queries import active_bonds, has_flag, living_entity, living_son
from aerona.rules.registry import Rules

MECHANIC_WEIGHTS = {
    ResourceMechanic.DECAYING: "weight_decaying",
    ResourceMechanic.ADDICTIVE: "weight_addictive",
    ResourceMechanic.SENTIENT: "weight_sentient",
    ResourceMechanic.DEPLETION_PRICE: "weight_depletion_price",
    ResourceMechanic.FIXED: "weight_fixed",
    ResourceMechanic.SACRED: "weight_sacred",
}
WORKING_LAWS = tuple(law for law in NaturalLaw if law is not NaturalLaw.NONE)


def text_of(entity: EntityRow) -> str:
    return f"{entity.name} {entity.subtype or ''} {entity.description}".casefold()


async def sacred_god(session: AsyncSession, resource: EntityRow) -> int | None:
    if resource.creator_son_id is not None and await living_son(session, resource.creator_son_id) is not None:
        return resource.creator_son_id
    holders = [bond.source_node_id for bond in sorted(await active_bonds(session, [BondKind.OWNS], targets=[resource.id]), key=lambda bond: bond.id)]
    for candidate_id in [*holders[:1], resource.location_id]:
        holder = await living_entity(session, candidate_id)
        patron = await living_patron(session, holder) if holder is not None else None
        if patron is not None:
            return patron.id
    return None


def _hinted(rules: Rules, resource: EntityRow, sacred: int | None) -> list[ResourceMechanic]:
    if stable_roll(resource.id, "hint") * 100 >= rules.mechanics.hint_chance:
        return []
    text = text_of(resource)
    found = [mechanic for mechanic, pattern in RESOURCE_HINTS if pattern.search(text) and (mechanic is not ResourceMechanic.SACRED or sacred is not None)]
    return found[: rules.mechanics.resource_max]


def _rolled(rules: Rules, resource: EntityRow, sacred: int | None) -> list[ResourceMechanic]:
    table = rules.mechanics
    if stable_roll(resource.id, "die") * 100 >= table.resource_die_chance:
        return []
    subtype = (resource.subtype or "").casefold()
    leaning = next((mechanic for pattern, mechanic in SUBTYPE_LEANINGS if pattern.search(subtype)), None)
    weighted = [
        (mechanic, getattr(table, field) * (table.subtype_leaning_mult if mechanic is leaning else 1))
        for mechanic, field in MECHANIC_WEIGHTS.items()
        if mechanic is not ResourceMechanic.SACRED or sacred is not None
    ]
    weighted = [(mechanic, weight) for mechanic, weight in weighted if weight > 0]
    total = sum(weight for _, weight in weighted)
    if total <= 0:
        return []
    threshold = stable_roll(resource.id, "choice") * total
    for mechanic, weight in weighted:
        threshold -= weight
        if threshold < 0:
            return [mechanic]
    return []


async def choose_resource_mechanics(
    session: AsyncSession, rules: Rules, resource: EntityRow, chosen: Sequence[ResourceMechanic] = ()
) -> list[ResourceMechanic]:
    sacred = await sacred_god(session, resource)
    picked = [mechanic for mechanic in dict.fromkeys(chosen) if mechanic is not ResourceMechanic.SACRED or sacred is not None]
    if picked:
        return picked[: rules.mechanics.resource_max]
    return _hinted(rules, resource, sacred) or _rolled(rules, resource, sacred)


def choose_law(rules: Rules, law: EntityRow, chosen: NaturalLaw | None = None) -> NaturalLaw:
    if chosen is not None:
        return chosen
    key = law.id if law.id is not None else text_of(law)
    if stable_roll(key, "hint") * 100 < rules.mechanics.hint_chance:
        text = text_of(law)
        hinted = next((item for item, pattern in LAW_HINTS if pattern.search(text)), None)
        if hinted is not None:
            return hinted
    if stable_roll(key, "die") * 100 >= rules.mechanics.law_die_chance:
        return NaturalLaw.NONE
    return WORKING_LAWS[min(len(WORKING_LAWS) - 1, int(stable_roll(key, "choice") * len(WORKING_LAWS)))]


async def resource_weighed(session: AsyncSession, resource: EntityRow) -> bool:
    return bool(await mechanics_of(session, resource)) or await has_flag(session, resource.id, EntityFlag.MECHANICS_WEIGHED)


async def assign_mechanics(
    session: AsyncSession, rules: Rules, entity: EntityRow, *, resource_choice: Sequence[ResourceMechanic] = (), law_choice: NaturalLaw | None = None
) -> bool:
    if entity.entity_type is EntityType.RESOURCE:
        if await resource_weighed(session, entity):
            return False
        mechanics = await choose_resource_mechanics(session, rules, entity, resource_choice)
        await set_mechanics(session, entity, mechanics, await sacred_god(session, entity) if ResourceMechanic.SACRED in mechanics else None)
        return True
    if entity.entity_type is EntityType.NATURAL_LAW:
        if entity.natural_law is not None:
            return False
        entity.natural_law = choose_law(rules, entity, law_choice)
        await session.flush()
        return True
    return False
