from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.catalog.intrigue import PLOT_STEPS, SCHEMES
from aerona.catalog.life.intrigue import SECRETS_KEPT_ELSEWHERE, SKILL_SKILL_KINDS
from aerona.catalog.relations import HOSTILE_KEYS
from aerona.catalog.weather import has_trait
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.affairs import CourtPositionRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.intrigue import FavourRow, HookRow, SchemeRow, TrueNameRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.operations import AdmiraltyRow
from aerona.db.tables.polity import ClaimRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import SettlementTreasuryRow
from aerona.db.tables.warfare import CaptiveRow, SiegeRow
from aerona.db.write_guard import free_rows, held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind, WeatherTrait
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand, HookSource, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.domain.enums.mind import Attribute, MemoryKind, TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind, DeathCause
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.statecraft import CourtPosition
from aerona.domain.enums.tongues import LanguageModality
from aerona.domain.enums.unions import UnionPurpose
from aerona.domain.enums.war import CaptiveStatus, SiegeStatus
from aerona.engine.arts.forgery import FORGEABLE, forge, work_of
from aerona.engine.communication.dispatches import ARMY, REGION, commanders_of
from aerona.engine.communication.post import FORGER, send
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.local import weather_here
from aerona.engine.folkways.biases import lean
from aerona.engine.intrigue.favours import owe
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.leverage import leaned_on
from aerona.engine.intrigue.names import teach_name
from aerona.engine.intrigue.secrets import expose, grant_hook, keep_secret
from aerona.engine.means.security import attempt_theft
from aerona.engine.mind.book import best_skill, traits_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mind.split import attribute
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.mythic.geasa import spring_trap
from aerona.engine.polity.trials import frame_case, report_crime
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import connect, living_entity, spoken_language
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.records import death_path
from aerona.engine.relations.book import ensure_relation, shift
from aerona.engine.services.war import release_captive, take_captive
from aerona.engine.storyteller.drama import pressed, pressing_foe
from aerona.engine.tongues.modality import modality_of

TEN = 10
HIRE_SEEK = 12
WEALTH = "wealth"
OPEN = frozenset({SchemePhase.RECRUIT, SchemePhase.PREPARE, SchemePhase.EXECUTE})
FRIENDS_AT = 30
SWAY = 20
POISON_PCT = 5
PHASE = "phase"
SCHEME_SLOT = "scheme"
SABOTAGES = ((ScarKind.BLIGHTED, "blighted with pests"), (ScarKind.BURNED, "burned"), (ScarKind.MADE_BARREN, "salted"))


@dataclass
class SchemeTally:
    begun: int = 0
    succeeded: int = 0
    failed: int = 0
    exposed: int = 0


