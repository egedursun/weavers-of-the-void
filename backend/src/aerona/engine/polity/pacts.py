from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import ClauseKind, LawKind, PartyRole, TreatyKind
from aerona.engine.context import TickContext
from aerona.engine.polity.accords import Clause, sign, treaty_between
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.queries import living_entity

HELD = (BeastTemper.BOUND, BeastTemper.TAMED)


async def faith_pacts(ctx: TickContext, book: RealmBook, laws: LawBook, room: int) -> int:
    made = 0
    for realm in book.realms.values():
        core = realm.profile.core_entity_id
        if core is None or made >= room or laws.param(realm.entity.id, LawKind.RELIGIOUS_TOLERANCE, "level") != "free":
            continue
        cults = await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type == EntityType.CULT,
                EntityRow.status == EntityStatus.CANON,
                EntityRow.location_id.in_(list(realm.members) or [-1]),
                EntityRow.id != (realm.profile.state_religion_id or -1),
            )
        )
        for cult in cults:
            if made >= room or await treaty_between(ctx.session, core, cult.id, [TreatyKind.NON_AGGRESSION]) is not None:
                continue
            await sign(
                ctx,
                TreatyKind.NON_AGGRESSION,
                [(core, PartyRole.SIGNATORY), (cult.id, PartyRole.SIGNATORY)],
                clauses=[Clause(ClauseKind.RELIGIOUS_FREEDOM, core, cult.id), Clause(ClauseKind.NON_AGGRESSION, cult.id, core)],
            )
            made += 1
    return made


async def beast_pacts(ctx: TickContext, room: int) -> int:
    made = 0
    for row in await ctx.session.scalars(
        select(BeastProfileRow)
        .where(BeastProfileRow.temper.in_(list(HELD)), BeastProfileRow.bound_to_node_id.is_not(None))
        .order_by(BeastProfileRow.beast_entity_id)
    ):
        if made >= room or row.bound_to_node_id is None:
            break
        beast = await living_entity(ctx.session, row.beast_entity_id)
        ward = await living_entity(ctx.session, row.bound_to_node_id)
        if beast is None or ward is None or await treaty_between(ctx.session, beast.id, ward.id, [TreatyKind.NON_AGGRESSION]) is not None:
            continue
        await sign(
            ctx,
            TreatyKind.NON_AGGRESSION,
            [(ward.id, PartyRole.SIGNATORY), (beast.id, PartyRole.SIGNATORY)],
            clauses=[Clause(ClauseKind.NON_AGGRESSION, beast.id, ward.id)],
            witnessed=False,
        )
        made += 1
    return made


async def god_pacts(ctx: TickContext, book: RealmBook, room: int) -> int:
    made = 0
    for realm in book.realms.values():
        core = realm.profile.core_entity_id
        if core is None or made >= room:
            continue
        gods = await ctx.session.scalars(
            select(ForeignGodRow)
            .join(BondRow, BondRow.target_node_id == ForeignGodRow.id)
            .where(BondRow.source_node_id == core, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, ForeignGodRow.stance >= 0)
        )
        for god in gods:
            if made >= room or await treaty_between(ctx.session, core, god.id, [TreatyKind.NON_AGGRESSION]) is not None:
                continue
            await sign(
                ctx,
                TreatyKind.NON_AGGRESSION,
                [(core, PartyRole.SIGNATORY), (god.id, PartyRole.GUARANTOR)],
                clauses=[Clause(ClauseKind.NON_AGGRESSION, god.id, core)],
                witnessed=False,
            )
            made += 1
    return made


async def outer_pacts(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    room = ctx.rules.treaties.outer_pact_cap
    laws = await LawBook.load(ctx.session)
    faiths = await faith_pacts(ctx, book, laws, room)
    beasts = await beast_pacts(ctx, room)
    gods = await god_pacts(ctx, book, room)
    return {"faith": faiths, "beasts": beasts, "gods": gods}
