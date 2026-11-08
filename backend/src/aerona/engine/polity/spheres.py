from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.statecraft import SphereRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import RegionalStanding
from aerona.domain.enums.statecraft import CrisisDemand
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.crises import GREAT, open_crisis, power_of
from aerona.engine.polity.regard import borders, shift_regard
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import declare_war

STANDING = "standing"


@dataclass
class SphereTally:
    drawn: int = 0
    lost: int = 0
    protected: int = 0
    summits: int = 0
    demands: int = 0


async def spheres_over(ctx: TickContext, client_id: int) -> list[SphereRow]:
    return list(await ctx.session.scalars(select(SphereRow).where(SphereRow.client_entity_id == client_id).order_by(SphereRow.power_entity_id)))


async def demand_release(ctx: TickContext, power: Realm, lord: Realm | None, client: int, tally: SphereTally) -> None:
    if lord is None or not ctx.rng(f"statecraft.release.{power.entity.id}.{client}.{ctx.epoch}").chance(ctx.rules.statecraft.crisis_pct):
        return
    if await open_crisis(ctx, power, lord, CrisisDemand.RELEASE_VASSAL, subject_id=client) is not None:
        tally.demands += 1


async def draw(ctx: TickContext, book: RealmBook, power: Realm, strength: MilitaryStrength, tally: SphereTally) -> None:
    table = ctx.rules.statecraft
    mine = await power_of(ctx, strength, power)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        client = realm.entity.id
        if client == power.entity.id or realm.entity.world_id != power.entity.world_id or realm.profile.standing in GREAT or held(client):
            continue
        if not borders(book, power, realm) or await ctx.session.get(SphereRow, (power.entity.id, client)) is not None:
            continue
        if mine < await power_of(ctx, strength, realm) * table.sphere_ratio_pct / PERCENT:
            continue
        overlord = book.vassals.get(client)
        if overlord is not None and overlord.overlord_entity_id != power.entity.id:
            await demand_release(ctx, power, book.realms.get(overlord.overlord_entity_id), client, tally)
            continue
        ctx.session.add(SphereRow(power_entity_id=power.entity.id, client_entity_id=client, strength=PERCENT * 3 // 10, since_epoch=ctx.epoch))
        tally.drawn += 1
        await note(
            ctx,
            f"{realm.entity.name} fell into the sphere of {power.entity.name}.",
            key="statecraft.sphere",
            ids=[power.entity.id, client],
            kind=ChronicleKind.CIVILIZATION,
        )
    await ctx.session.flush()


async def contest(ctx: TickContext, client_id: int, rows: list[SphereRow], tally: SphereTally) -> None:
    table = ctx.rules.statecraft
    strongest = max(rows, key=lambda row: (row.strength, -row.power_entity_id))
    for row in rows:
        if row.locked:
            continue
        if row is strongest:
            row.strength = clamp_int(row.strength + table.sphere_growth, 0, PERCENT)
            continue
        row.strength = clamp_int(row.strength - table.sphere_contest, 0, PERCENT)
        if row.strength == 0:
            await ctx.session.delete(row)
            tally.lost += 1


async def favour(ctx: TickContext, book: RealmBook, row: SphereRow) -> None:
    power, client = book.realms.get(row.power_entity_id), book.realms.get(row.client_entity_id)
    if power is None or client is None:
        return
    gain = ctx.rules.statecraft.sphere_regard
    await shift_regard(ctx, row.client_entity_id, row.power_entity_id, trust=gain)
    await shift_regard(ctx, row.power_entity_id, row.client_entity_id, trust=gain)
    first, second = power.profile.core_entity_id, client.profile.core_entity_id
    if first is not None and second is not None and not held(second):
        await change_relation(ctx, second, first, gain, MemoryKind.TRADED_WITH, note="favoured in trade within a sphere")
    if STANDING not in client.profile.locked:
        client.profile.standing = RegionalStanding.CLIENT


async def protect(ctx: TickContext, book: RealmBook, row: SphereRow, tally: SphereTally) -> None:
    power, client = book.realms.get(row.power_entity_id), book.realms.get(row.client_entity_id)
    if power is None or client is None or power.profile.core_entity_id is None or client.profile.core_entity_id is None:
        return
    guard = power.profile.core_entity_id
    for bond in await active_bonds(ctx.session, [BondKind.ENEMY], targets=[client.profile.core_entity_id]):
        foe = bond.source_node_id
        foe_realm = book.realm_for(foe)
        if foe == guard or (foe_realm is not None and foe_realm.entity.id == power.entity.id) or held(guard):
            continue
        reason = f"{power.entity.name} stood by its client {client.entity.name}"
        if await declare_war(ctx, guard, foe, reason, cause=WarCause.DECLARED, world_cap=False, brokered=True):
            tally.protected += 1


async def summit(ctx: TickContext, book: RealmBook, tally: SphereTally) -> None:
    table = ctx.rules.statecraft
    if ctx.epoch % table.summit_epochs != 0:
        return
    by_world: dict[int, list[Realm]] = {}
    for realm in book.realms.values():
        if realm.profile.standing in GREAT and not held(realm.entity.id):
            by_world.setdefault(realm.entity.world_id or 0, []).append(realm)
    for powers in by_world.values():
        if len(powers) < 2:
            continue
        for first in powers:
            for second in powers:
                if first.entity.id != second.entity.id:
                    await shift_regard(ctx, first.entity.id, second.entity.id, trust=table.summit_trust, threat=-table.summit_trust)
        tally.summits += 1
        await note(
            ctx,
            f"The great powers {', '.join(realm.entity.name for realm in powers)} met in a summit.",
            key="statecraft.summit",
            ids=[realm.entity.id for realm in powers],
            kind=ChronicleKind.CIVILIZATION,
        )


async def tend_spheres(ctx: TickContext, tally: SphereTally) -> None:
    book = await RealmBook.load(ctx.session)
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if realm.profile.standing in GREAT and not held(realm.entity.id):
            await draw(ctx, book, realm, strength, tally)
    clients = sorted({row.client_entity_id for row in await ctx.session.scalars(select(SphereRow))})
    for client in clients:
        rows = [row for row in await spheres_over(ctx, client) if not held(row.power_entity_id) and not held(client)]
        if not rows:
            continue
        if client not in book.realms:
            for row in rows:
                await ctx.session.delete(row)
            continue
        await contest(ctx, client, rows, tally)
        for row in rows:
            if row.strength > 0:
                await favour(ctx, book, row)
                await protect(ctx, book, row, tally)
    await summit(ctx, book, tally)
