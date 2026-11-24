from sqlalchemy import select

from aerona.catalog.pacts import NEIGHBOUR_ACCORDS
from aerona.db.tables.polity import TreatyPartyRow, TreatyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import PartyRole, TreatyKind, TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.polity.accords import sign, treaty_between
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import move_stat, stat_or
from aerona.engine.services.community_relations import change_relation, relation


def cores(book: RealmBook) -> list[Realm]:
    return [
        realm
        for realm in sorted(book.realms.values(), key=lambda item: item.entity.id)
        if realm.profile.core_entity_id is not None and not held(realm.entity.id)
    ]


async def seek_accords(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    table = ctx.rules.treaties
    made = {"accords": 0, "aid_pacts": 0}
    realms = cores(book)
    for index, first in enumerate(realms):
        for second in realms[index + 1 :]:
            if first.entity.world_id != second.entity.world_id:
                continue
            one, two = first.profile.core_entity_id or 0, second.profile.core_entity_id or 0
            regard = await relation(ctx.session, ctx.rules, one, two)
            rng = ctx.rng(f"accord.{one}.{two}.{ctx.epoch}")
            for kind, wanted, key in ((TreatyKind.BORDER_ACCORD, table.accord_relation, "accords"), (TreatyKind.MUTUAL_AID, table.aid_relation, "aid_pacts")):
                if regard >= wanted and await treaty_between(ctx.session, one, two, [kind]) is None and rng.chance(table.accord_pct):
                    await sign(ctx, kind, [(one, PartyRole.SIGNATORY), (two, PartyRole.SIGNATORY)], until=ctx.epoch + table.alliance_epochs)
                    made[key] += 1
    return made


async def parties(ctx: TickContext, treaty_id: int) -> list[int]:
    return list(
        await ctx.session.scalars(
            select(TreatyPartyRow.party_node_id)
            .where(TreatyPartyRow.treaty_entity_id == treaty_id, TreatyPartyRow.role == PartyRole.SIGNATORY)
            .order_by(TreatyPartyRow.party_node_id)
        )
    )


async def keep_accords(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.treaties
    kept = {"aid_sent": 0, "borders_kept": 0}
    rows = await ctx.session.scalars(
        select(TreatyProfileRow)
        .where(TreatyProfileRow.status == TreatyStatus.IN_FORCE, TreatyProfileRow.kind.in_(sorted(NEIGHBOUR_ACCORDS)))
        .order_by(TreatyProfileRow.treaty_entity_id)
    )
    for profile in list(rows):
        signers = await parties(ctx, profile.treaty_entity_id)
        if len(signers) < 2 or held(profile.treaty_entity_id):
            continue
        if profile.kind is TreatyKind.BORDER_ACCORD:
            await change_relation(ctx, signers[0], signers[1], table.border_accord_regard, MemoryKind.GOODWILL, note="kept the borders fixed by accord")
            kept["borders_kept"] += 1
            continue
        for needy, giver in ((signers[0], signers[1]), (signers[1], signers[0])):
            struck, helper = await living_entity(ctx.session, needy), await living_entity(ctx.session, giver)
            if struck is None or helper is None or held(struck.id) or held(helper.id):
                continue
            if stat_or(struck, "prosperity", 0) < table.aid_struck_prosperity <= stat_or(helper, "prosperity", 0):
                move_stat(helper, struck, "prosperity", table.aid_prosperity)
                kept["aid_sent"] += 1
    return kept
