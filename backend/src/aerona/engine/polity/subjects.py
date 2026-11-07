from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.polity import VassalageRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.statecraft import SubjectKind
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.crises import power_of
from aerona.engine.polity.regard import borders, core_values, value_distance
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.strength import MilitaryStrength

TRIBUTE_KINDS = frozenset({SubjectKind.VASSAL, SubjectKind.TRIBUTARY, SubjectKind.COLONY})
LEVY_KINDS = frozenset({SubjectKind.VASSAL, SubjectKind.MARCH, SubjectKind.COLONY})
FREE_CAUSES = frozenset({WarCause.INDEPENDENCE, WarCause.TRIBUTE_REVOLT, WarCause.UPRISING, WarCause.LIBERATION})
LIBERTY = "liberty"
LOYALTY = "loyalty"
TRIBUTE = "tribute_pct"
RULER = "confirmed_ruler_entity_id"


@dataclass
class SubjectTally:
    renegotiated: int = 0
    refused: int = 0
    confirmed: int = 0
    dissolved: int = 0


def pays_tribute(row: VassalageRow) -> bool:
    return row.kind in TRIBUTE_KINDS


def sends_levies(row: VassalageRow) -> bool:
    return row.kind in LEVY_KINDS


def kind_for(book: RealmBook, vassal: Realm, overlord: Realm) -> SubjectKind:
    if vassal.entity.world_id != overlord.entity.world_id:
        return SubjectKind.COLONY
    others = [realm for realm in book.realms.values() if realm.entity.id not in (vassal.entity.id, overlord.entity.id)]
    if any(borders(book, vassal, realm) and not borders(book, overlord, realm) for realm in others):
        return SubjectKind.MARCH
    return SubjectKind.VASSAL


async def forbidden_war(ctx: TickContext, first_id: int, second_id: int, cause: WarCause) -> bool:
    if cause in FREE_CAUSES:
        return False
    book = await RealmBook.load(ctx.session)
    realm, foe = book.realm_for(first_id), book.realm_for(second_id)
    if realm is None:
        return False
    row = book.vassals.get(realm.entity.id)
    return row is not None and not row.private_war and (foe is None or foe.entity.id != row.overlord_entity_id)


async def yearn(ctx: TickContext, book: RealmBook, strength: MilitaryStrength, row: VassalageRow) -> None:
    table = ctx.rules.statecraft
    vassal, overlord = book.realms.get(row.vassal_entity_id), book.realms.get(row.overlord_entity_id)
    if vassal is None or overlord is None or LIBERTY in row.locked:
        return
    mine, theirs = await power_of(ctx, strength, vassal), await power_of(ctx, strength, overlord)
    ratio = min(1.0, mine / theirs) if theirs > 0 else 1.0
    distance = value_distance(await core_values(ctx, vassal), await core_values(ctx, overlord))
    aim = (PERCENT - row.loyalty) / 2 + ratio * PERCENT * table.liberty_strength_pct / PERCENT / 2 + distance * table.liberty_distance_pct / PERCENT
    row.liberty = clamp_int(row.liberty + round_half_up((aim - row.liberty) * table.liberty_drift_pct / PERCENT), 0, PERCENT)


async def bargain(ctx: TickContext, book: RealmBook, strength: MilitaryStrength, row: VassalageRow, tally: SubjectTally) -> None:
    table = ctx.rules.statecraft
    vassal, overlord = book.realms.get(row.vassal_entity_id), book.realms.get(row.overlord_entity_id)
    if vassal is None or overlord is None or row.liberty < table.renegotiate_at or row.tribute_pct <= 0 or TRIBUTE in row.locked:
        return
    mine, theirs = await power_of(ctx, strength, vassal), await power_of(ctx, strength, overlord)
    if mine * PERCENT >= theirs * table.back_down_ratio_pct:
        row.tribute_pct = row.tribute_pct // 2
        row.liberty = clamp_int(row.liberty - table.renegotiate_loyalty, 0, PERCENT)
        tally.renegotiated += 1
        text = f"{overlord.entity.name} eased the terms of {vassal.entity.name}, halving what it owes."
    else:
        if LOYALTY not in row.locked:
            row.loyalty = clamp_int(row.loyalty - table.renegotiate_loyalty, 0, PERCENT)
        tally.refused += 1
        text = f"{overlord.entity.name} refused {vassal.entity.name}'s plea for better terms."
    await note(ctx, text, key="statecraft.terms", ids=[overlord.entity.id, vassal.entity.id], kind=ChronicleKind.CIVILIZATION)


async def confirm(ctx: TickContext, book: RealmBook, row: VassalageRow, tally: SubjectTally) -> None:
    vassal = book.realms.get(row.vassal_entity_id)
    if vassal is None or vassal.ruler_id is None or row.confirmed_ruler_entity_id == vassal.ruler_id or RULER in row.locked:
        return
    first = row.confirmed_ruler_entity_id is None
    row.confirmed_ruler_entity_id = vassal.ruler_id
    if first or not row.confirm_succession:
        return
    table = ctx.rules.statecraft
    if row.loyalty >= PERCENT // 2:
        if LOYALTY not in row.locked:
            row.loyalty = clamp_int(row.loyalty + table.renegotiate_loyalty, 0, PERCENT)
    elif LIBERTY not in row.locked:
        row.liberty = clamp_int(row.liberty + table.renegotiate_loyalty, 0, PERCENT)
    tally.confirmed += 1


async def dissolved(ctx: TickContext, book: RealmBook, row: VassalageRow, tally: SubjectTally) -> bool:
    if row.kind is not SubjectKind.PERSONAL_UNION or "kind" in row.locked:
        return False
    vassal, overlord = book.realms.get(row.vassal_entity_id), book.realms.get(row.overlord_entity_id)
    if vassal is not None and overlord is not None and vassal.ruler_id is not None and vassal.ruler_id == overlord.ruler_id:
        return False
    await ctx.session.delete(row)
    book.vassals.pop(row.vassal_entity_id, None)
    tally.dissolved += 1
    return True


async def tend_subjects(ctx: TickContext, tally: SubjectTally) -> None:
    book = await RealmBook.load(ctx.session)
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    for vassal_id, row in sorted(book.vassals.items()):
        if held(vassal_id) or held(row.overlord_entity_id):
            continue
        if await dissolved(ctx, book, row, tally):
            continue
        await yearn(ctx, book, strength, row)
        await bargain(ctx, book, strength, row, tally)
        await confirm(ctx, book, row, tally)
