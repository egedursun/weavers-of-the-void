from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, LivingLineTraitRow, LivingProfileRow, SymbiontRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.polity import LawKind
from aerona.engine.polity.laws import law_param

LIST_LINES = 4
LAWS = (
    (LawKind.LIVING_CRAFT_LAW, "level", "living craft is"),
    (LawKind.CLONE_LAW, "level", "making clones is"),
    (LawKind.GERMLINE_LAW, "level", "changing what passes to descendants is"),
)


async def trait_words(scope: Scope, line_id: int) -> str:
    rows = await scope.session.execute(select(LivingLineTraitRow.trait, LivingLineTraitRow.strength).where(LivingLineTraitRow.line_id == line_id))
    shown = [f"{words(trait.value)} {strength:+d}" for trait, strength in rows.all()]
    return ", ".join(shown) if shown else "no designed traits"


async def line_words(scope: Scope, line: LivingLineRow) -> str:
    loose = ", loose in the wild" if line.escaped else ""
    return (
        f"the line {line.name} (line {line.id}), made by {words(line.method.value)}: stability {line.stability}, "
        f"generation {line.generation}, drift {line.drift_pct}, {words(line.fertility.value)}{loose}; {await trait_words(scope, line.id)}"
    )


async def mortal_living_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    profile = await session.get(LivingProfileRow, me.id)
    if profile is not None:
        handler = await named(scope, profile.bonded_to_node_id) if profile.bonded_to_node_id else "no one"
        found.append(
            f"your own living body: {words(profile.growth_stage.value)}, health {profile.health}, size {profile.size_pct}, "
            f"eats by {words(profile.metabolism.value)}, bond {profile.bond} with {handler}"
        )
    mine = select(LivingLineRow).where(or_(LivingLineRow.owner_node_id == me.id, LivingLineRow.maker_node_id == me.id)).order_by(LivingLineRow.id)
    for line in await session.scalars(mine.limit(LIST_LINES)):
        found.append(f"you hold {await line_words(scope, line)}")
    for row in await session.scalars(select(SymbiontRow).where(SymbiontRow.host_node_id == me.id).order_by(SymbiontRow.id).limit(LIST_LINES)):
        found.append(
            f"something lives within you (symbiont {row.id}) in the {words(row.placement.value)}, {words(row.relation.value)}, strength {row.strength}"
        )
    banks = select(GeneBankRow).where(or_(GeneBankRow.holder_node_id == me.id, GeneBankRow.holder_node_id == me.location_id))
    for bank in await session.scalars(banks.order_by(GeneBankRow.structure_entity_id).limit(LIST_LINES)):
        samples = list(await session.scalars(select(GeneBankSampleRow).where(GeneBankSampleRow.bank_entity_id == bank.structure_entity_id).limit(LIST_LINES)))
        kept = ", ".join([f"sample {row.id} of {await named(scope, row.organism_node_id)}" for row in samples]) or "nothing yet"
        found.append(f"the bank of life in {await named(scope, bank.structure_entity_id)} (bank {bank.structure_entity_id}) keeps {kept}")
    if me.location_id is not None:
        for law, key, said in LAWS:
            level = await law_param(session, me.location_id, law, key)
            if level is not None:
                found.append(f"here {said} {words(str(level))}")
    return found


async def son_living_lines(scope: Scope, son: SonRow) -> list[str]:
    world = son.current_world_id
    if world is None:
        return []
    in_world = select(EntityRow.id).where(EntityRow.world_id == world, EntityRow.status == EntityStatus.CANON)
    lines = (
        select(LivingLineRow).where(or_(LivingLineRow.species_entity_id.in_(in_world), LivingLineRow.owner_node_id.in_(in_world))).order_by(LivingLineRow.id)
    )
    return [f"in your world lives {await line_words(scope, line)}" for line in await scope.session.scalars(lines.limit(LIST_LINES))]
