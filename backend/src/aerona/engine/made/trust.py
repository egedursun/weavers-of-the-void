from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import InformationTrustRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import Authenticity
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import best_skill
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_percent, round_half_up

FALSE = frozenset({Authenticity.ALTERED, Authenticity.FORGED, Authenticity.GENERATED})
KEEPERS = (SkillKind.WRITING, SkillKind.LAW, SkillKind.CRYPTOGRAPHY, SkillKind.COMPUTING)


async def trust_of(ctx: TickContext, holder_id: int) -> InformationTrustRow:
    row = await ctx.session.get(InformationTrustRow, holder_id)
    if row is None:
        row = InformationTrustRow(holder_entity_id=holder_id, information_trust=60, shared_account_pct=100, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def censorship_on(ctx: TickContext, holder_id: int) -> int:
    networks = select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id == holder_id)
    rows = await ctx.session.scalars(select(NetworkProfileRow.censorship).where(NetworkProfileRow.network_entity_id.in_(networks)))
    return max(rows, default=0)


async def keeper_skill(ctx: TickContext, town: EntityRow) -> int:
    folk = await ctx.session.scalars(
        select(EntityRow.id).where(await present_in(ctx.session, town), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    )
    best = 0
    for mortal in folk:
        best = max(best, await best_skill(ctx.session, mortal, KEEPERS))
    return best


async def find_forgeries(ctx: TickContext, town: EntityRow, accounts: list[AccountRow]) -> int:
    table = ctx.rules.information
    if await keeper_skill(ctx, town) < table.detection_skill:
        return 0
    found = 0
    for account in accounts:
        if account.authenticity is Authenticity.UNKNOWN and "authenticity" not in account.locked:
            if ctx.rng(f"verify.{account.id}.{ctx.epoch}").chance(table.detection_chance):
                account.authenticity = Authenticity.GENUINE
            continue
        if account.authenticity in FALSE and account.credence > 0 and ctx.rng(f"forgery.{account.id}.{ctx.epoch}").chance(table.detection_chance):
            if "credence" not in account.locked:
                account.credence = 0
            found += 1
    if found:
        await note(ctx, f"The keepers of {town.name} found a false record.", key="trust.forgery_found", ids=[town.id])
    return found


async def tend(ctx: TickContext, town: EntityRow) -> None:
    table = ctx.rules.information
    row = await trust_of(ctx, town.id)
    accounts = list(await ctx.session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == town.id)))
    found = await find_forgeries(ctx, town, accounts)
    censorship = await censorship_on(ctx, town.id)
    if "information_trust" not in row.locked:
        blows = round_half_up(table.censorship_loss * censorship / PERCENT) + found * table.forgery_loss
        row.information_trust = clamp_percent(row.information_trust - blows + (table.recovery if not blows else 0))
    if "shared_account_pct" not in row.locked:
        genuine = sum(1 for account in accounts if account.authenticity is Authenticity.GENUINE)
        row.shared_account_pct = clamp_percent(genuine * PERCENT // len(accounts)) if accounts else PERCENT
    row.updated_epoch = ctx.epoch
    if row.information_trust < table.low_trust:
        for account in accounts:
            if "credence" not in account.locked:
                account.credence = clamp_percent(account.credence - 1)


@reads("table.accounts", "table.entities", "table.information_trust", "table.network_nodes", "table.network_profiles", "table.nodes", "table.skills")
@writes("table.accounts", "table.information_trust")
async def keep_trust(ctx: TickContext) -> None:
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        await tend(ctx, town)
        ctx.count("trust_kept")
    await ctx.session.flush()
