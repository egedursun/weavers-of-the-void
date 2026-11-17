from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import CRAFT_SKILLS
from aerona.catalog.techniques import TECHNIQUES
from aerona.db.read_memo import memoized
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import GuildSecretRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.mind.book import best_skill
from aerona.engine.primitives.naming import seed_of

GUILDS = (FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD)
CRAFT_BRANCHES = frozenset({KnowledgeBranch.METALLURGY, KnowledgeBranch.ARCHITECTURE, KnowledgeBranch.TRADE, KnowledgeBranch.AGRICULTURE})
RANK = "rank"


@dataclass
class GuildTally:
    promoted: int = 0
    secrets: int = 0


def rank_for(rules_master: int, rules_fellow: int, rules_grand: int, skill: int) -> FactionRank:
    if skill >= rules_grand:
        return FactionRank.LEADER
    if skill >= rules_master:
        return FactionRank.OFFICER
    if skill >= rules_fellow:
        return FactionRank.MEMBER
    return FactionRank.NOVICE


async def guild_rows(ctx: TickContext) -> list[tuple[EntityRow, FactionProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(GUILDS)), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows]


async def rank_members(ctx: TickContext, guild: EntityRow, tally: GuildTally) -> None:
    table = ctx.rules.guild_ranks
    for member in list(await ctx.session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == guild.id))):
        if RANK in (member.locked or []) or held(member.mortal_entity_id):
            continue
        skill = await best_skill(ctx.session, member.mortal_entity_id, CRAFT_SKILLS)
        rank = rank_for(table.master_at, table.fellow_at, table.grandmaster_at, skill)
        if rank is not member.rank:
            member.rank = rank
            tally.promoted += 1


async def keep_secrets(ctx: TickContext, guild: EntityRow, profile: FactionProfileRow, tally: GuildTally) -> None:
    if profile.home_entity_id is None or held(profile.home_entity_id):
        return
    if not ctx.rng(seed_of("guild.secret", guild.id, ctx.epoch)).chance(ctx.rules.guild_ranks.secret_pct):
        return
    known = await ctx.session.scalars(
        select(HolderTechniqueRow)
        .where(HolderTechniqueRow.holder_entity_id == profile.home_entity_id, HolderTechniqueRow.secret.is_(False))
        .order_by(HolderTechniqueRow.technique)
    )
    for row in known:
        if TECHNIQUES[row.technique].branch not in CRAFT_BRANCHES:
            continue
        row.secret = True
        ctx.session.add(GuildSecretRow(guild_entity_id=guild.id, technique=row.technique, since_epoch=ctx.epoch))
        tally.secrets += 1
        return


async def tend_guilds(ctx: TickContext, tally: GuildTally) -> None:
    for guild, profile in await guild_rows(ctx):
        if held(guild.id):
            continue
        await rank_members(ctx, guild, tally)
        await keep_secrets(ctx, guild, profile, tally)


@memoized(FactionProfileRow)
async def guild_homes(session: AsyncSession) -> frozenset[int]:
    homes = await session.scalars(select(FactionProfileRow.home_entity_id).where(FactionProfileRow.kind == FactionKind.CRAFT_GUILD))
    return frozenset(home for home in homes if home is not None)


async def guild_standard(ctx: TickContext, community_id: int) -> int:
    return ctx.rules.guild_ranks.quality_bonus if community_id in await guild_homes(ctx.session) else 0


async def enrol_apprentice(ctx: TickContext, community_id: int, mortal_id: int) -> bool:
    guild = await ctx.session.scalar(
        select(FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.kind == FactionKind.CRAFT_GUILD, FactionProfileRow.home_entity_id == community_id)
        .limit(1)
    )
    if guild is None or held(guild) or await ctx.session.get(FactionMembershipRow, (guild, mortal_id)) is not None:
        return False
    ctx.session.add(FactionMembershipRow(faction_entity_id=guild, mortal_entity_id=mortal_id, rank=FactionRank.NOVICE, joined_epoch=ctx.epoch, locked=[]))
    return True
