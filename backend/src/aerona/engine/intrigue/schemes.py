from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.intrigue import SCHEMES
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.intrigue import SchemeRow, TrueNameRow
from aerona.db.tables.polity import ClaimRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import SettlementTreasuryRow
from aerona.db.tables.warfare import CaptiveRow, SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind, WeatherKind
from aerona.domain.enums.intrigue import FavourOrigin, HookSource, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.domain.enums.mind import Attribute, MemoryKind, SkillKind, TraitKind
from aerona.domain.enums.mortal import DeathCause, MarriageKind
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.enums.relations import RelationType
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.war import CaptiveStatus, SiegeStatus
from aerona.engine.communication.post import FORGER, send
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.local import weather_here
from aerona.engine.intrigue.favours import owe
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.names import teach_name
from aerona.engine.intrigue.secrets import expose, grant_hook, keep_secret
from aerona.engine.mind.book import best_skill, traits_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mind.split import attribute
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.notes import note
from aerona.engine.polity.trials import frame_case
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.records import death_path
from aerona.engine.relations.book import ensure_relation, shift
from aerona.engine.services.war import release_captive, take_captive

TEN = 10
OPEN = frozenset({SchemePhase.RECRUIT, SchemePhase.PREPARE, SchemePhase.EXECUTE})
FRIENDS_AT = 30
RIVALS = frozenset({RelationType.RIVAL.value, RelationType.NEMESIS.value, RelationType.ENEMY.value})
SWAY = 20
POISON_PCT = 5
PHASE = "phase"
SCHEME_SLOT = "scheme"
COVERING_WEATHER = frozenset({WeatherKind.FOG, WeatherKind.BLIZZARD, WeatherKind.SANDSTORM})
PURSUIT_CUTTING_WEATHER = frozenset({WeatherKind.STORM, WeatherKind.MAGIC_STORM})


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
    return await best_skill(ctx.session, node_id, [SkillKind.INTRIGUE, SkillKind.DECEPTION])


async def recruit(ctx: TickContext, scheme: SchemeRow) -> None:
    spec = SCHEMES[scheme.kind]
    friends = await ctx.session.scalars(
        select(RelationshipRow.subject_node_id)
        .where(RelationshipRow.holder_node_id == scheme.owner_node_id, RelationshipRow.friendship >= FRIENDS_AT)
        .order_by(RelationshipRow.friendship.desc(), RelationshipRow.subject_node_id)
    )
    agents = list(scheme.agents)
    for friend in friends:
        if len(agents) >= spec.agents:
            break
        found = await living_entity(ctx.session, friend)
        if found is not None and found.entity_type is EntityType.MORTAL and friend not in agents and friend != scheme.target_node_id and not held(friend):
            agents.append(friend)
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
    return base


