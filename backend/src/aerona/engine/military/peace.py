from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow, PeaceTermRow, WarAimRow
from aerona.db.tables.polity import HouseProfileRow, PolityMemberRow
from aerona.db.tables.warfare import CaptiveRow, WarRow
from aerona.domain.enums.military import CaptiveFate, PeaceTermKind, WarAimKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.war import CaptiveStatus, WarCause, WarEnding
from aerona.engine.context import TickContext
from aerona.engine.military.captivity import settle_into
from aerona.engine.mind.book import values_for
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.primitives.queries import living_entity
from aerona.engine.services.war import release_captive

A = WarAimKind
K = PeaceTermKind
AIM_TERMS: dict[WarAimKind, PeaceTermKind] = {
    A.CONQUER_REGION: K.CESSION,
    A.SEIZE_RESOURCE: K.CESSION,
    A.SEIZE_NEXUS: K.CESSION,
    A.SEIZE_SETTLEMENT: K.CESSION,
    A.VASSALISE: K.VASSALAGE,
    A.HUMILIATE: K.HOSTAGE,
    A.REVENGE: K.HOSTAGE,
    A.LOOT: K.REPARATIONS,
    A.TRIBUTE: K.TRIBUTE,
    A.LIBERATE: K.LIBERTY,
    A.PRESS_CLAIM: K.THRONE,
    A.DESTROY_CULT: K.BREAK_CULT,
    A.CONVERT: K.OPEN_TEMPLES,
    A.CHANGE_GOVERNMENT: K.GOVERNMENT,
    A.SEIZE_ROUTE: K.TRADE_CONCESSION,
}
TRADE_CAUSES = frozenset({WarCause.TRADE_ROUTE, WarCause.RESOURCE, WarCause.DEBT})
TREATY_ENDINGS = {
    WarEnding.VICTORY: TreatyKind.PEACE,
    WarEnding.CONQUEST: TreatyKind.PEACE,
    WarEnding.TRIBUTE: TreatyKind.TRIBUTE,
    WarEnding.EXHAUSTION: TreatyKind.PEACE,
    WarEnding.PEACE: TreatyKind.PEACE,
    WarEnding.WHITE_PEACE: TreatyKind.PEACE,
    WarEnding.MIRACLE: TreatyKind.PEACE,
}
NO_TREATY = {
    WarEnding.BETRAYAL: "the war ended in betrayal; no one sat down to sign",
    WarEnding.SAME_FRONT: "the war was folded into another front of the same war",
    WarEnding.NO_SIDE_LEFT: "no side was left standing to sign a peace",
}


@dataclass
class PeaceTerm:
    kind: PeaceTermKind
    params: dict[str, int | str | bool] = field(default_factory=dict)


async def release_all(ctx: TickContext, war: WarRow) -> int:
    freed = 0
    for row in list(await ctx.session.scalars(select(CaptiveCohortRow).where(CaptiveCohortRow.war_id == war.id, CaptiveCohortRow.fate == CaptiveFate.HELD))):
        home = await living_entity(ctx.session, row.origin_entity_id)
        freed += settle_into(ctx, home, row.count)
        row.fate, row.settled_epoch = CaptiveFate.RELEASED, ctx.epoch
    for captive in list(await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.war_id == war.id, CaptiveRow.status == CaptiveStatus.HELD))):
        await release_captive(ctx, captive, CaptiveStatus.RELEASED)
        freed += 1
    return freed


async def houses_of(ctx: TickContext, *entity_ids: int) -> list[HouseProfileRow]:
    realms = list(await ctx.session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(entity_ids))))
    return list(await ctx.session.scalars(select(HouseProfileRow).where(HouseProfileRow.polity_entity_id.in_(realms))))