async def begin_scheme(ctx: TickContext, owner: EntityRow, kind: PlotKind, target: EntityRow | None) -> SchemeRow | None:
    if held(owner.id) or (target is not None and held(target.id)):
        return None
    spec = SCHEMES[kind]
    row = SchemeRow(
        owner_node_id=owner.id,
        kind=kind,
        target_node_id=target.id if target is not None else None,
        agents=[],
        power=0,
        secrecy=spec.secrecy,
        progress=0,
        phase=SchemePhase.RECRUIT,
        discovered_by=[],
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def skill(ctx: TickContext, node_id: int) -> int:
    return await best_skill(ctx.session, node_id, SKILL_SKILL_KINDS)


async def candidates(ctx: TickContext, scheme: SchemeRow) -> list[tuple[int, bool]]:
    owner = scheme.owner_node_id
    friends = await ctx.session.scalars(
        select(RelationshipRow.subject_node_id)
        .where(RelationshipRow.holder_node_id == owner, RelationshipRow.friendship >= FRIENDS_AT)
        .order_by(RelationshipRow.friendship.desc(), RelationshipRow.subject_node_id)
    )
    hooked = await ctx.session.scalars(select(HookRow.target_node_id).where(HookRow.holder_node_id == owner, HookRow.used_epoch.is_(None)).order_by(HookRow.id))
    debtors = await ctx.session.scalars(
        select(FavourRow.owed_by_node_id).where(FavourRow.owed_to_node_id == owner, FavourRow.called_epoch.is_(None)).order_by(FavourRow.id)
    )
    return [*((node, False) for node in friends), *((node, True) for node in hooked), *((node, True) for node in debtors)]


async def recruitable(ctx: TickContext, scheme: SchemeRow, node_id: int, agents: list[int]) -> bool:
    if node_id in agents or node_id in (scheme.target_node_id, scheme.owner_node_id) or held(node_id):
        return False
    found = await living_entity(ctx.session, node_id)
    return found is not None and found.entity_type is EntityType.MORTAL


async def hire(ctx: TickContext, scheme: SchemeRow, agents: list[int], wanted: int) -> list[int]:
    table = ctx.rules.intrigue
    owner = await living_entity(ctx.session, scheme.owner_node_id)
    payer = await ctx.session.get(MortalProfileRow, scheme.owner_node_id)
    if owner is None or owner.location_id is None or payer is None or WEALTH in payer.locked:
        return []
    place = await ctx.session.get(EntityRow, owner.location_id)
    seek = scaled_cap(HIRE_SEEK, ctx.rules.scale.hire_seek_people, stat_or(place, "population", 0) if place is not None else 0)
    everyone = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [owner.location_id]))
        .order_by(EntityRow.id)
    )
    locals_ = ctx.rng(f"scheme.hire.{scheme.id}.{ctx.epoch}").sample(list(everyone), seek)
    pool = [node for node in locals_ if await recruitable(ctx, scheme, node, agents)]
    skills = {node: await skill(ctx, node) for node in pool}
    hired: list[int] = []
    for node in sorted(pool, key=lambda item: (-skills[item], item)):
        if len(hired) >= wanted or payer.wealth < table.agent_wage:
            break
        payee = await ctx.session.get(MortalProfileRow, node)
        if payee is None or not move_amount(payer, payee, WEALTH, table.agent_wage):
            continue
        hired.append(node)
    ctx.count("scheme_agents_hired", len(hired))
    return hired


async def recruit(ctx: TickContext, scheme: SchemeRow) -> None:
    spec = SCHEMES[scheme.kind]
    agents = list(scheme.agents)
    for node, leaned in await candidates(ctx, scheme):
        if len(agents) >= spec.agents:
            break
        if not await recruitable(ctx, scheme, node, agents):
            continue
        if leaned and not await leaned_on(ctx, scheme.owner_node_id, node, HookDemand.SUPPORT):
            continue
        agents.append(node)
    if len(agents) < spec.agents:
        agents.extend(await hire(ctx, scheme, agents, spec.agents - len(agents)))
    scheme.agents = agents
    if ctx.epoch - scheme.started_epoch >= ctx.rules.intrigue.recruit_epochs:
        scheme.phase = SchemePhase.PREPARE


async def prepare(ctx: TickContext, scheme: SchemeRow) -> None:
    table = ctx.rules.intrigue
    gain = await skill(ctx, scheme.owner_node_id) // TEN * table.owner_power
    for agent in scheme.agents:
        gain += await skill(ctx, agent) // TEN * table.agent_power
    scheme.power += max(1, gain)
    scheme.progress = clamp_int(scheme.power * PERCENT / max(1, SCHEMES[scheme.kind].difficulty), 0, PERCENT)
    if scheme.progress >= PERCENT:
        scheme.phase = SchemePhase.EXECUTE


async def spymaster_of(ctx: TickContext, target_id: int) -> int | None:
    realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == target_id).limit(1))
    office = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == (realm or target_id), OfficeRow.kind == OfficeKind.SPYMASTER).limit(1)
    )
    return office


