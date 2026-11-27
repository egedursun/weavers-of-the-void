from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.identity import IDENTITY_LAYERS, NEW_LAYERS, SALIENCE_DRIVERS, VOTE_LAYERS
from aerona.catalog.kinds.war_causes import WAR_CAUSES
from aerona.catalog.life.belonging import CROSSING_PUSHES_IDENTITY_LAYERS, GUILD_PUSHES_IDENTITY_LAYERS
from aerona.catalog.tongues import POLICIES
from aerona.db.fast_session import rows_by_prefix
from aerona.db.fixups import fixup_due
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.arts import MatchRow
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import CommemorationRow, MovementRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.estates import MovementSupportRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.folkways import PurityRankRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.tongues import LanguagePolicyRow, ScriptRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import CollectiveActKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.tongues import LanguageStage, ScriptChangeCause
from aerona.domain.enums.war import WarStatus
from aerona.engine.belonging.effects import approach
from aerona.engine.belonging.values import GUILDS, Value, values_of
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.recording.record import record

COMMUNITIES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
PERSECUTING = "persecution"
UNSHELTERED = frozenset({"persecution", "none"})
FAITH_CAUSES = frozenset(cause for cause, spec in WAR_CAUSES.items() if spec.over_faith)
Pushes = dict[int, dict[IdentityLayer, tuple[int, SalienceDriver]]]


@dataclass
class IdentityTally:
    communities: int = 0
    mortals: int = 0
    stirred: int = 0
    crossed: int = 0


def push(pushes: Pushes, community: int, layer: IdentityLayer, amount: int, driver: SalienceDriver) -> None:
    current = pushes[community].get(layer)
    total = (current[0] if current is not None else 0) + amount
    strongest = driver if current is None or abs(amount) >= abs(current[0]) else current[1]
    pushes[community][layer] = (total, strongest)


async def war_pushes(ctx: TickContext, atlas: RegionAtlas, communities: list[EntityRow], pushes: Pushes) -> None:
    table = ctx.rules.identities
    holy = set(
        await ctx.session.scalars(
            select(WarSideRow.entity_id)
            .join(WarRow, WarRow.id == WarSideRow.war_id)
            .where(WarRow.status == WarStatus.ONGOING, WarRow.cause.in_(list(FAITH_CAUSES)), WarSideRow.left_epoch.is_(None))
        )
    )
    targets: dict[int, set[int]] = defaultdict(set)
    for region, target in await ctx.session.execute(
        select(ArmyProfileRow.region_entity_id, ArmyProfileRow.target_entity_id)
        .join(EntityRow, EntityRow.id == ArmyProfileRow.army_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, ArmyProfileRow.region_entity_id.is_not(None), ArmyProfileRow.target_entity_id.is_not(None))
    ):
        if region is not None and target is not None:
            targets[region].add(target)
    for community in communities:
        realm = await realm_of(ctx.session, community.id)
        if realm is not None and realm in holy:
            push(pushes, community.id, IdentityLayer.FAITH, table.holy_war, SalienceDriver.HOLY_WAR)
        region = atlas.top_region(community.id)
        if region is not None and targets.get(region, set()) & {community.id, *([realm] if realm is not None else [])}:
            push(pushes, community.id, IdentityLayer.PEOPLE, table.invasion, SalienceDriver.INVASION)
            push(pushes, community.id, IdentityLayer.POLITY, table.invasion, SalienceDriver.INVASION)


async def hunger_pushes(ctx: TickContext, atlas: RegionAtlas, pushes: Pushes) -> None:
    lands = set(
        await ctx.session.scalars(
            select(NotableYearRow.region_entity_id).where(NotableYearRow.kind == NotableYearKind.HUNGER, NotableYearRow.epoch >= ctx.epoch - 1)
        )
    )
    for land in sorted(item for item in lands if item is not None):
        for community in atlas.communities_in(land):
            push(pushes, community, IdentityLayer.CLASS, ctx.rules.identities.famine, SalienceDriver.FAMINE)


