from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.intrigue import BELIEF_ATTRIBUTES
from aerona.catalog.life.intrigue import FALSE_CAMPFIRES_SKILL_KINDS
from aerona.catalog.life_traits import PACKAGE_KIND_TRAITS, having
from aerona.catalog.pacts import WILLLESS_LAWS
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.intrigue import IdentityRow, SecretRow
from aerona.db.tables.law_depth import OutlawRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, SpyAgentRow, SpyNetworkRow
from aerona.db.tables.minds import MindLawRow, MindProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import Visibility
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.intrigue import BeliefSource, IdentityReason, IntrigueSecret
from aerona.domain.enums.life_traits import PackageKindTrait
from aerona.domain.enums.military import AgentStatus, UnitKind
from aerona.domain.enums.mind import Facet
from aerona.domain.enums.society import SocialClass
from aerona.engine.communication.post import FACTS, SPIED, send
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.secrets import expose, keep_secret, learn
from aerona.engine.mind.book import best_skill
from aerona.engine.mind.split import facets_of
from aerona.engine.mortal.kin import partners_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import bond_exists, living_entity
from aerona.engine.primitives.stats import stat

CURSED_PACKAGES = having(PACKAGE_KIND_TRAITS, PackageKindTrait.HIDDEN_BY_BEARER)
NEIGHBOUR_HOPS = 1
DECEIVE_DEPTH = 60
SOLDIERS = "soldiers"
SCOUTS = frozenset({UnitKind.LIGHT_CAVALRY, UnitKind.LIGHT_INFANTRY, UnitKind.MOUNTED_ARCHERS, UnitKind.SKY_RIDERS})


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


async def hidden_lives(ctx: TickContext) -> list[tuple[int, IdentityReason, str | None, int | None]]:
    found: list[tuple[int, IdentityReason, str | None, int | None]] = []
    chance = ctx.rules.intrigue.exile_mask_pct
    outlaws = set(await ctx.session.scalars(select(OutlawRow.mortal_entity_id)))
    at_large = select(FugitiveRow.mortal_entity_id).where(FugitiveRow.caught_epoch.is_(None), FugitiveRow.freed_epoch.is_(None))
    for runner in sorted(outlaws | set(await ctx.session.scalars(at_large))):
        if ctx.rng(seed_of("intrigue.fugitive_name", runner)).chance(chance):
            found.append((runner, IdentityReason.FUGITIVE, None, None))
    heretics = select(SecretRow.holder_node_id).where(SecretRow.kind == IntrigueSecret.HERESY, SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.id)
    for heretic in await ctx.session.scalars(heretics):
        if ctx.rng(seed_of("intrigue.faith_mask", heretic)).chance(chance):
            found.append((heretic, IdentityReason.HIDDEN_FAITH, None, None))
    made = (
        select(MindProfileRow.node_id)
        .join(EntityRow, EntityRow.id == MindProfileRow.node_id)
        .join(MindLawRow, MindLawRow.world_id == EntityRow.world_id)
        .where(MindProfileRow.made_by_node_id.is_not(None), MindLawRow.made_minds.in_(list(WILLLESS_LAWS)))
        .order_by(MindProfileRow.node_id)
    )
    for mind in await ctx.session.scalars(made):
        if ctx.rng(seed_of("intrigue.passing", mind)).chance(chance):
            found.append((mind, IdentityReason.PASSING_KIND, None, None))
    return found


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
    wanted.extend(await hidden_lives(ctx))
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
        .where(await present_among(ctx.session, [target_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [target_id, *rows]


async def army_sizes(ctx: TickContext) -> dict[int, tuple[int, int | None, frozenset[UnitKind]]]:
    rows = await ctx.session.execute(
        select(ArmyRow.entity_id, ArmyRow.owner_entity_id, ArmyProfileRow.region_entity_id)
        .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == ArmyRow.entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), ArmyRow.war_id.is_not(None))
        .order_by(ArmyRow.entity_id)
    )
    found: dict[int, tuple[int, int | None, frozenset[UnitKind]]] = {}
    for army_id, owner, region in rows:
        units = list(await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id)))
        found[army_id] = (owner, region, frozenset(unit.kind for unit in units if unit.count > 0))
    return found


