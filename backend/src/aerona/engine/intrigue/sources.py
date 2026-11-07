from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.intrigue import BELIEF_ATTRIBUTES
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.intrigue import IdentityRow, SecretRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Visibility
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.intrigue import BeliefSource, IdentityReason, IntrigueSecret
from aerona.domain.enums.military import AgentStatus
from aerona.domain.enums.mind import Facet
from aerona.domain.enums.society import SocialClass
from aerona.engine.communication.post import FACTS, SPIED, send
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.secrets import expose, keep_secret, learn
from aerona.engine.mind.split import facets_of
from aerona.engine.mortal.kin import partners_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat

CURSED_PACKAGES = frozenset({PackageKind.VAMPIRISM})
NEIGHBOUR_HOPS = 1
DECEIVE_DEPTH = 60


@dataclass
class SourceTally:
    secrets: int = 0
    identities: int = 0
    learned: int = 0
    exposed: int = 0
    beliefs: int = 0


async def hidden_conditions(ctx: TickContext, tally: SourceTally) -> None:
    for row in list(await ctx.session.scalars(select(AfflictionRow).where(AfflictionRow.cured_epoch.is_(None)).order_by(AfflictionRow.id))):
        if PACKAGES[row.package].visibility is Visibility.HIDDEN and await keep_secret(
            ctx, row.bearer_node_id, IntrigueSecret.HIDDEN_CONDITION, source=f"affliction.{row.package.value}"
        ):
            tally.secrets += 1


async def noble_debts(ctx: TickContext, tally: SourceTally) -> None:
    threshold = ctx.rules.intrigue.debt_secret_at
    for row in list(await ctx.session.scalars(select(HouseholdRow).where(HouseholdRow.social_class == SocialClass.NOBLE).order_by(HouseholdRow.id))):
        if row.head_node_id is None or sum((row.debts or {}).values()) < threshold:
            continue
        if await keep_secret(ctx, row.head_node_id, IntrigueSecret.DEBT, source=f"household.{row.id}"):
            tally.secrets += 1


async def hidden_memberships(ctx: TickContext, tally: SourceTally) -> None:
    hidden = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind == FactionKind.SECRET_SOCIETY)
    rows = await ctx.session.scalars(
        select(FactionMembershipRow)
        .where(FactionMembershipRow.faction_entity_id.in_(hidden))
        .order_by(FactionMembershipRow.faction_entity_id, FactionMembershipRow.mortal_entity_id)
    )
    for row in list(rows):
        if await keep_secret(ctx, row.mortal_entity_id, IntrigueSecret.SECRET_CULT_MEMBERSHIP, about_id=row.faction_entity_id, source="faction"):
            tally.secrets += 1


async def masked_lives(ctx: TickContext, namer: Namer, tally: SourceTally) -> None:
    masked = set(await ctx.session.scalars(select(IdentityRow.mortal_node_id)))
    wanted: list[tuple[int, IdentityReason, str | None, int | None]] = []
    for row in await ctx.session.scalars(select(AfflictionRow).where(AfflictionRow.cured_epoch.is_(None), AfflictionRow.package.in_(list(CURSED_PACKAGES)))):
        wanted.append((row.bearer_node_id, IdentityReason.BLOOD_CURSE, None, None))
    for agent in await ctx.session.scalars(select(SpyAgentRow).where(SpyAgentRow.status == AgentStatus.ACTIVE, SpyAgentRow.mortal_entity_id.is_not(None))):
        network = await ctx.session.get(SpyNetworkRow, agent.network_id)
        if agent.mortal_entity_id is not None:
            wanted.append((agent.mortal_entity_id, IdentityReason.SPY, agent.cover.value, network.target_entity_id if network is not None else None))
    for flag in await ctx.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.EXILE)):
        if ctx.rng(seed_of("intrigue.exile_name", flag)).chance(ctx.rules.intrigue.exile_mask_pct):
            wanted.append((flag, IdentityReason.EXILE, None, None))
    for mortal_id, reason, cover, community_id in wanted:
        if mortal_id in masked or held(mortal_id):
            continue
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL:
            continue
        name = await namer.person([mortal], seed_of("false_name", mortal.id, reason.value), mortal.world_id)
        if name and await assume(ctx, mortal, reason, name, cover_role=cover, community_id=community_id or mortal.location_id):
            masked.add(mortal_id)
            tally.identities += 1


async def watched_ids(ctx: TickContext, target_id: int) -> list[int]:
    rows = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.location_id == target_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [target_id, *rows]


