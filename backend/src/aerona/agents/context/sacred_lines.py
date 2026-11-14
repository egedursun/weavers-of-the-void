from sqlalchemy import func, select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.core.grammar import several
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import (
    DivinationRow,
    DivinationSystemRow,
    DoctrineAfterlifeRow,
    FaithClimateRow,
    ForesightRow,
    GeniusLocusRow,
    GodFeedingRow,
    MillenarianRow,
    MysticRow,
    PetitionRow,
    SacramentRow,
    SpiritOfficeRow,
    TheodicyCrisisRow,
)
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.sacred import ForesightStatus, MillenarianStage, PetitionStatus, TheodicyResolution
from aerona.engine.sacred.places import realm_ruled_by, town_of

LIST_LINES = 3
OPEN = (PetitionStatus.FILED, PetitionStatus.DELAYED, PetitionStatus.APPEALED)
LIVING = (MillenarianStage.STIRRING, MillenarianStage.GATHERING, MillenarianStage.VIGIL, MillenarianStage.MARCHING, MillenarianStage.REDATED)


async def mystic_lines(scope: Scope, me: EntityRow) -> list[str]:
    row = await scope.session.get(MysticRow, me.id)
    if row is None:
        return []
    return [
        f"visions seize you ({words(row.state.value)} mystic): {several(row.visions, 'vision', 'visions')}, {several(row.followers, 'follower', 'followers')}; "
        f"reverence {row.reverence}, persecution {row.persecution}"
    ]


async def sacrament_lines(scope: Scope, me: EntityRow) -> list[str]:
    rows = list(await scope.session.scalars(select(SacramentRow).where(SacramentRow.mortal_entity_id == me.id).order_by(SacramentRow.id)))
    if not rows:
        return []
    return ["your sacraments: " + "; ".join(f"{words(row.kind.value)} {'missed' if row.missed else 'received'}" for row in rows)]