async def defence(ctx: TickContext, scheme: SchemeRow, target: EntityRow | None) -> float:
    table = ctx.rules.intrigue
    base = float(SCHEMES[scheme.kind].difficulty)
    if target is None:
        return base
    master = await spymaster_of(ctx, target.id)
    if master is not None:
        base += await skill(ctx, master) // TEN * table.defence_spymaster
    if target.entity_type is EntityType.MORTAL:
        base += await attribute(ctx.session, ctx.rules, target, Attribute.INTUITION) * table.defence_intuition_pct / PERCENT
        guard = await bodyguard_of(ctx, target.id)
        if guard is not None:
            base += (stat(guard, "strength") or 0) // TEN * table.defence_bodyguard
    return base


async def bodyguard_of(ctx: TickContext, mortal_id: int) -> EntityRow | None:
    realm = await realm_of(ctx, mortal_id)
    if realm is None:
        return None
    holder = await ctx.session.scalar(
        select(CourtPositionRow.holder_entity_id).where(CourtPositionRow.polity_entity_id == realm, CourtPositionRow.position == CourtPosition.CHAMPION)
    )
    return await living_entity(ctx.session, holder) if holder is not None and holder != mortal_id else None


async def conditions(ctx: TickContext, target: EntityRow | None, atlas: RegionAtlas) -> tuple[float, float]:
    table = ctx.rules.intrigue
    boost, witnesses = 1.0, 1.0
    if target is None:
        return boost, witnesses
    weather = await weather_here(ctx, target.id, SCHEME_SLOT, atlas)
    kind = weather.kind if weather is not None else None
    if has_trait(kind, WeatherTrait.COVERING):
        boost += table.night_fog_pct / PERCENT
        witnesses -= table.night_fog_pct / PERCENT
    elif has_trait(kind, WeatherTrait.STORM):
        boost += table.storm_pct / PERCENT
    town_id = target.id if target.entity_type is EntityType.SETTLEMENT else target.location_id
    if town_id is not None and await ctx.session.scalar(
        select(SettlementTreasuryRow.id)
        .where(
            SettlementTreasuryRow.settlement_entity_id == town_id,
            SettlementTreasuryRow.epoch == ctx.epoch,
            SettlementTreasuryRow.entry == TreasuryEntry.FESTIVAL,
        )
        .limit(1)
    ):
        boost += table.crowd_pct / PERCENT
        witnesses += table.crowd_pct / PERCENT
    region_id = atlas.top_region(target.id)
    panic = region_id is not None and await ctx.session.scalar(
        select(OutbreakRow.id).where(OutbreakRow.region_entity_id == region_id, OutbreakRow.status == OutbreakStatus.ACTIVE).limit(1)
    )
    siege = town_id is not None and await ctx.session.scalar(
        select(SiegeRow.id).where(SiegeRow.besieged_entity_id == town_id, SiegeRow.status == SiegeStatus.ONGOING).limit(1)
    )
    if panic or siege:
        boost += table.panic_pct / PERCENT
    return boost, max(0.0, witnesses)


async def discovered(ctx: TickContext, scheme: SchemeRow, target: EntityRow | None, witnesses: float) -> bool:
    if target is None:
        return False
    master = await spymaster_of(ctx, target.id)
    counter = 0.5 + (await skill(ctx, master) if master is not None else 0) / PERCENT
    chance = ctx.rules.intrigue.discovery_pct * counter * (PERCENT - scheme.secrecy) / PERCENT * witnesses
    if await modality_of(ctx.session, (await spoken_language(ctx.session, target.id) or target).id) is LanguageModality.SCENT:
        chance *= 1 + ctx.rules.modality.scent_trace_pct / PERCENT
    return ctx.rng(f"scheme.discover.{scheme.id}.{ctx.epoch}").chance(chance)