async def conditions(ctx: TickContext, target: EntityRow | None, atlas: RegionAtlas) -> tuple[float, float]:
    table = ctx.rules.intrigue
    boost, witnesses = 1.0, 1.0
    if target is None:
        return boost, witnesses
    weather = await weather_here(ctx, target.id, SCHEME_SLOT, atlas)
    kind = weather.kind if weather is not None else None
    if kind in COVERING_WEATHER:
        boost += table.night_fog_pct / PERCENT
        witnesses -= table.night_fog_pct / PERCENT
    elif kind in PURSUIT_CUTTING_WEATHER:
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
    owner = await living_entity(ctx.session, scheme.owner_node_id)
    if owner is not None:
        await note(
            ctx,
            f"{target.name} uncovered the {SCHEMES[scheme.kind].label.lower()} {owner.name} plotted against them.",
            key="intrigue.scheme_exposed",
            ids=[target.id, owner.id, *scheme.agents],
            kind=ChronicleKind.WORLD,
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


async def murder(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    await death_path(ctx, target, "was murdered in secret", killer_id=owner.id, manner=DeathCause.MURDER)
    return f"{target.name} was found dead"


async def abduct(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    await take_captive(ctx, owner, target, None, description="taken by a hidden hand", home_id=target.location_id)
    return f"{target.name} vanished into captivity"


async def seduce(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    view = await ensure_relation(ctx.session, target.id, owner.id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, romance=SWAY * 2, friendship=SWAY)
    await keep_secret(ctx, target.id, IntrigueSecret.AFFAIR, about_id=owner.id, known_by=(owner.id,), source="scheme.seduce")
    return f"{target.name} was drawn into a hidden love"


async def sway(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    view = await ensure_relation(ctx.session, target.id, owner.id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, friendship=SWAY)
    return f"{target.name} warmed to {owner.name}"


async def fabricate_claim(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    realm = await realm_of(ctx, target.id)
    if realm is None:
        return "there was no throne to claim"
    ctx.session.add(ClaimRow(claimant_entity_id=owner.id, polity_entity_id=realm, basis=ClaimBasis.FABRICATED, since_epoch=ctx.epoch, locked=[]))
    if owner.entity_type is EntityType.MORTAL:
        await assume(ctx, owner, IdentityReason.IMPOSTOR, owner.name, cover_role="lost heir", community_id=realm)
    return f"{owner.name} gained a forged claim on the throne of {target.name}"


async def fabricate_hook(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    secret = await keep_secret(ctx, target.id, IntrigueSecret.CRIME, known_by=(owner.id,), source="scheme.fabricate_hook")
    await grant_hook(ctx, owner.id, target.id, HookSource.SECRET, strong=False, secret_id=secret.id if secret is not None else None)
    return f"{owner.name} gained a hold over {target.name}"


async def steal_relic(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    relic = await owned_relic(ctx, target.id)
    if relic is None:
        return "there was nothing worth stealing"
    bonds = BondRepository(ctx.session)
    for bond in await bonds.active_between(target.id, relic.id, [BondKind.OWNS]):
        await bonds.deactivate(bond, ctx.epoch, "stolen")
    await connect(ctx.session, owner.id, relic.id, BondKind.OWNS, ctx.epoch, description="stolen")
    return f"{relic.name} was stolen from {target.name}"


async def coup(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    realm = await realm_of(ctx, target.id)
    office = (
        await ctx.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == OfficeKind.RULER).limit(1)) if realm else None
    )
    if office is None or "holder_entity_id" in (office.locked or []):
        return "the throne could not be seized"
    office.holder_entity_id, office.since_epoch = owner.id, ctx.epoch
    return f"{owner.name} seized the throne from {target.name}"


async def poison_well(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    if target.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
        return "there was no well to poison"
    set_stats(target, population=max(1, round_half_up((stat(target, "population") or 0) * (PERCENT - POISON_PCT) / PERCENT)))
    return f"the wells of {target.name} were poisoned"


async def frame(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    secret = await keep_secret(ctx, target.id, IntrigueSecret.CRIME, known_by=(owner.id,), source="scheme.frame")
    if secret is not None:
        await expose(ctx, secret, by_id=owner.id)
    case = await frame_case(ctx, target, owner.id)
    return f"{target.name} was blamed for a crime" + (" and brought to trial" if case is not None else "")


async def elope(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    await marry(ctx.session, owner, target, ctx.epoch, kind=MarriageKind.MONOGAMOUS, description="eloped in secret")
    return f"{owner.name} and {target.name} eloped"


async def convert_secretly(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    gods = [bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(owner.id, BondKind.WORSHIPS)]
    if not gods:
        return "there was no faith to share"
    await connect(ctx.session, target.id, gods[0], BondKind.WORSHIPS, ctx.epoch, description="converted in secret")
    await keep_secret(ctx, target.id, IntrigueSecret.SECRET_CULT_MEMBERSHIP, about_id=gods[0], known_by=(owner.id,), source="scheme.convert")
    return f"{target.name} took up a hidden faith"


async def sabotage_wedding(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    bonds = BondRepository(ctx.session)
    broken = 0
    for bond in await bonds.outgoing(target.id, BondKind.BETROTHED_TO):
        await bonds.deactivate(bond, ctx.epoch, "a betrothal undone")
        broken += 1
    return f"the betrothal of {target.name} fell apart" if broken else "there was no wedding to spoil"


async def free_prisoner(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    row = await ctx.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == target.id, CaptiveRow.status == CaptiveStatus.HELD).limit(1))
    if row is None:
        return "there was no prisoner to free"
    await release_captive(ctx, row, CaptiveStatus.RESCUED)
    await owe(ctx, target.id, owner.id, FavourOrigin.RESCUE, ctx.rules.intrigue.rescue_favour)
    return f"{target.name} was freed"


async def ecosabotage(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    land = await living_entity(ctx.session, target.id if target.entity_type is EntityType.REGION else target.location_id)
    ground = await ctx.session.get(RegionEnvironmentRow, land.id) if land is not None and land.entity_type is EntityType.REGION else None
    if ground is None:
        return f"there was no land of {target.name} to blight"
    add_scar(ground, ScarKind.BLIGHTED, PERCENT // 4)
    await keep_secret(ctx, owner.id, IntrigueSecret.ECOSABOTAGE, about_id=target.id, known_by=tuple(scheme.agents), source="scheme.ecosabotage")
    return f"the land of {target.name} was blighted in the night"


async def learn_true_name(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    name = await ctx.session.get(TrueNameRow, target.id)
    if name is None:
        return f"{target.name} has no true name to learn"
    if not await teach_name(ctx, name, owner.id):
        return f"{owner.name} could not learn more of the name of {target.name}"
    return f"{owner.name} learned the true name of {target.name}"


async def forge_letter(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow) -> str:
    realm = await realm_of(ctx, target.id) or target.id
    rivals = select(PolityProfileRow.polity_entity_id).where(PolityProfileRow.polity_entity_id.not_in([realm, owner.id]))
    neighbour = await ctx.session.scalar(rivals.order_by(PolityProfileRow.polity_entity_id).limit(1))
    if neighbour is None:
        return "there was no one to deceive"
    await send(ctx, realm, neighbour, DispatchContent.DECLARATION, Medium.LETTER, payload={FORGER: owner.id}, forged=True)
    return f"a forged declaration went out in the name of {target.name}"


STRIKES: dict[PlotKind, Callable[[TickContext, SchemeRow, EntityRow, EntityRow], Awaitable[str]]] = {
    PlotKind.MURDER: murder,
    PlotKind.ABDUCT: abduct,
    PlotKind.SEDUCE: seduce,
    PlotKind.SWAY: sway,
    PlotKind.FABRICATE_CLAIM: fabricate_claim,
    PlotKind.FABRICATE_HOOK: fabricate_hook,
    PlotKind.STEAL_RELIC: steal_relic,
    PlotKind.COUP: coup,
    PlotKind.POISON_WELL: poison_well,
    PlotKind.FRAME: frame,
    PlotKind.ELOPE: elope,
    PlotKind.CONVERT_SECRETLY: convert_secretly,
    PlotKind.SABOTAGE_WEDDING: sabotage_wedding,
    PlotKind.FREE_PRISONER: free_prisoner,
    PlotKind.ECOSABOTAGE: ecosabotage,
    PlotKind.LEARN_TRUE_NAME: learn_true_name,
    PlotKind.FORGE_LETTER: forge_letter,
}
SELF_SECRETS = frozenset({PlotKind.SEDUCE, PlotKind.FABRICATE_HOOK, PlotKind.FRAME, PlotKind.CONVERT_SECRETLY, PlotKind.ECOSABOTAGE})


async def strike(ctx: TickContext, scheme: SchemeRow, owner: EntityRow, target: EntityRow | None) -> str:
    if target is None:
        return "it struck at nothing"
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
    if spec.secret is not None and scheme.kind not in (
        PlotKind.SEDUCE,
        PlotKind.FABRICATE_HOOK,
        PlotKind.FRAME,
        PlotKind.CONVERT_SECRETLY,
        PlotKind.ECOSABOTAGE,
    ):
        await keep_secret(
            ctx, owner.id, spec.secret, about_id=target.id if target is not None else None, known_by=tuple(scheme.agents), source=f"scheme.{scheme.kind.value}"
        )
    if spec.act is not None and target is not None:
        await judged(ctx, owner.id, target.id, spec.act)
    for agent in scheme.agents:
        await owe(ctx, owner.id, agent, FavourOrigin.SCHEME_AID, ctx.rules.intrigue.scheme_favour)
    tally.succeeded += 1
    await note(
        ctx,
        f"A {spec.label.lower()} was carried out: {told}.",
        key="intrigue.scheme_done",
        ids=[owner.id, *([target.id] if target else [])],
        kind=ChronicleKind.WORLD,
    )


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
        await execute(ctx, scheme, owner, target, boost=boost, tally=tally)


async def rival_of(ctx: TickContext, mortal_id: int) -> EntityRow | None:
    rows = await ctx.session.scalars(
        select(RelationshipRow)
        .where(RelationshipRow.holder_node_id == mortal_id, RelationshipRow.friendship < 0)
        .order_by(RelationshipRow.friendship, RelationshipRow.id)
    )
    for row in rows:
        if RIVALS & set(row.kinds or []) or row.friendship <= -FRIENDS_AT:
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
        return PlotKind.FRAME
    return PlotKind.FABRICATE_HOOK if (await skill(ctx, owner.id)) >= PERCENT // 2 else PlotKind.SWAY


async def plotters(ctx: TickContext, tally: SchemeTally) -> None:
    table = ctx.rules.intrigue
    open_owners = set(await ctx.session.scalars(select(SchemeRow.owner_node_id).where(SchemeRow.phase.in_(list(OPEN)))))
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for mortal in await ctx.session.scalars(statement):
        if tally.begun >= table.scheme_cap:
            return
        if mortal.id in open_owners or held(mortal.id):
            continue
        traits = set(await traits_of(ctx.session, mortal.id))
        if not traits & {TraitKind.AMBITIOUS, TraitKind.CRUEL, TraitKind.DECEITFUL}:
            continue
        if not ctx.rng(f"scheme.begin.{mortal.id}.{ctx.epoch}").chance(table.scheme_ambition_pct):
            continue
        rival = await rival_of(ctx, mortal.id)
        if rival is None:
            continue
        if await begin_scheme(ctx, mortal, await choose_kind(ctx, mortal, rival), rival) is not None:
            tally.begun += 1