async def town_lines(scope: Scope, town: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for row in await session.scalars(
        select(GeniusLocusRow).where(GeniusLocusRow.community_entity_id == town.id).order_by(GeniusLocusRow.spirit_entity_id).limit(LIST_LINES)
    ):
        office = await session.get(SpiritOfficeRow, row.spirit_entity_id)
        rank = f", an office of {office.rank.value} rank" if office is not None and not office.dismissed else ""
        grievance = f", offended by {words(row.offended.value)}" if row.offended is not None else ""
        found.append(
            f"{await named(scope, row.spirit_entity_id)} (spirit {row.spirit_entity_id}) keeps your town{rank}: "
            f"contentment {row.contentment}, favour {row.favour}{grievance}"
        )
    movement = await session.scalar(select(MillenarianRow).where(MillenarianRow.settlement_entity_id == town.id, MillenarianRow.stage.in_(LIVING)).limit(1))
    if movement is not None:
        found.append(
            f"{movement.members} of your town await the end set for epoch {movement.end_epoch} "
            f"({words(movement.stage.value)}, conviction {movement.conviction})"
        )
    crisis = await session.scalar(
        select(TheodicyCrisisRow).where(TheodicyCrisisRow.community_entity_id == town.id, TheodicyCrisisRow.resolution == TheodicyResolution.PENDING).limit(1)
    )
    if crisis is not None:
        found.append(f"suffering from {words(crisis.cause.value)} tests the faith of your town (suffering {crisis.suffering})")
    climate = await session.get(FaithClimateRow, town.id)
    if climate is not None and climate.piety_drift:
        found.append(f"the piety of your town drifts by {climate.piety_drift} each epoch")
    return found


async def petition_lines(scope: Scope, me: EntityRow) -> list[str]:
    rows = await scope.session.scalars(
        select(PetitionRow).where(PetitionRow.petitioner_node_id == me.id, PetitionRow.status.in_(OPEN)).order_by(PetitionRow.id).limit(LIST_LINES)
    )
    return [f"your petition to {await named(scope, row.office_spirit_id)} for {words(row.kind.value)} waits until epoch {row.due_epoch}" for row in rows]


async def court_lines(scope: Scope, me: EntityRow) -> list[str]:
    if await realm_ruled_by(scope.session, me.id) is None:
        return []
    found: list[str] = []
    reading = await scope.session.scalar(select(DivinationRow).where(DivinationRow.client_entity_id == me.id).order_by(DivinationRow.id.desc()).limit(1))
    if reading is not None:
        system = await scope.session.get(DivinationSystemRow, reading.system_id)
        way = f" by {words(system.kind.value)}, trusted {system.trust}" if system is not None else ""
        heeded = "you heeded it" if reading.heeded else "you paid it little mind"
        found.append(f"your diviners last read an {reading.verdict.value} omen on the {reading.question.value}{way}; {heeded}")
    return found


async def foresight_lines(scope: Scope, me: EntityRow) -> list[str]:
    rows = await scope.session.scalars(
        select(ForesightRow)
        .where(ForesightRow.seer_node_id == me.id, ForesightRow.status == ForesightStatus.PENDING)
        .order_by(ForesightRow.id)
        .limit(LIST_LINES)
    )
    return [
        f"you foresee that {await named(scope, row.subject_node_id)} {row.predicate.value} by epoch {row.due_epoch} (certainty {row.certainty})" for row in rows
    ]


async def mortal_sacred_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await town_of(scope.session, me)
    return [
        *await mystic_lines(scope, me),
        *await sacrament_lines(scope, me),
        *(await town_lines(scope, town) if town is not None else []),
        *await petition_lines(scope, me),
        *await court_lines(scope, me),
        *await foresight_lines(scope, me),
    ]


async def son_sacred_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    feedings = list(await session.scalars(select(GodFeedingRow).where(GodFeedingRow.god_node_id == son.id).order_by(GodFeedingRow.emotion)))
    if feedings:
        drawn = sum(row.harvested for row in feedings)
        found.append(
            "you feed on: " + ", ".join(f"{row.emotion.value} {row.weight}" for row in feedings) + f"; your faithful's feelings last gave you {drawn} essence"
        )
    offices = list(await session.scalars(select(SpiritOfficeRow).where(SpiritOfficeRow.overseer_node_id == son.id, SpiritOfficeRow.dismissed.is_(False))))
    if offices:
        corrupt = [row for row in offices if row.corruption >= scope.rules.celestial_bureaucracy.rogue_at]
        found.append(f"spirit offices under your oversight: {len(offices)}, {len(corrupt)} gone rogue")
        for office in sorted(offices, key=lambda row: (-row.corruption, row.spirit_entity_id))[:LIST_LINES]:
            found.append(
                f"{await named(scope, office.spirit_entity_id)} (spirit {office.spirit_entity_id}) holds an office of {office.rank.value} rank: "
                f"merit {office.merit}, corruption {office.corruption}"
            )
        waiting = await session.scalars(
            select(PetitionRow)
            .where(PetitionRow.office_spirit_id.in_([row.spirit_entity_id for row in offices]), PetitionRow.status.in_(OPEN))
            .order_by(PetitionRow.id)
            .limit(LIST_LINES)
        )
        for petition in waiting:
            found.append(f"petition {petition.id} to {await named(scope, petition.office_spirit_id)} asks for {words(petition.kind.value)}")
    if son.current_world_id is not None:
        world = son.current_world_id
        for mystic, mortal in await session.execute(
            select(MysticRow, EntityRow)
            .join(EntityRow, EntityRow.id == MysticRow.mortal_entity_id)
            .where(EntityRow.world_id == world)
            .order_by(MysticRow.followers.desc())
            .limit(LIST_LINES)
        ):
            visions_counted = several(mystic.visions, "vision", "visions")
            followers_counted = several(mystic.followers, "follower", "followers")
            found.append(f"{mortal.name} (mortal {mortal.id}) is a mystic: {visions_counted}, {followers_counted}, {words(mystic.state.value)}")
        for crisis, town in await session.execute(
            select(TheodicyCrisisRow, EntityRow)
            .join(EntityRow, EntityRow.id == TheodicyCrisisRow.community_entity_id)
            .where(EntityRow.world_id == world, TheodicyCrisisRow.resolution == TheodicyResolution.PENDING)
            .order_by(TheodicyCrisisRow.id)
            .limit(LIST_LINES)
        ):
            found.append(f"crisis of faith {crisis.id} in {town.name}: {words(crisis.cause.value)}, suffering {crisis.suffering}")
    churches = select(BondRow.source_node_id).where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    for row in await session.scalars(
        select(DoctrineAfterlifeRow).where(DoctrineAfterlifeRow.cult_entity_id.in_(churches)).order_by(DoctrineAfterlifeRow.cult_entity_id).limit(LIST_LINES)
    ):
        aligned = "you made it so" if row.aligned else f"{several(row.shocks, 'soul', 'souls')} found otherwise, doubt {row.doubt}"
        found.append(f"{await named(scope, row.cult_entity_id)} teaches the {words(row.model.value)}; {aligned}")
    seen = await session.scalar(
        select(func.count()).select_from(ForesightRow).where(ForesightRow.seer_node_id == son.id, ForesightRow.status == ForesightStatus.PENDING)
    )
    if seen:
        found.append(f"you hold {several(seen, 'foresight', 'foresights')} yet to come true or fail")
    return found
