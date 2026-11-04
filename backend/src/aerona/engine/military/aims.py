from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.military import OccupationRow, WarAimRow
from aerona.db.tables.polity import ClaimRow, PolityTerritoryRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.war import CaptiveStatus, WarCause
from aerona.engine.context import TickContext
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import set_ruler
from aerona.engine.polity.treaties import Clause, sign
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.services.war import held_captive, take_captive

A = WarAimKind
CAUSE_AIMS: dict[WarCause, tuple[WarAimKind, ...]] = {
    WarCause.HOSTILITY: (A.CONQUER_REGION, A.TRIBUTE),
    WarCause.UPRISING: (A.LIBERATE, A.REVENGE),
    WarCause.TRIBUTE_REVOLT: (A.LIBERATE, A.HUMILIATE),
    WarCause.INCITED: (A.LOOT, A.HUMILIATE),
    WarCause.DECLARED: (A.CONQUER_REGION, A.VASSALISE),
    WarCause.BETRAYAL: (A.REVENGE, A.HUMILIATE),
    WarCause.CONQUEST_JOURNEY: (A.CONQUER_REGION, A.SEIZE_SETTLEMENT),
    WarCause.FOREIGN_GOD: (A.CONVERT, A.DESTROY_CULT),
    WarCause.INDEPENDENCE: (A.LIBERATE, A.TRIBUTE),
    WarCause.VENDETTA: (A.REVENGE, A.LOOT),
    WarCause.GRUDGE: (A.HUMILIATE, A.REVENGE),
    WarCause.DIVINE_GRUDGE: (A.CONVERT, A.HUMILIATE),
    WarCause.RIVALRY: (A.HUMILIATE, A.VASSALISE),
    WarCause.DEBT: (A.TRIBUTE, A.LOOT),
    WarCause.ESPIONAGE: (A.HUMILIATE, A.TRIBUTE),
    WarCause.SABOTAGE: (A.REVENGE, A.TRIBUTE),
    WarCause.ENVY: (A.LOOT, A.SEIZE_RESOURCE),
    WarCause.SCHISM: (A.CONVERT, A.DESTROY_CULT),
    WarCause.BEAST: (A.LOOT, A.REVENGE),
    WarCause.RESOURCE: (A.SEIZE_RESOURCE, A.CONQUER_REGION),
}
DEFENDER_AIMS = (A.HUMILIATE, A.LOOT)
REGION_AIMS = frozenset({A.CONQUER_REGION, A.SEIZE_RESOURCE, A.SEIZE_NEXUS})


async def aims_of(ctx: TickContext, war_id: int, side_id: int | None = None) -> list[WarAimRow]:
    query = select(WarAimRow).where(WarAimRow.war_id == war_id)
    if side_id is not None:
        query = query.where(WarAimRow.side_entity_id == side_id)
    return list(await ctx.session.scalars(query.order_by(WarAimRow.id)))


async def wanted(ctx: TickContext, war: WarRow, attacker: EntityRow, defender: EntityRow) -> list[WarAimKind]:
    kinds: list[WarAimKind] = []
    claimed = await ctx.session.scalar(select(ClaimRow.id).where(ClaimRow.claimant_entity_id == attacker.id, ClaimRow.ended_epoch.is_(None)).limit(1))
    if claimed is not None:
        kinds.append(A.PRESS_CLAIM)
    region_id = (await RegionAtlas.load(ctx.session)).top_region(defender.id)
    places = select(PlaceEnvironmentRow.entity_id).where(PlaceEnvironmentRow.region_entity_id == region_id, PlaceEnvironmentRow.nexus.is_(True))
    nexus = await ctx.session.scalar(places.limit(1))
    if region_id is not None and nexus is not None:
        kinds.append(A.SEIZE_NEXUS)
    if defender.entity_type is EntityType.CULT:
        kinds.append(A.DESTROY_CULT)
    if defender.entity_type is EntityType.SETTLEMENT:
        kinds.append(A.SEIZE_SETTLEMENT)
    kinds.extend(CAUSE_AIMS.get(war.cause, CAUSE_AIMS[WarCause.HOSTILITY]))
    return list(dict.fromkeys(kinds))