async def unmask(ctx: TickContext, scheme: SchemeRow, target: EntityRow) -> None:
    scheme.phase, scheme.ended_epoch = SchemePhase.EXPOSED, ctx.epoch
    scheme.discovered_by = sorted({*scheme.discovered_by, target.id})
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=target.id,
        subject_id=scheme.owner_node_id,
        kind=MemoryKind.BETRAYED_ME,
        magnitude=-SCHEMES[scheme.kind].difficulty,
        epoch=ctx.epoch,
    )
    await add_infamy(ctx.session, scheme.owner_node_id, SCHEMES[scheme.kind].difficulty // 2, ctx.epoch, rules=ctx.rules)
    share = SCHEMES[scheme.kind].difficulty * ctx.rules.intrigue.agent_exposure_pct // PERCENT
    for agent in scheme.agents:
        if agent == target.id or held(agent):
            continue
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=target.id,
            subject_id=agent,
            kind=MemoryKind.BETRAYED_ME,
            magnitude=-share,
            epoch=ctx.epoch,
        )
        await add_infamy(
            ctx.session, agent, SCHEMES[scheme.kind].difficulty * ctx.rules.intrigue.agent_exposure_pct // (2 * PERCENT), ctx.epoch, rules=ctx.rules
        )
    owner = await living_entity(ctx.session, scheme.owner_node_id)
    if owner is not None:
        await record(
            ctx,
            f"intrigue.scheme_exposed_{scheme.kind.value}",
            roles={IncidentRole.TARGET: target.id, IncidentRole.ACTOR: owner.id, IncidentRole.CO_ACTOR: list(scheme.agents)},
            facts={"infamy": SCHEMES[scheme.kind].difficulty // 2, "power": scheme.power},
            place=target.location_id,
            steps=(StepDraft(StepAction.FIND_EVIDENCE, actor=target.id, target=owner.id, record_table=SchemeRow.__tablename__, record_key=str(scheme.id)),),
        )


async def owned_relic(ctx: TickContext, owner_id: int) -> EntityRow | None:
    for bond in await BondRepository(ctx.session).outgoing(owner_id, BondKind.OWNS):
        item = await living_entity(ctx.session, bond.target_node_id)
        if item is not None and item.entity_type is EntityType.ITEM and not held(item.id):
            return item
    return None


async def realm_of(ctx: TickContext, node_id: int) -> int | None:
    found: int | None = await ctx.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == node_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return found


STRIKES: Handlers[PlotKind, Callable[[TickContext, SchemeRow, EntityRow, EntityRow], Awaitable[str]]] = Handlers(PlotKind)


@STRIKES.on(PlotKind.MURDER)
async def murder(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    await death_path(ctx, target, "was murdered in secret", killer_id=owner.id, manner=DeathCause.MURDER)
    return f"{target.name} was found dead"


@STRIKES.on(PlotKind.ABDUCT)
async def abduct(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    await take_captive(ctx, owner, target, None, description="taken captive in secret", home_id=target.location_id)
    return f"{target.name} was taken captive"


@STRIKES.on(PlotKind.SEDUCE)
async def seduce(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    view = await ensure_relation(ctx.session, target.id, owner.id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, romance=SWAY * 2, friendship=SWAY)
    await keep_secret(ctx, target.id, IntrigueSecret.AFFAIR, about_id=owner.id, known_by=(owner.id,), source="scheme.seduce")
    return f"{target.name} began a secret love affair"


@STRIKES.on(PlotKind.SWAY)
async def sway(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    view = await ensure_relation(ctx.session, target.id, owner.id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, friendship=SWAY)
    return f"{target.name} came to like {owner.name}"


@STRIKES.on(PlotKind.FABRICATE_CLAIM)
async def fabricate_claim(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    realm = await realm_of(ctx, target.id)
    if realm is None:
        return "there was no rule to claim"
    ctx.session.add(ClaimRow(claimant_entity_id=owner.id, polity_entity_id=realm, basis=ClaimBasis.FABRICATED, since_epoch=ctx.epoch, locked=[]))
    if owner.entity_type is EntityType.MORTAL:
        await assume(ctx, owner, IdentityReason.IMPOSTOR, owner.name, cover_role="lost heir", community_id=realm)
    return f"{owner.name} gained a forged claim to rule over {target.name}"


@STRIKES.on(PlotKind.FABRICATE_HOOK)
async def fabricate_hook(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    secret = await keep_secret(ctx, target.id, IntrigueSecret.CRIME, known_by=(owner.id,), source="scheme.fabricate_hook")
    await grant_hook(ctx, owner.id, target.id, HookSource.SECRET, strong=False, secret_id=secret.id if secret is not None else None)
    return f"{owner.name} gained a hold over {target.name}"


@STRIKES.on(PlotKind.STEAL_RELIC)
async def steal_relic(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    relic = await owned_relic(ctx, target.id)
    if relic is None:
        return "there was nothing worth stealing"
    attempt = await attempt_theft(ctx, owner, target, relic)
    if attempt.thwarted:
        return f"the guards of {relic.name} stopped the theft" + ("; the thief was named" if attempt.betrayed else "")
    bonds = BondRepository(ctx.session)
    for bond in await bonds.active_between(target.id, relic.id, [BondKind.OWNS]):
        await bonds.deactivate(bond, ctx.epoch, "stolen")
    await connect(ctx.session, owner.id, relic.id, BondKind.OWNS, ctx.epoch, description="stolen")
    return f"{relic.name} was stolen from {target.name}"


@STRIKES.on(PlotKind.COUP)
async def coup(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    realm = await realm_of(ctx, target.id)
    office = (
        await ctx.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == OfficeKind.RULER).limit(1)) if realm else None
    )
    if office is None or "holder_entity_id" in (office.locked or []):
        return "rule could not be seized"
    office.holder_entity_id, office.since_epoch = owner.id, ctx.epoch
    return f"{owner.name} seized rule from {target.name}"


@STRIKES.on(PlotKind.POISON_WELL)
async def poison_well(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    if target.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
        return "there was no well to poison"
    home = await living_entity(ctx.session, owner.location_id) if owner.entity_type is EntityType.MORTAL else owner
    brought = home is not None and await GoodsLedger(ctx.session, ctx.epoch).take_units(home.id, CommodityKind.POISON, 1, GoodsFlow.CONSUMPTION) > 0
    loss = POISON_PCT + (ctx.rules.flora.poison_well_pct if brought else 0)
    set_stats(target, population=max(1, round_half_up((stat(target, "population") or 0) * (PERCENT - loss) / PERCENT)))
    return f"the wells of {target.name} were poisoned" + (" with poison brought from stores" if brought else "")


@STRIKES.on(PlotKind.FRAME)
async def frame(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    secret = await keep_secret(ctx, target.id, IntrigueSecret.CRIME, known_by=(owner.id,), source="scheme.frame")
    if secret is not None:
        await expose(ctx, secret, by_id=owner.id)
    case = await frame_case(ctx, target, owner.id)
    return f"{target.name} was blamed for a crime" + (" and brought to trial" if case is not None else "")


@STRIKES.on(PlotKind.ELOPE)
async def elope(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    await marry(ctx.session, owner, target, ctx.epoch, purpose=UnionPurpose.KINSHIP, description="eloped in secret")
    return f"{owner.name} and {target.name} eloped"


@STRIKES.on(PlotKind.CONVERT_SECRETLY)
async def convert_secretly(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    gods = [bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(owner.id, BondKind.WORSHIPS)]
    if not gods:
        return "there was no faith to share"
    await connect(ctx.session, target.id, gods[0], BondKind.WORSHIPS, ctx.epoch, description="converted in secret")
    await keep_secret(ctx, target.id, IntrigueSecret.SECRET_CULT_MEMBERSHIP, about_id=gods[0], known_by=(owner.id,), source="scheme.convert")
    return f"{target.name} took up a hidden faith"


@STRIKES.on(PlotKind.SABOTAGE_WEDDING)
async def sabotage_wedding(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    bonds = BondRepository(ctx.session)
    broken = 0
    for bond in await bonds.outgoing(target.id, BondKind.BETROTHED_TO):
        await bonds.deactivate(bond, ctx.epoch, "a betrothal undone")
        broken += 1
    return f"the betrothal of {target.name} fell apart" if broken else "there was no wedding to spoil"


@STRIKES.on(PlotKind.FREE_PRISONER)
async def free_prisoner(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    row = await ctx.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == target.id, CaptiveRow.status == CaptiveStatus.HELD).limit(1))
    if row is None:
        return "there was no prisoner to free"
    await release_captive(ctx, row, CaptiveStatus.RESCUED)
    await owe(ctx, target.id, owner.id, FavourOrigin.RESCUE, ctx.rules.intrigue.rescue_favour)
    return f"{target.name} was freed"


@STRIKES.on(PlotKind.ECOSABOTAGE)
async def ecosabotage(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    land = await living_entity(ctx.session, target.id if target.entity_type is EntityType.REGION else target.location_id)
    ground = await ctx.session.get(RegionEnvironmentRow, land.id) if land is not None and land.entity_type is EntityType.REGION else None
    if ground is None or land is None:
        return f"there was no land of {target.name} to blight"
    scar, deed = SABOTAGES[ctx.rng(f"scheme.ecosabotage.{scheme.id}").below(len(SABOTAGES))]
    add_scar(ground, scar, PERCENT // 4)
    await keep_secret(ctx, owner.id, IntrigueSecret.ECOSABOTAGE, about_id=target.id, known_by=tuple(scheme.agents), source="scheme.ecosabotage")
    town = (
        target
        if target.entity_type is EntityType.SETTLEMENT
        else await ctx.session.scalar(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == land.id)
            .order_by(EntityRow.importance.desc(), EntityRow.id)
            .limit(1)
        )
    )
    if town is not None and await report_crime(ctx, town.id, owner.id, CrimeKind.TREASON) is not None:
        ctx.count("sabotage_cases_opened")
    return f"the land of {target.name} was {deed}"


@STRIKES.on(PlotKind.LEARN_TRUE_NAME)
async def learn_true_name(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    name = await ctx.session.get(TrueNameRow, target.id)
    if name is None:
        return f"{target.name} has no true name to learn"
    if not await teach_name(ctx, name, owner.id):
        return f"{owner.name} could not learn more of the name of {target.name}"
    return f"{owner.name} learned the true name of {target.name}"


async def forged_order(ctx: TickContext, owner: EntityRow, realm: int) -> str | None:
    profile = await ctx.session.get(PolityProfileRow, realm)
    seat = profile.capital_entity_id if profile is not None else None
    for army in await commanders_of(ctx, realm):
        place = await ctx.session.get(ArmyProfileRow, army.entity_id)
        if seat is None or army.war_id is None or place is None or army.commander_entity_id is None:
            continue
        home = await ctx.session.get(EntityRow, seat)
        region = home.location_id if home is not None else None
        if region is None or region == place.region_entity_id:
            continue
        payload = {FORGER: owner.id, ARMY: army.entity_id, REGION: region}
        if await send(ctx, seat, army.commander_entity_id, DispatchContent.ORDER, Medium.LETTER, payload=payload, forged=True) is not None:
            return "a forged order went out to call an army home"
    return None


@STRIKES.on(PlotKind.FORGE_LETTER)
async def forge_letter(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    realm = await realm_of(ctx, target.id) or target.id
    ordered = await forged_order(ctx, owner, realm)
    if ordered is not None:
        return ordered
    rivals = (
        select(PolityProfileRow.polity_entity_id)
        .join(EntityRow, EntityRow.id == PolityProfileRow.polity_entity_id)
        .where(
            PolityProfileRow.polity_entity_id.not_in([realm, owner.id]),
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == target.world_id,
            free_rows(PolityProfileRow.polity_entity_id),
        )
    )
    neighbour = await ctx.session.scalar(rivals.order_by(PolityProfileRow.polity_entity_id).limit(1))
    if neighbour is None:
        return "there was no one to deceive"
    await send(ctx, realm, neighbour, DispatchContent.DECLARATION, Medium.LETTER, payload={FORGER: owner.id}, forged=True)
    return f"a forged declaration went out in the name of {target.name}"


@STRIKES.on(PlotKind.GEAS_TRAP)
async def geas_trap(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    row = await spring_trap(ctx, target, f"scheme.geas.{scheme.id}")
    return f"{target.name} was forced to break a geas" if row is not None else f"{target.name} avoided the trap"


@STRIKES.on(PlotKind.HIDE_FLEET)
async def hide_fleet(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    row = await ctx.session.scalar(
        select(AdmiraltyRow).where(or_(AdmiraltyRow.polity_entity_id == owner.id, AdmiraltyRow.admiral_entity_id == owner.id)).limit(1)
    )
    if row is None or row.limit_tonnage is None or "concealed" in row.locked:
        return "there was no fleet to hide"
    row.concealed = max(0, row.tonnage - row.limit_tonnage)
    return f"ships past the tonnage sworn to {target.name} were built and kept out of sight"


@STRIKES.on(PlotKind.FORGE_WORK)
async def forge_work(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    original = target if target.entity_type in FORGEABLE else await work_of(ctx, target)
    if original is None or held(original.id):
        return f"{owner.name} found nothing of {target.name} worth forging"
    row = await forge(ctx, original, owner)
    return f"{owner.name} made a forgery of {original.name} ({spoken(row.kind)})"


async def strike(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow | None) -> str:
    if target is None:
        return "it found no target"
    return await STRIKES[scheme.kind](ctx, scheme, owner, target)


async def execute(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow | None, *, boost: float, tally: SchemeTally) -> None:
    guard = await defence(ctx, scheme, target)
    odds = scheme.power * boost / max(1.0, scheme.power * boost + guard) * PERCENT
    scheme.ended_epoch = ctx.epoch
    if not ctx.rng(f"scheme.strike.{scheme.id}.{ctx.epoch}").chance(odds):
        scheme.phase = SchemePhase.FAILED
        tally.failed += 1
        return
    told = await strike(ctx, scheme, owner, target)
    scheme.phase, scheme.outcome = SchemePhase.SUCCEEDED, told
    spec = SCHEMES[scheme.kind]
    if spec.secret is not None and scheme.kind not in SECRETS_KEPT_ELSEWHERE:
        await keep_secret(
            ctx, owner.id, spec.secret, about_id=target.id if target is not None else None, known_by=tuple(scheme.agents), source=f"scheme.{scheme.kind.value}"
        )
    if spec.act is not None and target is not None:
        await judged(ctx, owner.id, target.id, spec.act)
    for agent in scheme.agents:
        await owe(ctx, owner.id, agent, FavourOrigin.SCHEME_AID, ctx.rules.intrigue.scheme_favour)
    tally.succeeded += 1
    await record(
        ctx,
        f"intrigue.scheme_done_{scheme.kind.value}",
        roles={IncidentRole.ACTOR: owner.id, IncidentRole.TARGET: target.id if target is not None else None, IncidentRole.CO_ACTOR: list(scheme.agents)},
        facts={"odds": odds, "power": scheme.power, "guard": guard},
        place=target.location_id if target is not None else owner.location_id,
        steps=plotted(scheme, owner, target),
    )


def plotted(scheme: SchemeRow, owner: EntityRow, target: EntityRow | None) -> tuple[StepDraft, ...]:
    action = PLOT_STEPS.get(scheme.kind)
    if action is None:
        return ()
    return (StepDraft(action, actor=owner.id, target=target.id if target is not None else None, outcome=StepOutcome.SUCCESS),)


async def tend_scheme(ctx: TickContext, scheme: SchemeRow, tally: SchemeTally, atlas: RegionAtlas) -> None:
    if scheme.phase not in OPEN or PHASE in (scheme.locked or []) or held(scheme.owner_node_id):
        return
    owner = await living_entity(ctx.session, scheme.owner_node_id)
    target = await living_entity(ctx.session, scheme.target_node_id) if scheme.target_node_id is not None else None
    if owner is None or (SCHEMES[scheme.kind].needs_target and target is None):
        scheme.phase, scheme.ended_epoch = SchemePhase.ABANDONED, ctx.epoch
        return
    if target is not None and held(target.id):
        return
    boost, witnesses = await conditions(ctx, target, atlas)
    if scheme.phase is SchemePhase.RECRUIT:
        await recruit(ctx, scheme)
    elif scheme.phase is SchemePhase.PREPARE:
        await prepare(ctx, scheme)
    if target is not None and scheme.phase is not SchemePhase.EXECUTE and await discovered(ctx, scheme, target, witnesses):
        await unmask(ctx, scheme, target)
        tally.exposed += 1
        return
    if scheme.phase is SchemePhase.EXECUTE:
        if boost <= 1.0 and await waits_for_cover(ctx, scheme):
            ctx.count("schemes_waiting_for_cover")
            return
        await execute(ctx, scheme, owner, target, boost=boost, tally=tally)


async def waits_for_cover(ctx: TickContext, scheme: SchemeRow) -> bool:
    patience = await skill(ctx, scheme.owner_node_id) * ctx.rules.intrigue.cover_patience_pct / PERCENT
    return ctx.rng(f"scheme.cover.{scheme.id}.{ctx.epoch}").chance(patience)


async def rival_of(ctx: TickContext, mortal_id: int) -> EntityRow | None:
    rows = await ctx.session.scalars(
        select(RelationshipRow)
        .where(RelationshipRow.holder_node_id == mortal_id, RelationshipRow.friendship < 0)
        .order_by(RelationshipRow.friendship, RelationshipRow.id)
    )
    for row in rows:
        if HOSTILE_KEYS & set(row.kinds or []) or row.friendship <= -FRIENDS_AT:
            found = await living_entity(ctx.session, row.subject_node_id)
            if found is not None and found.entity_type is EntityType.MORTAL and not held(found.id):
                return found
    return None


async def choose_kind(ctx: TickContext, owner: EntityRow, rival: EntityRow) -> PlotKind:
    traits = set(await traits_of(ctx.session, owner.id))
    if TraitKind.CRUEL in traits:
        return PlotKind.MURDER
    if TraitKind.AMBITIOUS in traits and await realm_of(ctx, rival.id) is not None:
        return PlotKind.COUP
    if TraitKind.DECEITFUL in traits:
        return (
            PlotKind.FORGE_WORK
            if stat_or(owner, "creativity", 0) >= ctx.rules.forgery.skill_floor and await work_of(ctx, rival) is not None
            else PlotKind.FRAME
        )
    return PlotKind.FABRICATE_HOOK if (await skill(ctx, owner.id)) >= PERCENT // 2 else PlotKind.SWAY


async def plotters(ctx: TickContext, tally: SchemeTally) -> None:
    table = ctx.rules.intrigue
    open_owners = set(await ctx.session.scalars(select(SchemeRow.owner_node_id).where(SchemeRow.phase.in_(list(OPEN)))))
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    mortals = ctx.rng("scheme.order").shuffled(list(await ctx.session.scalars(statement)))
    limit = scaled_cap(table.scheme_cap, table.scheme_cap_mortal_divisor, len(mortals))
    for mortal in mortals:
        if tally.begun >= limit:
            return
        if mortal.id in open_owners or held(mortal.id):
            continue
        traits = set(await traits_of(ctx.session, mortal.id))
        if not traits & {TraitKind.AMBITIOUS, TraitKind.CRUEL, TraitKind.DECEITFUL}:
            continue
        pressing = await pressing_foe(ctx, mortal.id)
        leaning = await lean(ctx, mortal.id, BiasedDecision.SCHEME)
        if not ctx.rng(f"scheme.begin.{mortal.id}.{ctx.epoch}").chance(pressed(ctx, table.scheme_ambition_pct, pressing[0] if pressing else 0) * leaning):
            continue
        rival = await living_entity(ctx.session, pressing[1]) if pressing is not None else None
        rival = rival or await rival_of(ctx, mortal.id)
        if rival is None:
            continue
        if await begin_scheme(ctx, mortal, await choose_kind(ctx, mortal, rival), rival) is not None:
            tally.begun += 1