async def soldiers_of(ctx: TickContext, army_id: int) -> int:
    return sum(unit.count for unit in await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id)))


async def false_campfires(ctx: TickContext, army_id: int) -> int:
    commander = await ctx.session.scalar(select(ArmyRow.commander_entity_id).where(ArmyRow.entity_id == army_id))
    if commander is None:
        return 0
    cunning = await best_skill(ctx.session, commander, FALSE_CAMPFIRES_SKILL_KINDS)
    if not ctx.rng(seed_of("intrigue.campfires", army_id, ctx.epoch)).chance(cunning * ctx.rules.belief_state.feint_pct / PERCENT):
        return 0
    return ctx.rules.belief_state.campfire_pct


async def scout_reports(ctx: TickContext, tally: SourceTally) -> None:
    armies = await army_sizes(ctx)
    for army_id, (owner, region, kinds) in armies.items():
        if region is None or held(owner) or not kinds & SCOUTS:
            continue
        for other_id, (other_owner, other_region, _) in armies.items():
            if other_id == army_id or other_region != region or other_owner == owner:
                continue
            if not await bond_exists(ctx.session, owner, other_owner, BondKind.ENEMY):
                continue
            seen = await soldiers_of(ctx, other_id)
            fires = await false_campfires(ctx, other_id)
            if fires:
                planted = round_half_up(seen * (PERCENT + fires) / PERCENT)
                if await believe(
                    ctx, owner, other_id, SOLDIERS, planted, source=BeliefSource.DECEPTION, confidence=ctx.rules.belief_state.scout_confidence, false=True
                ):
                    tally.beliefs += 1
                    ctx.count("false_campfires_believed")
                continue
            if await believe(ctx, owner, other_id, SOLDIERS, seen, source=BeliefSource.SCOUT, confidence=ctx.rules.belief_state.scout_confidence):
                tally.beliefs += 1


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


def shown_facts(community: EntityRow) -> list[tuple[str, int]]:
    return [(attribute, truth) for attribute in BELIEF_ATTRIBUTES if (truth := stat(community, attribute)) is not None]


async def neighbours_seen(ctx: TickContext, atlas: RegionAtlas, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_state.observe_confidence
    communities = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES))).order_by(EntityRow.id)
        )
    )
    homes = {community.id: atlas.top_region(community.id) for community in communities}
    shown = {community.id: shown_facts(community) for community in communities}
    by_world: dict[int | None, list[EntityRow]] = defaultdict(list)
    for community in communities:
        by_world[community.world_id].append(community)
    for watcher in communities:
        if held(watcher.id):
            continue
        home = homes[watcher.id]
        for other in by_world[watcher.world_id]:
            if other.id == watcher.id:
                continue
            hops = atlas.region_hops(home, homes[other.id])
            if hops is None or hops > NEIGHBOUR_HOPS:
                continue
            for attribute, truth in shown[other.id]:
                if await believe(ctx, watcher.id, other.id, attribute, truth, source=BeliefSource.OBSERVATION, confidence=confidence):
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


SECRETS_FIXUP = "secrets.w52"


async def backfill_power_secrets(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, SECRETS_FIXUP):
        return 0
    kept = 0
    masks = (
        select(IdentityRow).where(IdentityRow.reason == IdentityReason.HIDDEN_POWER, IdentityRow.exposed_epoch.is_(None)).order_by(IdentityRow.mortal_node_id)
    )
    for mask in list(await ctx.session.scalars(masks)):
        if await keep_secret(ctx, mask.mortal_node_id, IntrigueSecret.HIDDEN_POWER, source="identity.hidden_power") is not None:
            kept += 1
    ctx.session.add(AppliedFixupRow(key=SECRETS_FIXUP, result={"secrets": kept}))
    await ctx.session.flush()
    return kept