async def extra_terms(ctx: TickContext, war: WarRow, victor: EntityRow, loser: EntityRow, *, ending: WarEnding) -> list[PeaceTerm]:
    terms: list[PeaceTerm] = []
    values = await values_for(ctx.session, victor.id)
    if ending in {WarEnding.WHITE_PEACE, WarEnding.EXHAUSTION, WarEnding.PEACE, WarEnding.MIRACLE} or values.get(ValueAxis.MERCY, 0) > 0:
        terms.append(PeaceTerm(K.CAPTIVE_RELEASE))
    if war.cause in TRADE_CAUSES:
        terms.append(PeaceTerm(K.TRADE_CONCESSION))
    houses = await houses_of(ctx, victor.id, loser.id)
    if len({house.polity_entity_id for house in houses}) >= 2 and (values.get(ValueAxis.KINSHIP, 0) > 0 or ending is WarEnding.WHITE_PEACE):
        first = next(house for house in houses)
        second = next(house for house in houses if house.polity_entity_id != first.polity_entity_id)
        terms.append(PeaceTerm(K.MARRIAGE, {"first_house": first.house_entity_id, "second_house": second.house_entity_id}))
    aims = list(await ctx.session.scalars(select(WarAimRow).where(WarAimRow.war_id == war.id, WarAimRow.side_entity_id == victor.id)))
    border = next((aim for aim in aims if aim.kind is A.CONQUER_REGION and aim.achieved < ctx.rules.peace.cession_score and aim.target_entity_id), None)
    if border is not None and border.target_entity_id is not None:
        terms.append(PeaceTerm(K.DEMILITARISED, {"region": border.target_entity_id}))
    return terms


async def clause_for(ctx: TickContext, war: WarRow, term: PeaceTerm, victor: EntityRow, loser: EntityRow) -> tuple[str, Clause | None]:
    found: tuple[str, Clause | None] = ("", None)
    match term.kind:
        case K.CAPTIVE_RELEASE:
            freed = await release_all(ctx, war)
            found = f"both sides sent home their captives ({freed})", None
        case K.TRADE_CONCESSION:
            found = f"{loser.name} opened its markets to {victor.name}", Clause(ClauseKind.TRADE_RIGHTS, loser.id, victor.id, dict(term.params))
        case K.MARRIAGE:
            found = "the two houses were joined by marriage", Clause(ClauseKind.MARRIAGE, loser.id, victor.id, dict(term.params))
        case K.DEMILITARISED:
            found = "a border land was left without soldiers", Clause(ClauseKind.DEMILITARISED, loser.id, victor.id, dict(term.params))
        case K.CHAMPION:
            found = "future quarrels will be settled by champions", Clause(ClauseKind.CHAMPION, loser.id, victor.id, dict(term.params))
        case K.WHITE_PEACE:
            found = "neither side gained anything", Clause(ClauseKind.NON_AGGRESSION, loser.id, victor.id)
    return found


def record(
    ctx: TickContext, war: WarRow, kind: PeaceTermKind, *, victor_id: int | None, loser_id: int | None, params: dict[str, int | str | bool], note: str
) -> PeaceTermRow:
    row = PeaceTermRow(
        war_id=war.id, kind=kind, beneficiary_entity_id=victor_id, obligor_entity_id=loser_id, params=dict(params), epoch=ctx.epoch, note=note[:240] or None
    )
    ctx.session.add(row)
    return row


async def conclude(
    ctx: TickContext,
    war: WarRow,
    ending: WarEnding,
    sides: tuple[EntityRow, EntityRow],
    *,
    clauses: list[Clause],
    notes: list[str],
    terms: list[PeaceTerm],
    rows: list[PeaceTermRow],
) -> EntityRow | None:
    victor, loser = sides
    for term in terms:
        text, clause = await clause_for(ctx, war, term, victor, loser)
        if clause is not None:
            clauses.append(clause)
        if text:
            notes.append(text[0].upper() + text[1:] + ".")
        rows.append(record(ctx, war, term.kind, victor_id=victor.id, loser_id=loser.id, params=term.params, note=text))
    kind = TREATY_ENDINGS.get(ending)
    if kind is None:
        rows.append(
            record(ctx, war, K.WHITE_PEACE, victor_id=None, loser_id=None, params={"ending": ending.value, "treaty": False}, note=NO_TREATY.get(ending, ""))
        )
        return None
    parties = [(victor.id, PartyRole.SIGNATORY), (loser.id, PartyRole.SIGNATORY)]
    treaty = await sign(ctx, kind, parties, clauses=clauses, until=ctx.epoch + ctx.rules.peace.treaty_epochs)
    for row in rows:
        row.treaty_entity_id = treaty.id
    return treaty