async def spy_reports(ctx: TickContext, tally: SourceTally) -> None:
    table, beliefs = ctx.rules.intrigue, ctx.rules.belief_state
    for network in list(await ctx.session.scalars(select(SpyNetworkRow).order_by(SpyNetworkRow.id))):
        if held(network.owner_entity_id):
            continue
        target = await living_entity(ctx.session, network.target_entity_id)
        if target is None:
            continue
        facts = {attribute: value for attribute in BELIEF_ATTRIBUTES if (value := stat(target, attribute)) is not None}
        courier = next((node for node in (network.spymaster_entity_id, *network.agent_ids) if node is not None and node != network.owner_entity_id), target.id)
        report = {FACTS: {str(target.id): facts}, SPIED: True}
        if facts and await send(ctx, courier, network.owner_entity_id, DispatchContent.INTELLIGENCE, Medium.LETTER, payload=report, origin_id=target.id):
            tally.beliefs += len(facts)
        if network.depth >= DECEIVE_DEPTH and ctx.rng(seed_of("intrigue.deceive", network.id, ctx.epoch)).chance(table.deceive_pct):
            truth = stat(target, "defense")
            lie = (truth or 0) // 2
            if truth is not None and await believe(
                ctx, target.id, network.owner_entity_id, "defense", lie, source=BeliefSource.DECEPTION, confidence=beliefs.deception_confidence, false=True
            ):
                tally.beliefs += 1
        if not ctx.rng(seed_of("intrigue.spy_learn", network.id, ctx.epoch)).chance(table.spy_learn_pct):
            continue
        watched = await watched_ids(ctx, target.id)
        found = await ctx.session.scalar(
            select(SecretRow)
            .where(SecretRow.holder_node_id.in_(watched), SecretRow.exposed_epoch.is_(None))
            .order_by(SecretRow.severity.desc(), SecretRow.id)
            .limit(1)
        )
        if found is not None and await learn(ctx, found, network.owner_entity_id):
            tally.learned += 1


async def neighbours_seen(ctx: TickContext, atlas: RegionAtlas, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_state.observe_confidence
    communities = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES))).order_by(EntityRow.id)
        )
    )
    for watcher in communities:
        if held(watcher.id):
            continue
        home = atlas.top_region(watcher.id)
        for other in communities:
            if other.id == watcher.id or other.world_id != watcher.world_id:
                continue
            hops = atlas.region_hops(home, atlas.top_region(other.id))
            if hops is None or hops > NEIGHBOUR_HOPS:
                continue
            for attribute in BELIEF_ATTRIBUTES:
                truth = stat(other, attribute)
                if truth is not None and await believe(ctx, watcher.id, other.id, attribute, truth, source=BeliefSource.OBSERVATION, confidence=confidence):
                    tally.beliefs += 1


async def likeness_noticed(ctx: TickContext, tally: SourceTally) -> None:
    table = ctx.rules.intrigue
    rows = await ctx.session.scalars(
        select(SecretRow).where(SecretRow.kind == IntrigueSecret.TRUE_PARENTAGE, SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.id)
    )
    for secret in list(rows):
        genome = await ctx.session.get(GenomeRow, secret.holder_node_id)
        father = secret.about_node_id
        if genome is None or father is None or (genome.likeness or {}).get(str(father), 0) < table.likeness_notice:
            continue
        if not ctx.rng(seed_of("intrigue.likeness", secret.id, ctx.epoch)).chance(table.likeness_notice_pct):
            continue
        noticer = next(iter(sorted(set(await partners_of(ctx.session, father)) - set(secret.known_by))), None)
        if noticer is not None and await learn(ctx, secret, noticer):
            tally.learned += 1
        elif await expose(ctx, secret):
            tally.exposed += 1


async def hidden_birth(ctx: TickContext, first: EntityRow, second: EntityRow, children: list[EntityRow]) -> None:
    wed = [parent for parent in (first, second) if set(await partners_of(ctx.session, parent.id)) - {first.id, second.id}]
    if not wed:
        return
    parents = (first.id, second.id)
    for child in children:
        for parent in wed:
            await keep_secret(ctx, parent.id, IntrigueSecret.ILLEGITIMATE_CHILD, about_id=child.id, known_by=parents, source="birth")
        sire = next((parent for parent in (first, second) if parent not in wed), wed[0])
        await keep_secret(ctx, child.id, IntrigueSecret.TRUE_PARENTAGE, about_id=sire.id, known_by=parents, source="birth")


async def hidden_rites(ctx: TickContext, caster: EntityRow, rite: EntityRow, row: RiteProfileRow) -> None:
    if caster.entity_type is not EntityType.MORTAL:
        return
    if row.heretical:
        await keep_secret(ctx, caster.id, IntrigueSecret.HERESY, about_id=rite.id, source=f"rite.{rite.id}")
    if row.school is MagicSchool.VOID:
        await keep_secret(ctx, caster.id, IntrigueSecret.DEAL_WITH_OUTER_BEING, about_id=rite.id, source=f"rite.{rite.id}")


async def cowardice(ctx: TickContext, commander_id: int, side_id: int) -> None:
    facets = await facets_of(ctx.session, commander_id)
    if facets.get(Facet.ANXIETY, 0) < ctx.rules.intrigue.coward_anxiety:
        return
    if ctx.rng(seed_of("intrigue.coward", commander_id, ctx.epoch)).chance(ctx.rules.intrigue.coward_pct):
        await keep_secret(ctx, commander_id, IntrigueSecret.COWARDICE_IN_BATTLE, about_id=side_id, source="battle")