async def set_aims(ctx: TickContext, war: WarRow, attacker: EntityRow, defender: EntityRow) -> int:
    if await aims_of(ctx, war.id):
        return 0
    count = ctx.rules.war_aims.aims_per_side
    region = (await RegionAtlas.load(ctx.session)).top_region(defender.id)
    made = 0
    for side, enemy, kinds in ((attacker, defender, await wanted(ctx, war, attacker, defender)), (defender, attacker, list(DEFENDER_AIMS))):
        for kind in kinds[:count]:
            target = region if kind in REGION_AIMS and side is attacker else enemy.id
            ctx.session.add(WarAimRow(war_id=war.id, side_entity_id=side.id, kind=kind, target_entity_id=target, params={}, achieved=0))
            made += 1
    return made


async def advance(ctx: TickContext, war_id: int, side_id: int, amount: int, *, target: int | None = None, kinds: frozenset[WarAimKind] | None = None) -> int:
    moved = 0
    for aim in await aims_of(ctx, war_id, side_id):
        if (kinds is not None and aim.kind not in kinds) or (target is not None and aim.target_entity_id != target):
            continue
        aim.achieved = clamp_int(aim.achieved + amount, 0, PERCENT)
        moved += 1
    return moved


async def cede(ctx: TickContext, book: RealmBook, victor: EntityRow, loser: EntityRow, region_id: int) -> bool:
    realm, lost = book.realm_of(victor.id), book.realm_of(loser.id)
    occupation = await ctx.session.get(OccupationRow, region_id)
    control = occupation.control if occupation is not None else PERCENT // 2
    if lost is not None:
        statement = delete(PolityTerritoryRow).where(PolityTerritoryRow.polity_entity_id == lost.entity.id, PolityTerritoryRow.region_entity_id == region_id)
        await ctx.session.execute(statement)
    if realm is not None and await ctx.session.get(PolityTerritoryRow, (realm.entity.id, region_id)) is None:
        ctx.session.add(PolityTerritoryRow(polity_entity_id=realm.entity.id, region_entity_id=region_id, control=control))
    if occupation is not None:
        await ctx.session.delete(occupation)
    return realm is not None or lost is not None


async def hostage(ctx: TickContext, war: WarRow, victor: EntityRow, loser: EntityRow, book: RealmBook) -> EntityRow | None:
    realm = book.realm_of(loser.id)
    ruler = realm.ruler_id if realm is not None else None
    heir_id = await ctx.session.scalar(select(DesignatedHeirRow.heir_entity_id).where(DesignatedHeirRow.ruler_entity_id == ruler)) if ruler else None
    heir = await living_entity(ctx.session, heir_id)
    if heir is None or await held_captive(ctx.session, heir.id) is not None:
        return None
    row = await take_captive(ctx, victor, heir, war, description="hostage of the peace", home_id=loser.id)
    row.status = CaptiveStatus.WARD
    return heir


async def liberate(ctx: TickContext, victor: EntityRow, loser: EntityRow) -> int:
    bonds = BondRepository(ctx.session)
    freed = 0
    for bond in await bonds.outgoing(victor.id, BondKind.PAYS_TRIBUTE):
        if bond.target_node_id == loser.id:
            await bonds.deactivate(bond, ctx.epoch, "freed by war")
            freed += 1
    return freed


Term = tuple[str, Clause] | None
Sides = tuple[EntityRow, EntityRow]


async def cession_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    if aim.achieved < ctx.rules.peace.cession_score or aim.target_entity_id is None or not await cede(ctx, book, victor, loser, aim.target_entity_id):
        return None
    return f"{loser.name} ceded land to {victor.name}", Clause(ClauseKind.CESSION, loser.id, victor.id, {"region": aim.target_entity_id})


async def vassal_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    if aim.achieved < ctx.rules.peace.vassal_score:
        return None
    await sign(ctx, TreatyKind.VASSALAGE, [(victor.id, PartyRole.OVERLORD), (loser.id, PartyRole.VASSAL)])
    return f"{loser.name} bent the knee to {victor.name}", Clause(ClauseKind.NON_AGGRESSION, loser.id, victor.id)


