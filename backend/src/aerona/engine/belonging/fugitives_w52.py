from sqlalchemy import select

from aerona.catalog.fugitives import FUGITIVES
from aerona.db.tables.belonging import FugitiveRow, SanctuaryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import RegistryRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind, SanctuaryState
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.belonging.refuge import refuge_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.faith.book import patron_node
from aerona.engine.law.prisons import imprison
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.services.war import held_captive, ongoing_war_count


async def open_fugitives(ctx: TickContext) -> list[FugitiveRow]:
    return list(
        await ctx.session.scalars(select(FugitiveRow).where(FugitiveRow.caught_epoch.is_(None), FugitiveRow.freed_epoch.is_(None)).order_by(FugitiveRow.id))
    )


async def flee(ctx: TickContext, mortal: EntityRow, kind: FugitiveKind, pursuer: int | None) -> FugitiveRow | None:
    if held(mortal.id) or await ctx.session.scalar(select(FugitiveRow.id).where(FugitiveRow.mortal_entity_id == mortal.id)) is not None:
        return None
    row = FugitiveRow(mortal_entity_id=mortal.id, kind=kind, pursuer_entity_id=pursuer, fled_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "fugitive.fled", roles={IncidentRole.ACTOR: mortal.id, IncidentRole.OPPONENT: pursuer}, facts={"kind": kind}, place=mortal.location_id)
    return row


async def why_flee(ctx: TickContext, mortal: EntityRow, realm: int) -> FugitiveKind | None:
    table = ctx.rules.fugitives
    roll = ctx.rng(f"flee.{mortal.id}.{ctx.epoch}")
    if mortal.social_class is SocialClass.SERF_OR_SLAVE and roll.chance(table.runaway_flee_pct):
        return FugitiveKind.RUNAWAY
    if (
        mortal.mortal_role in (MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR)
        and await ongoing_war_count(ctx.session, realm)
        and roll.chance(table.deserter_flee_pct)
    ):
        return FugitiveKind.DESERTER
    if await held_captive(ctx.session, mortal.id) is not None and roll.chance(table.escaped_captive_flee_pct):
        return FugitiveKind.ESCAPED_CAPTIVE
    if await deep_in_debt(ctx, mortal.id) and roll.chance(table.debtor_flee_pct):
        return FugitiveKind.DEBTOR
    if await law_param(ctx.session, realm, LawKind.RELIGIOUS_TOLERANCE, "level") == "persecution":
        mine, theirs = await patron_node(ctx.session, mortal.id), await patron_node(ctx.session, realm)
        if mine is not None and theirs is not None and mine != theirs and roll.chance(table.heretic_flee_pct):
            return FugitiveKind.HERETIC
    return None


async def deep_in_debt(ctx: TickContext, mortal_id: int) -> bool:
    owed = await ctx.session.scalar(
        select(RegistryRow.id).where(RegistryRow.kind == RegistryKind.DEBT, RegistryRow.counterparty_entity_id == mortal_id, RegistryRow.amount > 0).limit(1)
    )
    return owed is not None


async def take_flight(ctx: TickContext) -> int:
    fled = 0
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        .order_by(EntityRow.id)
    )
    for mortal in list(mortals):
        realm = await realm_of(ctx.session, mortal.location_id) if mortal.location_id is not None else None
        if realm is None or held(mortal.id):
            continue
        kind = await why_flee(ctx, mortal, realm)
        if kind is not None and await flee(ctx, mortal, kind, realm) is not None:
            fled += 1
    return fled


async def hunt_one(ctx: TickContext, row: FugitiveRow, *, by: int | None = None, certain: bool = False) -> bool:
    mortal = await living_entity(ctx.session, row.mortal_entity_id)
    if mortal is None or held(mortal.id) or "caught_epoch" in row.locked:
        return False
    if await refuge_of(ctx.session, mortal.id) is not None:
        return False
    chance = int(getattr(ctx.rules.fugitives, FUGITIVES[row.kind].hunt))
    if not certain and not ctx.rng(f"hunt.{row.id}.{ctx.epoch}").chance(chance):
        return False
    row.caught_epoch = ctx.epoch
    await imprison(ctx, mortal)
    await record(
        ctx,
        "fugitive.caught",
        roles={IncidentRole.VICTIM: mortal.id, IncidentRole.ACTOR: by if by is not None else row.pursuer_entity_id},
        facts={"kind": row.kind},
        place=mortal.location_id,
    )
    return True


async def free_in_cities(ctx: TickContext) -> int:
    term = ctx.rules.sanctuary.epochs(ctx.rules.sanctuary.free_city_term_years)
    freed = 0
    rows = await ctx.session.scalars(
        select(SanctuaryRow).where(SanctuaryRow.kind == SanctuaryKind.FREE_CITY, SanctuaryRow.state == SanctuaryState.SHELTERED).order_by(SanctuaryRow.id)
    )
    for row in list(rows):
        mortal = await living_entity(ctx.session, row.fugitive_entity_id)
        if mortal is None or held(mortal.id) or ctx.epoch - row.granted_epoch < term:
            continue
        row.state = SanctuaryState.ENDED
        if mortal.social_class is SocialClass.SERF_OR_SLAVE:
            mortal.social_class = SocialClass.CITIZEN
        fugitive = await ctx.session.scalar(select(FugitiveRow).where(FugitiveRow.mortal_entity_id == mortal.id))
        if fugitive is not None and "freed_epoch" not in fugitive.locked:
            fugitive.freed_epoch = ctx.epoch
        freed += 1
        await record(ctx, "sanctuary.freed", roles={IncidentRole.ACTOR: mortal.id, IncidentRole.HOST: row.host_entity_id}, place=row.host_entity_id)
    return freed


async def keep_fugitives(ctx: TickContext) -> int:
    moved = await take_flight(ctx)
    for row in await open_fugitives(ctx):
        moved += int(await hunt_one(ctx, row))
    return moved + await free_in_cities(ctx)