async def movement_pushes(ctx: TickContext, pushes: Pushes) -> None:
    table = ctx.rules.identities
    for row in await ctx.session.scalars(select(MovementRow).where(MovementRow.ended_epoch.is_(None)).order_by(MovementRow.id)):
        if row.act is CollectiveActKind.STRIKE:
            push(pushes, row.settlement_entity_id, IdentityLayer.PROFESSION, table.strike, SalienceDriver.STRIKE)
            continue
        if row.cult_entity_id is not None:
            push(pushes, row.settlement_entity_id, IdentityLayer.FAITH, table.rhetoric, SalienceDriver.RHETORIC)
        if row.faction_entity_id is not None:
            profile = await ctx.session.get(FactionProfileRow, row.faction_entity_id)
            layer = IdentityLayer.PROFESSION if profile is not None and profile.kind in GUILDS else IdentityLayer.CIRCLE
            push(pushes, row.settlement_entity_id, layer, table.rhetoric, SalienceDriver.RHETORIC)


async def apart_pushes(ctx: TickContext, communities: list[EntityRow], pushes: Pushes) -> None:
    table = ctx.rules.identities
    quarters = set(await ctx.session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.kind == DistrictKind.FOREIGN_QUARTER)))
    castes = set(await ctx.session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.purity_rank_id.is_not(None))))
    apart = set(
        await ctx.session.scalars(select(PurityRankRow.people_entity_id).where((PurityRankRow.commensal.is_(True)) | (PurityRankRow.endogamous.is_(True))))
    )
    for community in communities:
        if community.id in quarters:
            push(pushes, community.id, IdentityLayer.PEOPLE, table.segregation, SalienceDriver.SEGREGATION)
        folk = await people_of(ctx.session, community)
        if (folk is not None and folk.id in apart) or community.id in castes:
            push(pushes, community.id, IdentityLayer.CLASS, table.segregation, SalienceDriver.SEGREGATION)


async def crossing_pushes(ctx: TickContext, atlas: RegionAtlas, pushes: Pushes, tally: IdentityTally) -> None:
    table = ctx.rules.identities
    for first_id, second_id in await ctx.session.execute(select(MarriageRow.first_id, MarriageRow.second_id).where(MarriageRow.end_epoch.is_(None))):
        first, second = await ctx.session.get(EntityRow, first_id), await ctx.session.get(EntityRow, second_id)
        if first is None or second is None or first.location_id is None or first.location_id != second.location_id:
            continue
        mine, theirs = await values_of(ctx.session, atlas, first), await values_of(ctx.session, atlas, second)
        for layer in CROSSING_PUSHES_IDENTITY_LAYERS:
            if mine[layer][0] is not None and theirs[layer][0] is not None and mine[layer][0] != theirs[layer][0]:
                push(pushes, first.location_id, layer, -table.crossing, SalienceDriver.CROSSING)
                tally.crossed += 1