async def hostage_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    taken = await hostage(ctx, war, victor, loser, book) if aim.achieved >= ctx.rules.peace.hostage_score else None
    if taken is None:
        return None
    return f"{taken.name} went to {victor.name} as a hostage", Clause(ClauseKind.HOSTAGE, loser.id, victor.id, {"hostage": taken.id})


async def reparation_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    peace = ctx.rules.peace
    if aim.achieved < peace.tribute_score:
        return None
    shift_stat(loser, "wealth", -peace.reparations)
    shift_stat(victor, "wealth", peace.reparations)
    return f"{loser.name} paid reparations", Clause(ClauseKind.TRIBUTE, loser.id, victor.id, {"amount": peace.reparations})


async def liberty_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    if aim.achieved < ctx.rules.peace.tribute_score or not await liberate(ctx, victor, loser):
        return None
    return f"{victor.name} threw off the tribute owed to {loser.name}", Clause(ClauseKind.NON_AGGRESSION, victor.id, loser.id)


async def claim_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    return await press(ctx, *sides, book) if aim.achieved >= ctx.rules.peace.cession_score else None


async def cult_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    if aim.achieved < ctx.rules.peace.vassal_score or loser.entity_type is not EntityType.CULT or loser.status is not EntityStatus.CANON:
        return None
    await retire_in(ctx, loser, f"broken by {victor.name}", close_bonds=True)
    return f"{loser.name} was broken and scattered", Clause(ClauseKind.RELIGIOUS_FREEDOM, loser.id, victor.id)


async def faith_term(ctx: TickContext, war: WarRow, aim: WarAimRow, sides: Sides, book: RealmBook) -> Term:
    victor, loser = sides
    if aim.achieved < ctx.rules.peace.tribute_score:
        return None
    return f"{loser.name} opened its temples to the faith of {victor.name}", Clause(ClauseKind.RELIGIOUS_FREEDOM, loser.id, victor.id)


TERMS = {
    A.CONQUER_REGION: cession_term,
    A.SEIZE_RESOURCE: cession_term,
    A.SEIZE_NEXUS: cession_term,
    A.SEIZE_SETTLEMENT: cession_term,
    A.VASSALISE: vassal_term,
    A.HUMILIATE: hostage_term,
    A.REVENGE: hostage_term,
    A.LOOT: reparation_term,
    A.TRIBUTE: reparation_term,
    A.LIBERATE: liberty_term,
    A.PRESS_CLAIM: claim_term,
    A.DESTROY_CULT: cult_term,
    A.CONVERT: faith_term,
}


async def press(ctx: TickContext, victor: EntityRow, loser: EntityRow, book: RealmBook) -> tuple[str, Clause] | None:
    realm = book.realm_of(loser.id)
    if realm is None:
        return None
    claim = await ctx.session.scalar(
        select(ClaimRow).where(ClaimRow.claimant_entity_id == victor.id, ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.ended_epoch.is_(None)).limit(1)
    )
    if claim is None or not set_ruler(ctx, realm, claim.claimant_entity_id, "claim won by war"):
        return None
    claim.pressed, claim.ended_epoch = True, ctx.epoch
    return f"{victor.name} took the throne it claimed", Clause(ClauseKind.CESSION, loser.id, victor.id, {"throne": realm.entity.id})


async def peace_terms(ctx: TickContext, war: WarRow, victor: EntityRow, loser: EntityRow) -> list[str]:
    book = await RealmBook.load(ctx.session)
    notes: list[str] = []
    clauses: list[Clause] = []
    for aim in await aims_of(ctx, war.id, victor.id):
        found = await TERMS[aim.kind](ctx, war, aim, (victor, loser), book)
        if found is not None:
            notes.append(found[0] + ".")
            clauses.append(found[1])
    parties = [(victor.id, PartyRole.SIGNATORY), (loser.id, PartyRole.SIGNATORY)]
    await sign(ctx, TreatyKind.PEACE, parties, clauses=clauses, until=ctx.epoch + ctx.rules.peace.treaty_epochs)
    return notes


async def white_peace(ctx: TickContext, first: EntityRow, second: EntityRow) -> None:
    await sign(ctx, TreatyKind.PEACE, [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)], until=ctx.epoch + ctx.rules.peace.treaty_epochs)