async def guild_pushes(ctx: TickContext, atlas: RegionAtlas, pushes: Pushes, tally: IdentityTally) -> None:
    table = ctx.rules.identities
    guilds = await ctx.session.execute(
        select(EntityRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(GUILDS)), EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        .order_by(EntityRow.id)
    )
    for (guild,) in guilds.all():
        members = await ctx.session.scalars(
            select(EntityRow)
            .join(BondRow, BondRow.source_node_id == EntityRow.id)
            .where(BondRow.target_node_id == guild.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
            .order_by(EntityRow.id)
        )
        values = [await values_of(ctx.session, atlas, member) for member in members]
        for layer in GUILD_PUSHES_IDENTITY_LAYERS:
            if guild.location_id is not None and len({row[layer][0] for row in values if row[layer][0] is not None}) > 1:
                push(pushes, guild.location_id, layer, -table.crossing, SalienceDriver.CROSSING)
                tally.crossed += 1


async def tongue_pushes(ctx: TickContext, communities: list[EntityRow], pushes: Pushes) -> None:
    table = ctx.rules.identity
    moving = [policy for policy, spec in POLICIES.items() if spec.identity]
    policies = await ctx.session.scalars(
        select(LanguagePolicyRow).where(LanguagePolicyRow.policy.in_(moving)).order_by(LanguagePolicyRow.holder_entity_id, LanguagePolicyRow.language_entity_id)
    )
    pressed = {(row.holder_entity_id, row.language_entity_id): row.policy for row in policies}
    imposed_since = ctx.epoch - 1
    for community in communities:
        tongue = await spoken_language(ctx.session, community.id)
        if tongue is None:
            continue
        profile = await ctx.session.get(LanguageProfileRow, tongue.id)
        if profile is not None and profile.stage is LanguageStage.REVIVED:
            push(pushes, community.id, IdentityLayer.LANGUAGE, ctx.rules.tongues.revived_identity, SalienceDriver.COMMEMORATION)
        script = await ctx.session.get(ScriptRow, profile.script_id) if profile is not None and profile.script_id is not None else None
        if script is not None and script.cause is ScriptChangeCause.IMPOSITION and script.epoch >= imposed_since:
            push(pushes, community.id, IdentityLayer.LANGUAGE, ctx.rules.script.imposition_identity, SalienceDriver.PERSECUTION)
        realm = await realm_of(ctx.session, community.id)
        policy = pressed.get((realm, tongue.id)) if realm is not None else None
        if policy is not None:
            spec = POLICIES[policy]
            push(pushes, community.id, IdentityLayer.LANGUAGE, spec.identity * table.language_suppression_rise, spec.driver)


async def kind_pushes(ctx: TickContext, communities: list[EntityRow], laws: LawBook, pushes: Pushes) -> None:
    table = ctx.rules.identity
    made_homes = set(
        await ctx.session.scalars(
            select(EntityRow.location_id)
            .join(MindProfileRow, MindProfileRow.node_id == EntityRow.id)
            .where(MindProfileRow.origin != MindOrigin.BORN, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        )
    )
    for community in communities:
        realm = await realm_of(ctx.session, community.id)
        if realm is not None and laws.in_force(realm, LawKind.MIND_STATUS) is not None:
            push(pushes, community.id, IdentityLayer.KIND, table.kind_law_rise, SalienceDriver.SEGREGATION)
        if community.id in made_homes:
            push(pushes, community.id, IdentityLayer.KIND, table.kind_contact_rise, SalienceDriver.CROSSING)


async def cause_pushes(ctx: TickContext, pushes: Pushes) -> None:
    table = ctx.rules.identity
    backing = await ctx.session.scalars(
        select(MovementSupportRow.community_entity_id)
        .where(MovementSupportRow.share >= ctx.rules.movements.protest_at)
        .order_by(MovementSupportRow.community_entity_id)
    )
    for community_id in sorted(set(backing)):
        push(pushes, community_id, IdentityLayer.CAUSE, table.cause_rise, SalienceDriver.RHETORIC)


async def persecution_pushes(ctx: TickContext, communities: list[EntityRow], laws: LawBook, pushes: Pushes) -> None:
    rise = SALIENCE_DRIVERS[SalienceDriver.PERSECUTION].rise(ctx.rules)
    bonds = BondRepository(ctx.session)
    for community in communities:
        realm = await realm_of(ctx.session, community.id)
        if realm is None or realm == community.id:
            continue
        if laws.param(realm, LawKind.RELIGIOUS_TOLERANCE, "level") == PERSECUTING:
            mine, theirs = await bonds.patron(community.id), await bonds.patron(realm)
            if mine is not None and theirs is not None and mine != theirs:
                push(pushes, community.id, IdentityLayer.FAITH, rise, SalienceDriver.PERSECUTION)
        if laws.param(realm, LawKind.FOREIGNER_RIGHTS, "level") in UNSHELTERED:
            folk = await people_of(ctx.session, community)
            core = await ctx.session.scalar(select(PolityProfileRow.core_entity_id).where(PolityProfileRow.polity_entity_id == realm))
            if folk is not None and core is not None and folk.id != core:
                push(pushes, community.id, IdentityLayer.PEOPLE, rise, SalienceDriver.PERSECUTION)


async def memory_pushes(ctx: TickContext, pushes: Pushes) -> None:
    rise = SALIENCE_DRIVERS[SalienceDriver.COMMEMORATION].rise(ctx.rules)
    for holder in await ctx.session.scalars(
        select(CommemorationRow.holder_entity_id).where(CommemorationRow.last_observed_epoch == ctx.epoch).order_by(CommemorationRow.holder_entity_id)
    ):
        push(pushes, holder, IdentityLayer.PEOPLE, rise, SalienceDriver.COMMEMORATION)


async def vote_pushes(ctx: TickContext, communities: list[EntityRow], pushes: Pushes) -> None:
    rise = SALIENCE_DRIVERS[SalienceDriver.ELECTION].rise(ctx.rules)
    votes = list(await ctx.session.scalars(select(ReferendumRow).where(ReferendumRow.held_epoch == ctx.epoch).order_by(ReferendumRow.id)))
    if not votes:
        return
    for community in communities:
        realm = await realm_of(ctx.session, community.id)
        for vote in votes:
            if vote.holder_node_id in {community.id, realm}:
                push(pushes, community.id, VOTE_LAYERS[vote.subject], rise, SalienceDriver.ELECTION)


async def match_pushes(ctx: TickContext, pushes: Pushes) -> None:
    rise = SALIENCE_DRIVERS[SalienceDriver.CONTEST].rise(ctx.rules)
    for match in await ctx.session.scalars(select(MatchRow).where(MatchRow.epoch == ctx.epoch).order_by(MatchRow.id)):
        for side in (match.home_entity_id, match.away_entity_id):
            team = await ctx.session.get(EntityRow, side)
            home = side if team is not None and team.entity_type is EntityType.SETTLEMENT else team.location_id if team is not None else None
            if home is not None:
                push(pushes, home, IdentityLayer.LOCALITY, rise, SalienceDriver.CONTEST)
                push(pushes, home, IdentityLayer.CIRCLE, rise, SalienceDriver.CONTEST)


def write(row: HeldIdentityRow, value: Value, salience: int, driver: SalienceDriver, epoch: int) -> None:
    if "value_node_id" not in row.locked:
        row.value_node_id = value[0]
    if "value_label" not in row.locked:
        row.value_label = value[1]
    if "salience" not in row.locked:
        row.salience = salience
    if "driver" not in row.locked:
        row.driver = driver
    row.updated_epoch = epoch


async def keep_holder(
    ctx: TickContext, atlas: RegionAtlas, holder: EntityRow, targets: dict[IdentityLayer, tuple[int, SalienceDriver]], pct: int, *, told: bool = False
) -> None:
    values = await values_of(ctx.session, atlas, holder)
    stored = {row.layer: row for row in await rows_by_prefix(ctx.session, HeldIdentityRow, holder.id)}
    for layer in IdentityLayer:
        row = stored.get(layer)
        target, driver = targets[layer]
        if row is None:
            row = HeldIdentityRow(
                holder_entity_id=holder.id, layer=layer, strength=50, salience=ctx.rules.identities.base_salience, updated_epoch=ctx.epoch, locked=[]
            )
            ctx.session.add(row)
        before, was = row.salience, row.driver
        write(row, values[layer], approach(row.salience, target, pct), driver, ctx.epoch)
        if told:
            await tell_change(ctx, holder, row, before=before, was=was)


async def tell_change(ctx: TickContext, holder: EntityRow, row: HeldIdentityRow, *, before: int, was: SalienceDriver) -> None:
    if before < ctx.rules.identities.fault_at <= row.salience:
        await record(ctx, "identity.rose", roles={IncidentRole.SUBJECT: holder.id}, facts={"layer": row.layer, "salience": row.salience})
    if row.driver is not was and row.driver is not SalienceDriver.BASELINE:
        await record(ctx, "identity.driven", roles={IncidentRole.SUBJECT: holder.id}, facts={"layer": row.layer, "driver": row.driver})


async def keep_identities(ctx: TickContext, tally: IdentityTally) -> None:
    table = ctx.rules.identities
    atlas = await RegionAtlas.load(ctx.session)
    communities = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITIES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    pushes: Pushes = defaultdict(dict)
    laws = await LawBook.load(ctx.session)
    await tongue_pushes(ctx, communities, pushes)
    await kind_pushes(ctx, communities, laws, pushes)
    await cause_pushes(ctx, pushes)
    await persecution_pushes(ctx, communities, laws, pushes)
    await memory_pushes(ctx, pushes)
    await vote_pushes(ctx, communities, pushes)
    await match_pushes(ctx, pushes)
    await war_pushes(ctx, atlas, communities, pushes)
    await hunger_pushes(ctx, atlas, pushes)
    await movement_pushes(ctx, pushes)
    await apart_pushes(ctx, communities, pushes)
    await guild_pushes(ctx, atlas, pushes, tally)
    await crossing_pushes(ctx, atlas, pushes, tally)
    for community in communities:
        if held(community.id):
            continue
        stirred = pushes.get(community.id, {})
        targets = {
            layer: (clamp_int(IDENTITY_LAYERS[layer].base(ctx.rules) + stirred[layer][0], 0, 100), stirred[layer][1])
            if layer in stirred
            else (IDENTITY_LAYERS[layer].base(ctx.rules), SalienceDriver.BASELINE)
            for layer in IdentityLayer
        }
        await keep_holder(ctx, atlas, community, targets, table.decay_pct, told=True)
        tally.communities += 1
        tally.stirred += len(stirred)
    await ctx.session.flush()
    mortals = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    homes: dict[int, dict[IdentityLayer, HeldIdentityRow]] = {}
    for mortal in list(mortals):
        if held(mortal.id):
            continue
        home = mortal.location_id
        if home and home not in homes:
            homes[home] = {row.layer: row for row in await ctx.session.scalars(select(HeldIdentityRow).where(HeldIdentityRow.holder_entity_id == home))}
        rows = homes.get(home, {}) if home else {}
        targets = {
            layer: (rows[layer].salience, rows[layer].driver) if layer in rows else (IDENTITY_LAYERS[layer].base(ctx.rules), SalienceDriver.BASELINE)
            for layer in IdentityLayer
        }
        await keep_holder(ctx, atlas, mortal, targets, table.mortal_pct)
        tally.mortals += 1
    await ctx.session.flush()


LAYERS_FIXUP = "identity.w52"


async def backfill_layers(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, LAYERS_FIXUP):
        return 0
    atlas = await RegionAtlas.load(ctx.session)
    holders = sorted(set(await ctx.session.scalars(select(HeldIdentityRow.holder_entity_id))))
    filled = 0
    for holder_id in holders:
        holder = await ctx.session.get(EntityRow, holder_id)
        if holder is None or held(holder_id):
            continue
        have = {row.layer for row in await rows_by_prefix(ctx.session, HeldIdentityRow, holder_id)}
        missing = [layer for layer in NEW_LAYERS if layer not in have]
        if not missing:
            continue
        values = await values_of(ctx.session, atlas, holder)
        for layer in missing:
            ctx.session.add(
                HeldIdentityRow(
                    holder_entity_id=holder_id,
                    layer=layer,
                    value_node_id=values[layer][0],
                    value_label=values[layer][1],
                    strength=50,
                    salience=IDENTITY_LAYERS[layer].base(ctx.rules),
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
            )
            filled += 1
    ctx.session.add(AppliedFixupRow(key=LAYERS_FIXUP, result={"layers": filled}))
    await ctx.session.flush()
    return filled
